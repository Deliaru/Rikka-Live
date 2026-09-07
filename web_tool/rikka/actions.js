import { api, postAsrProbe } from "./api.js";
import { recordMicProbe } from "./audio.js";
import { $, prettyJson, setPill, text, toneForState } from "./dom.js";
import { eventIsDiagnostic } from "./diagnostics.js";
import { loadAll, loadCapture, loadConfig, loadFlow, loadLab, loadLogs, loadSettings } from "./loaders.js";
import {
  buildBilibiliConnectPayload,
  buildBilibiliTestEventPayload,
  buildDebugConfigPatch,
  buildRuntimeTtsPatch,
  buildSettingsPatch,
  setConfigState,
} from "./settings.js";
import { state } from "./state.js";
import { renderAll, setView } from "./render.js";

export function bindActions() {
  document.querySelectorAll(".nav-button").forEach((node) => {
    node.addEventListener("click", () => setView(node.dataset.view));
  });
  $("refresh-current").addEventListener("click", refreshCurrent);
  $("test-live2d-refresh").addEventListener("click", async () => {
    state.clients = await api.clients();
    renderAll();
  });
  $("test-debug-speak").addEventListener("click", runDebugSpeak);
  $("test-capture-keyframe").addEventListener("click", runCaptureKeyframe);
  $("test-capture-windows").addEventListener("click", refreshWindows);
  $("test-multimodal").addEventListener("click", runMultimodal);
  $("test-proactive-refresh").addEventListener("click", async () => {
    state.proactive = await api.proactiveStatus();
    renderAll();
  });
  $("test-mic-permission").addEventListener("click", runMicProbe);
  $("test-asr-disabled").addEventListener("click", runAsrDisabledProbe);
  $("save-settings").addEventListener("click", saveSettings);
  $("reset-settings").addEventListener("click", resetSettings);
  $("save-debug-config").addEventListener("click", saveDebugConfig);
  $("bilibili-connect").addEventListener("click", connectBilibili);
  $("bilibili-disconnect").addEventListener("click", disconnectBilibili);
  $("bilibili-test-event").addEventListener("click", sendBilibiliTestEvent);
  $("apply-runtime-tts").addEventListener("click", applyRuntimeTts);
  $("audition-runtime-tts").addEventListener("click", auditionRuntimeTts);
  $("refresh-logs").addEventListener("click", loadLogs);
  $("copy-log-summary").addEventListener("click", copyLogSummary);
  $("recent-events").addEventListener("click", replayRecentEvent);
  window.addEventListener("hashchange", () => setView(location.hash.slice(1) || "overview"));
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refreshCurrent().catch(() => {});
  });
}

async function refreshCurrent() {
  if (state.view === "overview") return loadAll();
  if (state.view === "lab") return loadLab();
  if (state.view === "flow") return loadFlow();
  if (state.view === "config") {
    await Promise.all([loadSettings(), loadConfig(), loadCapture()]);
    renderAll();
    return;
  }
  if (state.view === "logs") return loadLogs();
}

async function runDebugSpeak() {
  setPill($("speak-state"), "running", "warn");
  const textValue = $("debug-speak-text").value.trim() || "六花，做一次 debug speak。";
  try {
    const payload = {
      event: {
        type: "system.test_event",
        source: "debug",
        text: textValue,
        actor: { display_name: "Console" },
        privacy: { contains_raw_media: false, cloud_upload_allowed: false },
      },
      speak: true,
    };
    const result = await api.debugSpeak(payload);
    text($("speak-result"), prettyJson({
      reason_code: result.response?.reason_code,
      delivery: result.delivery,
      response: result.response,
    }));
    setPill($("speak-state"), result.delivery?.ok ? "delivered" : result.delivery?.reason || "not delivered", result.delivery?.ok ? "ok" : "warn");
    await Promise.all([loadFlow(), loadLab()]);
  } catch (error) {
    text($("speak-result"), error.message);
    setPill($("speak-state"), "error", "bad");
  }
}

async function connectBilibili() {
  setPill($("bilibili-ready"), "connecting", "warn");
  try {
    const payload = buildBilibiliConnectPayload();
    const result = await api.bilibiliConnect(payload);
    applyBilibiliActionResult(result, "connected");
    await Promise.all([loadConfig(), loadFlow()]);
  } catch (error) {
    text($("bilibili-result"), error.message);
    setPill($("bilibili-ready"), "error", "bad");
  }
}

