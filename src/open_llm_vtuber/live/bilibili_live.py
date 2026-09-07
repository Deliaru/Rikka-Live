from __future__ import annotations

import asyncio
import http.cookies
import inspect
import json
import os
import random
import sys
import time
import traceback
from collections.abc import Awaitable, Callable
from typing import Any, Dict, List, Optional

import aiohttp
from loguru import logger
import websockets

from .live_interface import LivePlatformInterface

try:
    # Prefer a checked-out local blivedm clone when present, otherwise use the
    # PyPI package provided by bili-listener.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    project_blivedm = os.path.join(project_root, "blivedm")
    if os.path.isdir(project_blivedm):
        sys.path.insert(0, project_blivedm)

    import blivedm
    from blivedm.models import web as web_models
    from blivedm.handlers import BaseHandler

    BLIVEDM_AVAILABLE = True
    BLIVEDM_IMPORT_ERROR = ""
except ImportError as e:
    logger.warning(f"blivedm import failed: {e}")
    logger.warning("BiliBili live functionality will not be available.")
    BLIVEDM_AVAILABLE = False
    BLIVEDM_IMPORT_ERROR = str(e)

    class BaseHandler:
        """Fallback base so optional Bilibili support can be imported when absent."""

        pass


BilibiliEventHandler = Callable[[Dict[str, Any]], Awaitable[None] | None]


def _now_ms() -> int:
    return int(time.time() * 1000)


def get_blivedm_status() -> Dict[str, Any]:
    """Return runtime dependency status for the Bilibili danmaku adapter."""
    return {
        "available": BLIVEDM_AVAILABLE,
        "module": "blivedm",
        "package": "bili-listener",
        "import_error": BLIVEDM_IMPORT_ERROR,
    }


def build_bilibili_danmaku_event(
    danmaku_text: str,
    user_name: str = "",
    user_id: str = "",
    room_id: str = "",
) -> Dict[str, Any]:
    """Build a normalized Rikka Live event from a Bilibili danmaku packet."""
    actor = {"platform": "bilibili"}
    if user_name:
        actor["display_name"] = user_name
    if user_id:
        actor["user_id"] = str(user_id)

    return {
        "type": "chat.message",
        "source": "bilibili",
        "actor": actor,
        "text": danmaku_text,
        "room_id": str(room_id) if room_id else None,
        "payload": {},
        "privacy": {
            "contains_raw_media": False,
            "cloud_upload_allowed": False,
        },
    }


def _build_actor(
    user_name: str = "",
    user_id: str | int = "",
    medal: str = "",
    is_admin: bool | None = None,
) -> Dict[str, Any]:
    actor: Dict[str, Any] = {"platform": "bilibili"}
    if user_name:
        actor["display_name"] = user_name
    if user_id:
        actor["user_id"] = str(user_id)
    if medal:
        actor["medal"] = medal
    if is_admin is not None:
        actor["is_admin"] = is_admin
    return actor


def build_bilibili_gift_event(message: Any, room_id: str = "") -> Dict[str, Any]:
    """Build a normalized gift event from a Bilibili gift packet."""
    gift_name = getattr(message, "gift_name", "") or "礼物"
    num = getattr(message, "num", 1) or 1
    text = f"送出了 {num} 个 {gift_name}"
    amount = getattr(message, "price", None) or getattr(message, "total_coin", None)
    return {
        "type": "chat.gift",
        "source": "bilibili",
        "actor": _build_actor(
            user_name=getattr(message, "uname", ""),
            user_id=getattr(message, "uid", ""),
            medal=getattr(message, "medal_name", ""),
        ),
        "text": text,
        "amount": float(amount or num),
        "room_id": str(room_id) if room_id else None,
        "payload": {
            "gift_name": gift_name,
            "num": num,
            "coin_type": getattr(message, "coin_type", ""),
        },
        "privacy": {
            "contains_raw_media": False,
            "cloud_upload_allowed": False,
        },
    }


