import { api } from "./api.js";
import { $, setPill } from "./dom.js";
import { renderAll } from "./render.js";
import { state } from "./state.js";

export async function loadAll() {
  try {
    const [health, clients, flow, events, settings, config, bilibili, capture, proactive, overlay, logs, errors] = await Promise.allSettled([
      api.health(),
      api.clients(),
      api.flow(),
      api.events(),
      api.settings(),
      api.config(),
      api.bilibiliStatus(),
      api.captureStatus(),
      api.proactiveStatus(),
      api.overlayStatus(),
      api.logs(),
      api.errors(),
    ]);
    applySettled({
      health,
      clients,
      flow,
      events,
      settings,
      config,
      bilibili,
      capture,
      proactive,
      overlay,
      logs,
      errors,
    });
    setPill($("app-status"), "backend connected", "ok");
  } catch (error) {
    setPill($("app-status"), error.message, "bad");
  }
  renderAll();
}

export async function loadLab() {
  const [clients, capture, proactive, overlay] = await Promise.allSettled([
    api.clients(),
    api.captureStatus(),
    api.proactiveStatus(),
    api.overlayStatus(),
  ]);
  applySettled({ clients, capture, proactive, overlay });
  renderAll();
}

export async function loadFlow() {
  const [flow, events, clients] = await Promise.allSettled([
    api.flow(),
    api.events(),
    api.clients(),
  ]);
  applySettled({ flow, events, clients });
  renderAll();
}

export async function loadSettings() {
  const result = await api.settings();
  state.settings = result.settings || {};
  renderAll();
}

export async function loadConfig() {
  const [config, bilibili] = await Promise.allSettled([
    api.config(),
    api.bilibiliStatus(),
  ]);
  applySettled({ config, bilibili });
  renderAll();
}

export async function loadCapture() {
  state.capture = await api.captureStatus();
  renderAll();
}

export async function loadLogs() {
  const [logs, errors] = await Promise.allSettled([api.logs(), api.errors()]);
  applySettled({ logs, errors });
  renderAll();
}

export function applySettled(entries) {
  Object.entries(entries).forEach(([key, result]) => {
    if (result.status !== "fulfilled") return;
    if (key === "events") {
      state.events = result.value.events || [];
    } else if (key === "settings") {
      state.settings = result.value.settings || {};
    } else if (key === "config") {
      state.config = result.value.config || {};
    } else {
      state[key] = result.value;
    }
  });
}