async function disconnectBilibili() {
  setPill($("bilibili-ready"), "disconnecting", "warn");
  try {
    const result = await api.bilibiliDisconnect();
    applyBilibiliActionResult(result, "disconnected");
    await Promise.all([loadConfig(), loadFlow()]);
  } catch (error) {
    text($("bilibili-result"), error.message);
    setPill($("bilibili-ready"), "error", "bad");
  }
}

async function sendBilibiliTestEvent() {
  setPill($("bilibili-ready"), "test event", "warn");
  try {
    const result = await api.bilibiliTestEvent(buildBilibiliTestEventPayload());
    applyBilibiliActionResult(result, "test sent");
    await Promise.all([loadConfig(), loadFlow()]);
  } catch (error) {
    text($("bilibili-result"), error.message);
    setPill($("bilibili-ready"), "error", "bad");
  }
}

function applyBilibiliActionResult(result, label) {
  if (result?.status) {
    state.bilibili = {
      ...(state.bilibili || {}),
      status: result.status,
    };
  }
  text($("bilibili-result"), prettyJson({
    action: label,
    state: result?.status?.state,
    connected: result?.status?.connected,
    active_room_id: result?.status?.active_room_id,
    received_events: result?.status?.received_events,
    last_delivery: result?.status?.last_delivery,
    result: result?.result,
  }));
  renderAll();
}

async function runCaptureKeyframe() {
  setPill($("capture-state"), "running", "warn");
  try {
    const result = await api.captureKeyframe();
    state.capture = result;
    text($("capture-result"), prettyJson({
      ...result,
      next_step: result.capture?.status === "captured"
        ? "现在可以通过 Overlay/正常对话问“能看到什么”，前提是已开启自动附加到用户提问。"
        : "根据状态和原因调整捕捉配置；只有 captured 才会成为可附加的 latest frame。",
    }));
    renderAll();
  } catch (error) {
    text($("capture-result"), error.message);
    setPill($("capture-state"), "blocked", "bad");
  }
}

async function refreshWindows() {
  try {
    const result = await api.captureWindows();
    state.windows = result;
    text($("capture-result"), prettyJson(result));
  } catch (error) {
    text($("capture-result"), error.message);
  }
}

async function runMultimodal() {
  try {
    const result = await api.multimodalKeyframe();
    text($("capture-result"), prettyJson({
      ...result,
      e2e_test: "真正的 E2E 测试是通过 Overlay/正常对话提问，并让 latest frame 附加到 BatchInput.images。",
      next_step: result.latest_frame
        ? "已有 latest frame；确认已开启自动附加到用户提问，然后通过 Overlay/正常对话问“能看到什么”。"
        : `当前没有 latest frame：${result.no_frame_reason || "unknown"}。先按状态/原因修复捕捉，再通过正常对话测试。`,
    }));
    await loadFlow();
  } catch (error) {
    text($("capture-result"), `${error.message}\n\n要测试多模态 E2E：开启捕捉、关键帧上传、自动附加到用户提问，捕获关键帧看到 captured，再通过 Overlay/正常对话问六花“能看到什么”。`);
  }
}

async function runMicProbe() {
  state.mic = {
    ...state.mic,
    status: "recording",
    permission: "prompt_or_recording",
    reason: "正在请求浏览器麦克风权限并捕获短音频",
    updatedAt: Date.now(),
  };
  renderAll();
  try {
    const blob = await recordMicProbe();
    state.mic.permission = "granted";
    state.mic.status = "captured";
    state.mic.reason = `captured ${blob.size} bytes, sending to /asr`;
    renderAll();
    const result = await postAsrProbe(blob);
    updateMicFromAsr(result);
    text($("mic-result"), prettyJson(result));
  } catch (error) {
    state.mic = {
      ...state.mic,
      status: "denied",
      permission: "denied_or_unavailable",
      reason: error.message,
      updatedAt: Date.now(),
    };
    text($("mic-result"), error.message);
  }
  renderAll();
}

