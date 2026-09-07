import { startMicStream } from "./audio.js";
import { $, prettyJson, setPill, text } from "./dom.js";
import { state } from "./state.js";
import { renderAll } from "./render.js";

const STORAGE_KEY = "rikkaAlwaysOnListening";
const SILENCE_FINAL_MS = 900;
const MIN_UTTERANCE_MS = 240;
const SPEECH_LEVEL = 0.012;

let socket = null;
let mic = null;
let ownerClientUid = "";
let speakingStartedAt = 0;
let lastVoiceAt = 0;
let sentSamples = 0;
let lastLevelRenderAt = 0;

function wsUrl() {
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${location.host}/client-ws`;
}

function send(payload) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return false;
  socket.send(JSON.stringify(payload));
  return true;
}

function setMicState(patch, options = {}) {
  state.mic = { ...state.mic, ...patch, updatedAt: Date.now() };
  if (options.render === false) return;
  renderAll();
}

function setMicLevel(level) {
  state.mic = { ...state.mic, audioLevel: level, updatedAt: Date.now() };
  const now = Date.now();
  if (now - lastLevelRenderAt < 250) return;
  lastLevelRenderAt = now;
  renderAll();
}

function isOwner() {
  return ownerClientUid && ownerClientUid === state.mic.clientUid;
}

function reportCapabilities(extra = {}) {
  send({
    type: "client-capabilities",
    client_kind: "console",
    always_on_enabled: Boolean(state.mic.alwaysOnEnabled),
    mic_permission: state.mic.permission || "unknown",
    listening: Boolean(state.mic.listening),
    ...extra,
  });
}

function requestMicOwner(reason = "console_owner_request") {
  return send({
    type: "mic-owner-request",
    client_kind: "console",
    always_on_enabled: Boolean(state.mic.alwaysOnEnabled),
    mic_permission: state.mic.permission || "unknown",
    listening: Boolean(state.mic.listening),
    reason,
  });
}

function applyOwnerState(payload) {
  ownerClientUid = payload.owner_client_uid || "";
  const owner = payload.owner || null;
  setMicState({
    owner,
    ownerClientUid,
    streamingStatus: payload.streaming_status || state.mic.streamingStatus,
    status: ownerClientUid === state.mic.clientUid ? "owner_listening" : state.mic.status,
    reason: payload.reason || state.mic.reason,
  });
}

function maybeFinalize(level) {
  const now = Date.now();
  if (level >= SPEECH_LEVEL) {
    if (!speakingStartedAt) speakingStartedAt = now;
    lastVoiceAt = now;
    return;
  }
  if (!speakingStartedAt || sentSamples <= 0) return;
  if (now - lastVoiceAt < SILENCE_FINAL_MS) return;
  if (now - speakingStartedAt < MIN_UTTERANCE_MS) {
    speakingStartedAt = 0;
    sentSamples = 0;
    return;
  }
  send({ type: "mic-audio-end" });
  setMicState({
    status: "endpoint",
    reason: "silence endpoint submitted",
    endpointsSent: (state.mic.endpointsSent || 0) + 1,
  });
  speakingStartedAt = 0;
  sentSamples = 0;
}

async function startListening() {
  if (mic) {
    reportCapabilities({ mic_permission: state.mic.permission || "granted", listening: true, reason: "mic_already_active" });
    requestMicOwner("mic_already_active");
    return;
  }
  try {
    setMicState({
      status: "requesting_permission",
      permission: "prompt_or_recording",
      alwaysOnEnabled: true,
      reason: "requesting browser microphone permission",
    });
    mic = await startMicStream({
      onLevel(level) {
        setMicLevel(level);
        maybeFinalize(level);
      },
      onChunk(chunk) {
        state.mic = { ...state.mic, chunksCaptured: (state.mic.chunksCaptured || 0) + 1 };
        if (!isOwner()) {
          state.mic = {
            ...state.mic,
            chunksDroppedNotOwner: (state.mic.chunksDroppedNotOwner || 0) + 1,
            reason: "microphone level active, waiting for mic owner",
          };
          return;
        }
        if (chunk.level < SPEECH_LEVEL && !speakingStartedAt) {
          state.mic = { ...state.mic, chunksDroppedQuiet: (state.mic.chunksDroppedQuiet || 0) + 1 };
          return;
        }
        sentSamples += Array.isArray(chunk.audio) ? chunk.audio.length : 0;
        state.mic = { ...state.mic, chunksSent: (state.mic.chunksSent || 0) + 1 };
        send({
          type: "mic-audio-data",
          audio: chunk.audio,
          sample_rate: chunk.sample_rate,
        });
      },
    });
    setMicState({
      permission: "granted",
      listening: true,
      status: "listening",
      reason: "console microphone capture active",
    });
    reportCapabilities({ mic_permission: "granted", listening: true });
    requestMicOwner("console_microphone_capture_active");
  } catch (error) {
    mic = null;
    setMicState({
      permission: "denied_or_unavailable",
      listening: false,
      status: "denied",
      reason: error.message,
    });
    reportCapabilities({
      mic_permission: "denied_or_unavailable",
      listening: false,
      reason: error.message,
    });
  }
}

function stopListening(reason = "disabled") {
  if (mic) mic.stop();
  mic = null;
  speakingStartedAt = 0;
  lastVoiceAt = 0;
  sentSamples = 0;
  setMicState({
    listening: false,
    audioLevel: 0,
    status: reason,
    reason,
  });
  send({ type: "mic-owner-release", reason });
  reportCapabilities({ listening: false, reason });
}

function connectSocket() {
  if (socket) socket.close();
  socket = new WebSocket(wsUrl());
  socket.addEventListener("open", () => {
    reportCapabilities({ reason: "console_connected" });
    if (state.mic.alwaysOnEnabled) {
      startListening();
      if (mic) requestMicOwner("console_reconnected");
    }
  });
  socket.addEventListener("close", () => {
    ownerClientUid = "";
    setMicState({ status: "ws_closed", reason: "console WebSocket closed" });
  });
  socket.addEventListener("message", (event) => {
    let payload = null;
    try {
      payload = JSON.parse(event.data);
    } catch (_error) {
      return;
    }
    if (payload.type === "set-model-and-conf") {
      setMicState({ clientUid: payload.client_uid || "" });
      if (mic) requestMicOwner("client_uid_received");
      return;
    }
    if (payload.type === "asr-owner-state") {
      applyOwnerState(payload);
      return;
    }
    if (payload.type === "asr-streaming-partial") {
      setMicState({
        transcript: payload.text || "",
        status: "partial_transcript",
        reason: "streaming partial transcript",
      });
      return;
    }
    if (payload.type === "user-input-transcription") {
      setMicState({
        transcript: payload.text || payload.transcript || "",
        status: "final_transcript",
        finalCount: (state.mic.finalCount || 0) + 1,
      });
      return;
    }
    if (payload.type === "wake-gate") {
      const match = payload.match_kind ? `/${payload.match_kind}` : "";
      setMicState({
        wakeDecision: `${payload.source || "wake"}:${payload.reason || "wake_gate"}${match}`,
        status: payload.source === "partial"
          ? payload.woke ? "partial_wake" : "partial_missing"
          : payload.should_process ? "accepted" : "rejected",
      });
      return;
    }
    if (payload.type === "control" && payload.text === "mic-disabled") {
      setMicState({ asr: "asr_disabled", status: "asr_disabled" });
    }
  });
}

function syncToggle() {
  const toggle = $("always-on-listening");
  if (!toggle) return;
  toggle.checked = state.mic.alwaysOnEnabled;
  setPill($("mic-owner-state"), "owner unknown", "info");
}

export function setupAlwaysOnListening() {
  const enabled = localStorage.getItem(STORAGE_KEY) === "true";
  state.mic.alwaysOnEnabled = enabled;
  syncToggle();
  const toggle = $("always-on-listening");
  if (toggle) {
    toggle.addEventListener("change", () => {
      const next = Boolean(toggle.checked);
      localStorage.setItem(STORAGE_KEY, String(next));
      setMicState({ alwaysOnEnabled: next });
      if (next) {
        startListening();
      } else {
        stopListening("always_on_disabled");
      }
    });
  }
  connectSocket();
  text($("mic-result"), prettyJson({ always_on_listening: enabled }));
}