def build_bilibili_guard_event(message: Any, room_id: str = "") -> Dict[str, Any]:
    """Build a normalized guard purchase event."""
    guard_level = getattr(message, "guard_level", 0) or 0
    guard_name = {1: "总督", 2: "提督", 3: "舰长"}.get(guard_level, "大航海")
    num = getattr(message, "num", 1) or 1
    return {
        "type": "chat.guard",
        "source": "bilibili",
        "actor": _build_actor(
            user_name=getattr(message, "username", ""),
            user_id=getattr(message, "uid", ""),
        ),
        "text": f"开通了 {num} 个 {guard_name}",
        "amount": float(getattr(message, "price", 0) or 0),
        "room_id": str(room_id) if room_id else None,
        "payload": {
            "guard_level": guard_level,
            "guard_name": guard_name,
            "num": num,
            "gift_name": getattr(message, "gift_name", ""),
        },
        "privacy": {
            "contains_raw_media": False,
            "cloud_upload_allowed": False,
        },
    }


def build_bilibili_super_chat_event(message: Any, room_id: str = "") -> Dict[str, Any]:
    """Build a normalized Super Chat event."""
    text = getattr(message, "message", "") or getattr(message, "message_trans", "")
    return {
        "type": "chat.super_chat",
        "source": "bilibili",
        "actor": _build_actor(
            user_name=getattr(message, "uname", ""),
            user_id=getattr(message, "uid", ""),
            medal=getattr(message, "medal_name", ""),
        ),
        "text": text,
        "amount": float(getattr(message, "price", 0) or 0),
        "room_id": str(room_id) if room_id else None,
        "payload": {
            "super_chat_id": str(getattr(message, "id", "")),
            "time": getattr(message, "time", 0),
        },
        "privacy": {
            "contains_raw_media": False,
            "cloud_upload_allowed": False,
        },
    }


def build_bilibili_follow_event(message: Any, room_id: str = "") -> Dict[str, Any]:
    """Build a normalized Bilibili interaction/follow event."""
    msg_type = getattr(message, "msg_type", 0) or 0
    action = {1: "进入直播间", 2: "关注了直播间"}.get(msg_type, "触发了互动")
    return {
        "type": "chat.follow",
        "source": "bilibili",
        "actor": _build_actor(
            user_name=getattr(message, "username", ""),
            user_id=getattr(message, "uid", ""),
        ),
        "text": action,
        "room_id": str(room_id) if room_id else None,
        "payload": {
            "msg_type": msg_type,
            "action": action,
        },
        "privacy": {
            "contains_raw_media": False,
            "cloud_upload_allowed": False,
        },
    }