async function runAsrDisabledProbe() {
  try {
    const silent = new Blob([new Uint8Array(44)], { type: "audio/wav" });
    const result = await postAsrProbe(silent);
    updateMicFromAsr(result);
    text($("mic-result"), prettyJson(result));
  } catch (error) {
    state.mic = { ...state.mic, status: "error", reason: error.message, updatedAt: Date.now() };
    text($("mic-result"), error.message);
  }
  renderAll();
}

async function saveSettings() {
  setConfigState("正在保存 Rikka 设置...");
  try {
    const result = await api.patchSettings(buildSettingsPatch());
    state.settings = result.settings;
    state.health = await api.health();
    setConfigState("Rikka 设置已保存");
    renderAll();
  } catch (error) {
    setConfigState(error.message);
  }
}

async function resetSettings() {
  setConfigState("正在重置 Rikka 设置...");
  try {
    const result = await api.resetSettings();
    state.settings = result.settings;
    setConfigState("Rikka 设置已重置");
    renderAll();
  } catch (error) {
    setConfigState(error.message);
  }
}

async function saveDebugConfig() {
  setConfigState("正在保存运行配置...");
  try {
    const result = await api.patchConfig(buildDebugConfigPatch());
    state.config = result.config;
    const [health, bilibili] = await Promise.allSettled([
      api.health(),
      api.bilibiliStatus(),
    ]);
    if (health.status === "fulfilled") state.health = health.value;
    if (bilibili.status === "fulfilled") state.bilibili = bilibili.value;
    setConfigState(result.config?.restart_required ? "配置已保存，重启后完全生效" : "配置已保存并热应用");
    renderAll();
  } catch (error) {
    setConfigState(error.message);
  }
}

async function applyRuntimeTts() {
  setConfigState("正在应用运行时 TTS...");
  try {
    const result = await api.patchRuntimeTts(buildRuntimeTtsPatch());
    state.health = await api.health();
    setConfigState(`运行时已应用: ${Object.keys(result.applied || {}).join(", ") || "ok"}`);
    renderAll();
  } catch (error) {
    setConfigState(error.message);
  }
}

async function auditionRuntimeTts() {
  await applyRuntimeTts();
  await runDebugSpeak();
}

async function copyLogSummary() {
  const errors = [
    ...(state.errors?.provider_errors || []),
    ...(state.errors?.errors || []),
  ].map((item) => `${item.source || item.file || "error"}: ${item.message || item.line || ""}`);
  const logs = (state.logs?.files || []).map((file) => `# ${file.name}\n${(file.lines || []).slice(-16).join("\n")}`);
  const payload = [...errors, ...logs].filter(Boolean).join("\n\n");
  if (!payload) return;
  await navigator.clipboard.writeText(payload);
}

async function replayRecentEvent(event) {
  const target = event.target.closest("button");
  if (!target || target.disabled) return;
  const item = state.events[Number(target.dataset.eventIndex)];
  if (!item || eventIsDiagnostic(item)) return;
  setView("lab");
  $("debug-speak-text").value = item.text || item.message || item.detail || "Recent event replay";
  await runDebugSpeak();
}

function updateMicFromAsr(result) {
  const detail = result.data?.error || result.data?.detail || result.data?.text || result.data?.transcript || "";
  const transcript = result.data?.text || result.data?.transcript || "";
  const asrDisabled = result.status === 503 && String(detail).toLowerCase().includes("disabled");
  state.mic = {
    ...state.mic,
    status: asrDisabled ? "asr_disabled" : result.ok ? "transcript_heard" : "error",
    asr: asrDisabled ? "asr_disabled" : result.ok ? "enabled" : `http_${result.status}`,
    transcript,
    wakeDecision: inferWakeDecision(transcript),
    reason: detail || (result.ok ? "ASR 返回成功" : "ASR 请求失败"),
    updatedAt: Date.now(),
  };
}

function inferWakeDecision(transcript) {
  const audio = state.settings?.audio || {};
  const phrases = [
    ...(audio.wake_phrases || []),
    ...(audio.wake_asr_confusions || []),
  ];
  if (!transcript) return "no_transcript";
  return phrases.some((phrase) => phrase && transcript.toLowerCase().includes(String(phrase).toLowerCase()))
    ? "wake gate accepted"
    : "rejected/missing";
}
