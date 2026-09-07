import { age, toneForState } from "./dom.js";

export function readiness(snapshot) {
  const health = snapshot.health || {};
  const providers = health.providers || {};
  const flowDiagnostics = snapshot.flow?.diagnostics || {};
  const clients = snapshot.clients || flowDiagnostics.live2d || {};
  const tts = providers.tts || flowDiagnostics.tts || {};
  const planner = providers.planner || flowDiagnostics.planner || {};
  const privacy = providers.privacy || flowDiagnostics.privacy || {};
  const capture = snapshot.capture?.capture || snapshot.overlay?.capture || {};
  const proactive = snapshot.proactive?.proactive || {};
  const mic = snapshot.mic || {};

  const connectedClients = Number(clients.connected_clients || 0);
  const bridgeReady = Boolean(clients.live2d_bridge_ready);
  const blocker = flowDiagnostics.blocker || inferBlocker({ connectedClients, bridgeReady, tts, planner, capture, mic });

  return {
    blocker: {
      key: blocker,
      tone: blocker === "ready" ? "ok" : blocker.includes("missing") || blocker.includes("offline") ? "bad" : "warn",
      title: blockerLabel(blocker),
      detail: flowDiagnostics.detail || blockerDetail(blocker),
    },
    metrics: [
      {
        label: "Live2D 客户端",
        value: String(connectedClients),
        detail: bridgeReady ? "bridge ready" : "bridge not ready",
        state: connectedClients > 0 && bridgeReady ? "ok" : "warn",
      },
      {
        label: "TTS",
        value: providerName(tts.provider),
        detail: tts.mode ? `${displayValue(tts.mode)} / key ${tts.api_key_configured ? "ready" : "missing"}` : providerDetail(tts),
        state: tts.last_error ? "bad" : tts.api_key_configured === false ? "warn" : "ok",
      },
      {
        label: "LLM / Planner",
        value: providerName(planner.provider || providers.llm?.provider),
        detail: planner.last_error || providerDetail(providers.llm || planner),
        state: planner.last_error ? "bad" : "ok",
      },
      {
        label: "Capture",
        value: displayValue(capture.status || (privacy.screen_capture_enabled ? "enabled" : "disabled")),
        detail: capture.reason || `upload ${privacy.keyframe_upload_enabled ? "enabled" : "disabled"}`,
        state: toneForState(capture.status || "disabled"),
      },
      {
        label: "Mic / Wake",
        value: displayValue(mic.status || "unknown"),
        detail: mic.reason || "等待测试",
        state: toneForState(mic.status),
      },
      {
        label: "Proactive",
        value: displayValue(proactive.last_decision || proactive.status || "unknown"),
        detail: proactive.last_tick_at_ms ? `last tick ${age(proactive.last_tick_at_ms)}` : "等待 scheduler tick",
        state: toneForState(proactive.last_decision || proactive.status),
      },
    ],
  };
}

export function latestFrontendAction(flow, kind = null) {
  const actions = flow?.frontend_actions || [];
  if (!kind) return actions[0] || null;
  return actions.find((action) => action.kind === kind) || null;
}

export function captureRows(capturePayload) {
  const capture = capturePayload?.capture || {};
  return [
    ["状态", displayValue(capture.status || "unknown")],
    ["原因", capture.reason || "无"],
    ["可用", capture.available],
    ["最新帧", capture.latest_frame ? "已有" : "无"],
    ["原始媒体落盘", capture.raw_media_persisted ? "是" : "否"],
  ];
}

export function proactiveRows(payload) {
  const proactive = payload?.proactive || {};
  const screen = payload?.screen_comment_decision || {};
  const idle = payload?.idle_speech_decision || {};
  return [
    ["last tick", proactive.last_tick_at_ms ? age(proactive.last_tick_at_ms) : "waiting_for_tick"],
    ["last decision", proactive.last_decision || "unknown"],
    ["triggered", proactive.last_triggered],
    ["screen comment", decisionLine(screen)],
    ["idle speech", decisionLine(idle)],
    ["reason", proactive.last_reason || screen.reason || idle.reason || "none"],
  ];
}