class BiliBiliLivePlatform(LivePlatformInterface):
    """
    Implementation of LivePlatformInterface for BiliBili Live platform.
    Connects to a BiliBili live room and forwards danmaku messages to the VTuber.
    """

    def __init__(
        self,
        room_ids: List[int],
        sessdata: str = "",
        proxy_url: str | None = "ws://localhost:12393/proxy-ws",
        event_handler: BilibiliEventHandler | None = None,
        speak: bool = True,
    ):
        """
        Initialize the BiliBili Live platform client.

        Args:
            room_ids: List of room IDs to monitor
            sessdata: Optional SESSDATA cookie value for authentication
            proxy_url: Optional proxy WebSocket URL. Pass None for in-process routing.
            event_handler: Optional callback for normalized LiveEvent payloads.
            speak: Whether proxy-forwarded events should trigger TTS.
        """
        if not BLIVEDM_AVAILABLE:
            raise ImportError(
                "blivedm library is required for BiliBili live functionality"
            )

        self._room_ids = room_ids
        self._sessdata = sessdata
        self._session: Optional[aiohttp.ClientSession] = None
        self._client: Optional[blivedm.BLiveClient] = None
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._proxy_url = proxy_url
        self._event_handler = event_handler
        self._speak = speak
        self._connected = False
        self._running = False
        self._active_room_id: Optional[int] = None
        self._connected_at_ms: Optional[int] = None
        self._last_packet_at_ms: Optional[int] = None
        self._last_packet_type = ""
        self._last_heartbeat_at_ms: Optional[int] = None
        self._last_heartbeat_popularity: Optional[int] = None
        self._received_packets = 0
        self._message_handlers: List[Callable[[Dict[str, Any]], None]] = []
        self._conversation_active = False
        self._last_error = ""

    @property
    def is_connected(self) -> bool:
        """Check if connected to the proxy server."""
        try:
            if hasattr(self._websocket, "closed"):
                return (
                    self._connected and self._websocket and not self._websocket.closed
                )
            elif hasattr(self._websocket, "open"):
                return self._connected and self._websocket and self._websocket.open
            else:
                return self._connected and self._websocket is not None
        except Exception:
            return False

    @property
    def is_running(self) -> bool:
        """Check if the Bilibili network client is expected to be running."""
        return self._running

    @property
    def active_room_id(self) -> Optional[int]:
        """Return the currently selected room ID, if a run has started."""
        return self._active_room_id

    @property
    def last_error(self) -> str:
        """Return the last privacy-safe lifecycle error, if any."""
        return self._last_error

    @property
    def connected_at_ms(self) -> Optional[int]:
        return self._connected_at_ms

    @property
    def last_packet_at_ms(self) -> Optional[int]:
        return self._last_packet_at_ms

    @property
    def last_packet_type(self) -> str:
        return self._last_packet_type

    @property
    def last_heartbeat_at_ms(self) -> Optional[int]:
        return self._last_heartbeat_at_ms

    @property
    def last_heartbeat_popularity(self) -> Optional[int]:
        return self._last_heartbeat_popularity

    @property
    def received_packets(self) -> int:
        return self._received_packets

    def _mark_packet(self, packet_type: str, popularity: int | None = None) -> None:
        self._last_packet_at_ms = _now_ms()
        self._last_packet_type = packet_type
        self._received_packets += 1
        if packet_type == "heartbeat":
            self._last_heartbeat_at_ms = self._last_packet_at_ms
            self._last_heartbeat_popularity = popularity

    def _init_session(self):
        """Initialize HTTP session with cookies if provided."""
        cookies = http.cookies.SimpleCookie()
        if self._sessdata:
            cookies["SESSDATA"] = self._sessdata
            cookies["SESSDATA"]["domain"] = "bilibili.com"

        self._session = aiohttp.ClientSession()
        self._session.cookie_jar.update_cookies(cookies)

    async def connect(self, proxy_url: str) -> bool:
        """
        Connect to the proxy WebSocket server.

        Args:
            proxy_url: The WebSocket URL of the proxy

        Returns:
            bool: True if connection successful
        """
        try:
            # Connect to the proxy WebSocket
            self._websocket = await websockets.connect(
                proxy_url, ping_interval=20, ping_timeout=10, close_timeout=5
            )
            self._connected = True
            logger.info(f"Connected to proxy at {proxy_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to proxy: {e}")
            return False

    async def disconnect(self) -> None:
        """
        Disconnect from the proxy server and stop the BiliBili client.
        """
        self._running = False

        # Stop BiliBili client if running
        if self._client:
            try:
                await self._client.stop_and_close()
                self._client = None
            except Exception as e:
                logger.warning(f"Error while stopping BiliBili client: {e}")

        # Close WebSocket connection
        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.warning(f"Error while closing WebSocket: {e}")

        # Close HTTP session
        if self._session:
            try:
                await self._session.close()
                self._session = None
            except Exception as e:
                logger.warning(f"Error while closing HTTP session: {e}")

        self._connected = False
        logger.info("Disconnected from BiliBili Live and proxy server")

    async def send_message(self, text: str) -> bool:
        """
        Send a text message to the VTuber through the proxy.
        Not used for BiliBili Live as we only receive messages, not send them.

        Args:
            text: The message text

        Returns:
            bool: True if sent successfully
        """
        # BiliBili Live platform only receives messages, doesn't send them back to the live room
        logger.warning(
            "BiliBili Live platform doesn't support sending messages back to the live room"
        )
        return False

    async def register_message_handler(
        self, handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register a callback for handling incoming messages.

        Args:
            handler: Function to call when a message is received
        """
        self._message_handlers.append(handler)
        logger.debug("Registered new message handler")

    async def _handle_danmaku(
        self,
        danmaku_text: str,
        user_name: str = "",
        user_id: str = "",
        room_id: str = "",
    ):
        """
        Process received danmaku message and forward it to VTuber.

        Args:
            danmaku_text: The danmaku text received from BiliBili
        """
        try:
            event = build_bilibili_danmaku_event(
                danmaku_text=danmaku_text,
                user_name=user_name,
                user_id=user_id,
                room_id=room_id,
            )
            await self._dispatch_live_event(event)
        except Exception as e:
            logger.error(f"Error forwarding danmaku to proxy: {e}")

    async def _dispatch_live_event(self, event: Dict[str, Any]) -> bool:
        handled = False

        if self._event_handler:
            result = self._event_handler(event)
            if inspect.isawaitable(result):
                await result
            handled = True

        if self._proxy_url:
            handled = await self._send_event_to_proxy(event) or handled

        if not handled:
            logger.warning("Bilibili event was normalized but had no consumer")
        return handled

    async def _send_event_to_proxy(self, event: Dict[str, Any]) -> bool:
        """
        Send normalized danmaku event to the proxy.

        Args:
            event: The normalized LiveEvent payload

        Returns:
            bool: True if sent successfully
        """
        if not self.is_connected:
            logger.error("Cannot send message: Not connected to proxy")
            return False

        try:
            message = {
                "type": "rikka-live-event",
                "event": event,
                "speak": self._speak,
            }
            await self._websocket.send(json.dumps(message))
            logger.info(f"Sent normalized danmaku event to VTuber: {event.get('text')}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to proxy: {e}")
            self._connected = False
            return False

    async def start_receiving(self) -> None:
        """
        Start receiving messages from the proxy WebSocket.
        This runs in the background to receive messages from the VTuber.
        """
        if not self.is_connected:
            logger.error("Cannot start receiving: Not connected to proxy")
            return

        try:
            logger.info("Started receiving messages from proxy")
            while self._running and self.is_connected:
                try:
                    message = await self._websocket.recv()
                    data = json.loads(message)

                    # Log received message (truncate audio data for readability)
                    if "audio" in data:
                        log_data = data.copy()
                        log_data["audio"] = (
                            f"[Audio data, length: {len(data['audio'])}]"
                        )
                        logger.debug(f"Received message from VTuber: {log_data}")
                    else:
                        logger.debug(f"Received message from VTuber: {data}")

                    # Process the message
                    await self.handle_incoming_messages(data)

                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed by server")
                    self._connected = False
                    break
                except Exception as e:
                    logger.error(f"Error receiving message from proxy: {e}")
                    await asyncio.sleep(1)

            logger.info("Stopped receiving messages from proxy")
        except Exception as e:
            logger.error(f"Error in message receiving loop: {e}")

    async def handle_incoming_messages(self, message: Dict[str, Any]) -> None:
        """
        Process messages received from the VTuber.

        Args:
            message: The message received from the VTuber
        """
        # Process the message with all registered handlers
        for handler in self._message_handlers:
            try:
                await asyncio.to_thread(handler, message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    class VtuberHandler(BaseHandler):
        """
        Handler for BiliBili Live danmaku messages.
        """

        def __init__(self, platform):
            super().__init__()
            self.platform = platform

        def _on_danmaku(
            self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage
        ):
            """
            Handle danmaku message from BiliBili Live.

            Args:
                client: The BiliBili Live client
                message: The danmaku message
            """
            self.platform._mark_packet("danmaku")
            logger.debug(f"[Room {client.room_id}] {message.uname}: {message.msg}")
            asyncio.create_task(
                self.platform._handle_danmaku(
                    danmaku_text=message.msg,
                    user_name=getattr(message, "uname", ""),
                    user_id=getattr(message, "uid", ""),
                    room_id=str(client.room_id),
                )
            )

        def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
            self.platform._mark_packet("gift")
            logger.debug(
                f"[Room {client.room_id}] gift from {message.uname}: {message.gift_name}"
            )
            asyncio.create_task(
                self.platform._dispatch_live_event(
                    build_bilibili_gift_event(message, room_id=str(client.room_id))
                )
            )

        def _on_buy_guard(
            self, client: blivedm.BLiveClient, message: web_models.GuardBuyMessage
        ):
            self.platform._mark_packet("guard")
            logger.debug(
                f"[Room {client.room_id}] guard from {message.username}: {message.gift_name}"
            )
            asyncio.create_task(
                self.platform._dispatch_live_event(
                    build_bilibili_guard_event(message, room_id=str(client.room_id))
                )
            )

        def _on_user_toast_v2(
            self, client: blivedm.BLiveClient, message: web_models.UserToastV2Message
        ):
            self.platform._mark_packet("guard_toast")
            logger.debug(
                f"[Room {client.room_id}] guard toast from {message.username}: {message.toast_msg}"
            )
            asyncio.create_task(
                self.platform._dispatch_live_event(
                    build_bilibili_guard_event(message, room_id=str(client.room_id))
                )
            )

        def _on_super_chat(
            self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage
        ):
            self.platform._mark_packet("super_chat")
            logger.debug(
                f"[Room {client.room_id}] super chat from {message.uname}: {message.message}"
            )
            asyncio.create_task(
                self.platform._dispatch_live_event(
                    build_bilibili_super_chat_event(message, room_id=str(client.room_id))
                )
            )

        def _on_interact_word(
            self, client: blivedm.BLiveClient, message: web_models.InteractWordMessage
        ):
            self.platform._mark_packet("interact")
            logger.debug(
                f"[Room {client.room_id}] interact from {message.username}: {message.msg_type}"
            )
            asyncio.create_task(
                self.platform._dispatch_live_event(
                    build_bilibili_follow_event(message, room_id=str(client.room_id))
                )
            )

        def _on_heartbeat(
            self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage
        ):
            """
            Handle heartbeat packet from BiliBili Live.

            Args:
                client: The BiliBili Live client
                message: The heartbeat message
            """
            self.platform._mark_packet(
                "heartbeat",
                popularity=getattr(message, "popularity", None),
            )
            logger.debug(
                f"[Room {client.room_id}] Heartbeat, popularity: {message.popularity}"
            )

    async def run(self) -> None:
        """
        Main entry point for running the BiliBili Live platform client.
        Connects to BiliBili Live rooms and the proxy, and starts monitoring danmaku.
        """
        try:
            self._last_error = ""
            self._running = True

            # Initialize HTTP session
            self._init_session()

            receive_task: asyncio.Task | None = None
            if self._proxy_url:
                if not await self.connect(self._proxy_url):
                    self._last_error = "failed to connect to configured proxy"
                    logger.error("Failed to connect to proxy, exiting")
                    return
                receive_task = asyncio.create_task(self.start_receiving())
            else:
                logger.info("Running BiliBili Live without proxy forwarding")

            # Randomly select a room ID if multiple are provided
            room_id = random.choice(self._room_ids)
            self._active_room_id = room_id
            self._connected_at_ms = _now_ms()

            # Create and start the BiliBili Live client
            self._client = blivedm.BLiveClient(room_id, session=self._session)
            handler = self.VtuberHandler(self)
            self._client.set_handler(handler)
            self._client.start()

            logger.info(f"Connected to BiliBili Live room {room_id}")

            # Wait until stopped
            try:
                await self._client.join()
            finally:
                await self._client.stop_and_close()

            # Clean up receive task if necessary
            if receive_task and not receive_task.done():
                receive_task.cancel()
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Error in BiliBili Live run loop: {e}")
            logger.debug(traceback.format_exc())
        finally:
            # Ensure clean disconnect
            await self.disconnect()
