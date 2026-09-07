import { api } from "./api.js";
import { setupAlwaysOnListening } from "./always_on.js";
import { bindActions } from "./actions.js";
import { $, setPill } from "./dom.js";
import { applySettled, loadAll, loadFlow, loadLab } from "./loaders.js";
import { renderAll, setView } from "./render.js";
import { setupEmotionInputs } from "./settings.js";
import { setupLive2dTuning } from "./live2d_tuning.js";
import { state } from "./state.js";

let pollTimer = null;

function startPolling() {
  window.clearInterval(pollTimer);
  pollTimer = window.setInterval(async () => {
    if (document.hidden) return;
    if (state.view === "overview") {
      const [clients, flow, capture, proactive] = await Promise.allSettled([
        api.clients(),
        api.flow(),
        api.captureStatus(),
        api.proactiveStatus(),
      ]);
      applySettled({ clients, flow, capture, proactive });
      renderAll();
    } else if (state.view === "lab") {
      await loadLab();
    } else if (state.view === "flow") {
      await loadFlow();
    }
  }, 2500);
}

async function init() {
  setupEmotionInputs();
  setupLive2dTuning();
  bindActions();
  setupAlwaysOnListening();
  setView(location.hash.slice(1) || "overview");
  await loadAll();
  startPolling();
}

init().catch((error) => {
  setPill($("app-status"), error.message, "bad");
});