export function micRows(mic, settings, telemetry = {}) {
  const audio = settings?.audio || {};
  const wakeAction = telemetry.wake || null;
  const micAction = telemetry.mic || null;
  return [
    ["ASR", mic.asr || "unknown"],
    ["streaming", mic.streamingStatus || "unknown"],
    ["浏览器麦克风", mic.permission || "unknown"],
    ["录音捕获", mic.status || "unknown"],
    ["常驻监听", mic.alwaysOnEnabled ? "enabled" : "off"],
    ["active owner", mic.owner?.client_kind ? `${mic.owner.client_kind} / ${mic.owner.client_uid === mic.clientUid ? "this client" : "other client"}` : "none"],
    ["listening", mic.listening ? "true" : "false"],
    ["audio level", Number(mic.audioLevel || 0).toFixed(4)],
    ["audio chunks", `captured ${mic.chunksCaptured || 0} / sent ${mic.chunksSent || 0}`],
    ["dropped chunks", `not owner ${mic.chunksDroppedNotOwner || 0} / quiet ${mic.chunksDroppedQuiet || 0}`],
    ["endpoints sent", String(mic.endpointsSent || 0)],
    ["唤醒门控", audio.wake_gate_enabled ? "enabled" : "off"],
    ["唤醒词", (audio.wake_phrases || []).join(", ") || "missing"],
    ["ASR 混淆别名", (audio.wake_asr_confusions || []).join(", ") || "none"],
    ["最近转写", mic.transcript || "none"],
    ["wake decision", mic.wakeDecision || "unknown"],
    ["Overlay mic", micAction ? `${micAction.status || "unknown"} / ${micAction.detail || ""}` : "no telemetry"],
    ["Overlay wake", wakeAction ? `${wakeAction.status || "unknown"} / ${wakeAction.detail || ""}` : "no telemetry"],
    ["reason", mic.reason || "尚未测试"],
  ];
}

export function eventIsDiagnostic(event) {
  if (event?.diagnostic === true) return true;
  if (event?.source === "diagnostic") return true;
  if (event?.platform === "diagnostic") return true;
  if (event?.type && String(event.type).startsWith("diagnostic.")) return true;
  const payload = event?.payload || {};
  return payload.diagnostic === true || payload.non_replayable === true;
}

function inferBlocker({ connectedClients, bridgeReady, tts, planner, capture, mic }) {
  if (connectedClients <= 0) return "live2d_offline";
  if (!bridgeReady) return "bridge_missing";
  if (planner.last_error) return "planner_error";
  if (tts.provider === "indextts2_tts" && tts.mode === "cloud" && !tts.api_key_configured) return "tts_key_missing";
  if (capture.status === "blocked") return "capture_blocked";
  if (mic.status === "asr_disabled") return "asr_disabled";
  return "ready";
}

function blockerLabel(blocker) {
  const labels = {
    ready: "READY",
    bilibili_failed: "BILIBILI FAILED",
    bilibili_idle: "BILIBILI IDLE",
    live2d_offline: "LIVE2D OFFLINE",
    bridge_missing: "BRIDGE MISSING",
    waiting_real_danmaku: "WAITING REAL EVENT",
    planner_error: "PLANNER ERROR",
    tts_key_missing: "TTS KEY MISSING",
    capture_blocked: "CAPTURE BLOCKED",
    asr_disabled: "ASR DISABLED",
  };
  return labels[blocker] || String(blocker || "UNKNOWN").toUpperCase();
}

function blockerDetail(blocker) {
  const details = {
    ready: "Overlay、后端和主要链路已可观察。",
    live2d_offline: "打开 /overlay/ 后再发送 debug speak，才会有 Live2D 前端回执。",
    bridge_missing: "Live2D bridge 不可用，检查 Overlay 是否加载完成。",
    tts_key_missing: "IndexTTS2 cloud 需要 API Key 和 Voice ID。",
    capture_blocked: "捕捉被隐私设置或前台调试保护拦截。",
    asr_disabled: "当前 ASR 被配置禁用，麦克风测试会显示 asr_disabled。",
  };
  return details[blocker] || "查看 Test Lab 中对应模块的 reason。";
}

function providerDetail(provider) {
  if (!provider) return "unknown";
  if (provider.last_error) return provider.last_error;
  if (provider.ready === false) return provider.reason || "not ready";
  return displayValue(provider.model || provider.mode || "ready");
}

function providerName(name) {
  const labels = {
    indextts2_tts: "IndexTTS2",
    xiaomi_mimo_tts: "MiMo",
    openai_compatible_llm: "OpenAI compat",
  };
  return labels[name] || name || "unknown";
}

function displayValue(value) {
  const labels = {
    cloud_or_local_by_endpoint: "endpoint decides mode",
    asr_disabled: "ASR disabled",
    waiting_for_tick: "waiting for tick",
    waiting_for_target: "waiting for target",
    foreground_debug: "foreground debug",
    key_missing: "key missing",
    no_active_flow: "no active flow",
  };
  return labels[value] || value || "unknown";
}

function decisionLine(decision) {
  if (!decision || !Object.keys(decision).length) return "unknown";
  const allowed = decision.allowed ?? decision.triggered ?? false;
  return `${allowed ? "triggered" : "not triggered"} / ${decision.reason || decision.decision || "no reason"}`;
}
