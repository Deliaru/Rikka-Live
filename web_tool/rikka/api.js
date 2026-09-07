async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  if (!response.ok) {
    const detail = data.detail || data.error || response.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  health: () => requestJson("/rikka/health"),
  events: () => requestJson("/rikka/events"),
  clients: () => requestJson("/rikka/debug/clients"),
  flow: () => requestJson("/rikka/debug/flow"),
  config: () => requestJson("/rikka/debug/config"),
  logs: () => requestJson("/rikka/debug/logs?max_files=8&max_lines=80"),
  errors: () => requestJson("/rikka/debug/errors"),
  settings: () => requestJson("/rikka/settings"),
  captureStatus: () => requestJson("/rikka/capture/status"),
  captureWindows: () => requestJson("/rikka/capture/windows"),
  captureKeyframe: () => requestJson("/rikka/capture/keyframe", { method: "POST", body: "{}" }),
  proactiveStatus: () => requestJson("/rikka/proactive/status"),
  overlayStatus: () => requestJson("/rikka/overlay/status"),
  multimodalKeyframe: () => requestJson("/rikka/multimodal/keyframe", {
    method: "POST",
    body: JSON.stringify({ reason: "manual_debug", event_id: null }),
  }),
  debugSpeak: (payload) => requestJson("/rikka/debug/speak", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  debugEvent: (payload) => requestJson("/rikka/debug/event", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  bilibiliStatus: () => requestJson("/rikka/bilibili/status"),
  bilibiliConnect: (payload) => requestJson("/rikka/bilibili/connect", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  bilibiliDisconnect: () => requestJson("/rikka/bilibili/disconnect", {
    method: "POST",
    body: "{}",
  }),
  bilibiliTestEvent: (payload) => requestJson("/rikka/bilibili/test-event", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  patchSettings: (payload) => requestJson("/rikka/settings", {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  resetSettings: () => requestJson("/rikka/settings/reset", { method: "POST", body: "{}" }),
  patchConfig: (payload) => requestJson("/rikka/debug/config", {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  patchRuntimeTts: (payload) => requestJson("/rikka/debug/runtime-tts", {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  getLive2dPresets: () => requestJson("/rikka/live2d/presets"),
  patchLive2dPresets: (payload) => requestJson("/rikka/live2d/presets", {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
};

export async function postAsrProbe(blob) {
  const form = new FormData();
  form.append("file", blob, "rikka-mic-probe.wav");
  const response = await fetch("/asr", { method: "POST", body: form });
  const text = await response.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  return { ok: response.ok, status: response.status, data };
}
