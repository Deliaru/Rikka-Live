import { api } from "./api.js";
import { $ } from "./dom.js";

let expressionPresets = {};
let gestureMap = {};
let currentPresetName = "neutral";
let currentPresetType = "expression"; // 'expression' or 'gesture'
let livePreviewEnabled = false;
let wsConnection = null;
let pendingPreviewSocketCallbacks = [];

export function setupLive2dTuning() {
  const presetTypeSelect = $("preset-type-select");
  const presetSelect = $("expression-preset-select");
  const addPresetBtn = $("add-expression-preset");
  const deletePresetBtn = $("delete-expression-preset");
  const addParamBtn = $("add-param-button");
  const addParamInput = $("add-param-id");
  const saveBtn = $("save-live2d-presets");
  const livePreviewCheckbox = $("live-preview-enabled");
  const previewNowBtn = $("preview-now");

  presetTypeSelect.addEventListener("change", () => {
    currentPresetType = presetTypeSelect.value;
    renderPresetSelect();
    renderPresetParams();
  });

  presetSelect.addEventListener("change", () => {
    currentPresetName = presetSelect.value;
    renderPresetParams();
  });

  addPresetBtn.addEventListener("click", () => {
    const name = prompt("新预设名称 (英文标识):");
    if (!name || !name.trim()) return;
    const label = prompt("预设标签 (中文):");

    if (currentPresetType === "expression") {
      expressionPresets[name.trim()] = {
        label: label || name.trim(),
        parameters: {},
        fade_ms: 300,
        hold_after_speech_ms: 2000,
      };
    } else {
      gestureMap[name.trim()] = {
        kind: "nod",
        amplitude: 1.0,
        duration_ms: 1000,
        cooldown_ms: 1200,
      };
    }

    renderPresetSelect();
    presetSelect.value = name.trim();
    currentPresetName = name.trim();
    renderPresetParams();
  });

  deletePresetBtn.addEventListener("click", () => {
    if (currentPresetName === "neutral") {
      alert("neutral 预设不可删除");
      return;
    }
    if (!confirm(`确定删除预设 "${currentPresetName}"?`)) return;

    if (currentPresetType === "expression") {
      delete expressionPresets[currentPresetName];
    } else {
      delete gestureMap[currentPresetName];
    }

    currentPresetName = Object.keys(currentPresetType === "expression" ? expressionPresets : gestureMap)[0] || "neutral";
    renderPresetSelect();
    renderPresetParams();
  });

  addParamBtn.addEventListener("click", () => {
    const paramId = addParamInput.value.trim();
    if (!paramId || currentPresetType !== "expression") return;

    const preset = expressionPresets[currentPresetName];
    if (!preset) return;
    if (!preset.parameters) preset.parameters = {};
    if (preset.parameters[paramId] === undefined) {
      preset.parameters[paramId] = 0;
    }
    addParamInput.value = "";
    renderPresetParams();
  });

  livePreviewCheckbox.addEventListener("change", () => {
    livePreviewEnabled = livePreviewCheckbox.checked;
  });

  previewNowBtn.addEventListener("click", () => {
    sendLivePreview();
  });

  saveBtn.addEventListener("click", async () => {
    try {
      const idleMicroEnabled = $("idle-micro-enabled").checked;
      const idleMicroAmplitude = parseFloat($("idle-micro-amplitude").value) || 1.0;
      const speakingSmileGain = parseFloat($("speaking-smile-gain").value) || 0.02;
      const speakingSmileMax = parseFloat($("speaking-smile-max").value) || 0.25;
      const payload = {
        expressionPresets,
        gestureMap,
        idleMicro: {
          enabled: idleMicroEnabled,
          amplitude: idleMicroAmplitude,
        },
        speakingSmile: {
          gain: speakingSmileGain,
          max: speakingSmileMax,
        },
      };
      await api.patchLive2dPresets(payload);
      alert("预设已保存并广播到 Overlay");
    } catch (err) {
      alert(`保存失败: ${err.message}`);
    }
  });

  loadPresets();
}

async function loadPresets() {
  try {
    const data = await api.getLive2dPresets();
    expressionPresets = data.expressionPresets || {};
    gestureMap = data.gestureMap || {};
    const idleMicro = data.idleMicro || {};
    const speakingSmile = data.speakingSmile || {};
    $("idle-micro-enabled").checked = idleMicro.enabled !== false;
    $("idle-micro-amplitude").value = idleMicro.amplitude || 1.0;
    $("speaking-smile-gain").value = speakingSmile.gain || 0.02;
    $("speaking-smile-max").value = speakingSmile.max || 0.25;
    renderPresetSelect();
    renderPresetParams();
  } catch (err) {
    console.error("Failed to load Live2D presets:", err);
  }
}

function renderPresetSelect() {
  const select = $("expression-preset-select");
  select.innerHTML = "";

  const presets = currentPresetType === "expression" ? expressionPresets : gestureMap;
  for (const [name, preset] of Object.entries(presets)) {
    const opt = document.createElement("option");
    opt.value = name;
    const displayLabel = currentPresetType === "expression"
      ? `${name} (${preset.label || name})`
      : `${name} [${preset.kind || "gesture"}]`;
    opt.textContent = displayLabel;
    select.appendChild(opt);
  }

  if (!presets[currentPresetName]) {
    currentPresetName = Object.keys(presets)[0] || (currentPresetType === "expression" ? "neutral" : "nod");
  }
  select.value = currentPresetName;
}

function renderPresetParams() {
  const grid = $("expression-params-grid");
  grid.innerHTML = "";

  const fadeInput = $("expression-fade-ms");
  const holdInput = $("expression-hold-ms");
  const addParamBtn = $("add-param-button");
  const addParamInput = $("add-param-id");

  if (currentPresetType === "expression") {
    const preset = expressionPresets[currentPresetName];
    if (!preset) return;

    // Show parameter inputs
    addParamBtn.style.display = "";
    addParamInput.style.display = "";
    addParamInput.parentElement.style.display = "";

    const params = preset.parameters || {};
    for (const [paramId, value] of Object.entries(params)) {
      const row = document.createElement("div");
      row.className = "param-row";
      const label = document.createElement("label");
      label.textContent = paramId;
      const input = document.createElement("input");
      input.type = "number";
      input.step = "0.05";
      input.min = "-3";
      input.max = "3";
      input.value = value;
      input.addEventListener("input", () => {
        params[paramId] = parseFloat(input.value) || 0;
        if (livePreviewEnabled) sendLivePreview();
      });
      const removeBtn = document.createElement("button");
      removeBtn.textContent = "×";
      removeBtn.className = "button ghost";
      removeBtn.addEventListener("click", () => {
        delete params[paramId];
        renderPresetParams();
      });
      row.appendChild(label);
      row.appendChild(input);
      row.appendChild(removeBtn);
      grid.appendChild(row);
    }

    fadeInput.value = preset.fade_ms || 300;
    holdInput.value = preset.hold_after_speech_ms || 2000;
    fadeInput.onchange = () => { preset.fade_ms = parseInt(fadeInput.value) || 300; };
    holdInput.onchange = () => { preset.hold_after_speech_ms = parseInt(holdInput.value) || 2000; };
    fadeInput.parentElement.style.display = "";
    holdInput.parentElement.style.display = "";
  } else {
    // Gesture mode
    const gesture = gestureMap[currentPresetName];
    if (!gesture) return;

    // Hide parameter inputs
    addParamBtn.style.display = "none";
    addParamInput.style.display = "none";
    addParamInput.parentElement.style.display = "none";
    fadeInput.parentElement.style.display = "none";
    holdInput.parentElement.style.display = "none";

    // Show gesture properties
    const fields = [
      { key: "kind", label: "Kind", type: "select", options: ["nod", "tilt", "lean_in", "look_away", "greeting_bob", "think_pose"] },
      { key: "amplitude", label: "Amplitude", type: "number", min: 0, max: 2, step: 0.1 },
      { key: "duration_ms", label: "Duration (ms)", type: "number", min: 100, max: 5000, step: 100 },
      { key: "cooldown_ms", label: "Cooldown (ms)", type: "number", min: 0, max: 10000, step: 100 },
    ];

    for (const field of fields) {
      const row = document.createElement("div");
      row.className = "param-row";
      const label = document.createElement("label");
      label.textContent = field.label;

      let input;
      if (field.type === "select") {
        input = document.createElement("select");
        for (const opt of field.options) {
          const option = document.createElement("option");
          option.value = opt;
          option.textContent = opt;
          input.appendChild(option);
        }
        input.value = gesture[field.key] || field.options[0];
      } else {
        input = document.createElement("input");
        input.type = field.type;
        input.min = field.min;
        input.max = field.max;
        input.step = field.step;
        input.value = gesture[field.key] || 0;
      }

      input.addEventListener("change", () => {
        gesture[field.key] = field.type === "number" ? parseFloat(input.value) : input.value;
      });

      row.appendChild(label);
      row.appendChild(input);
      grid.appendChild(row);
    }
  }
}

function sendLivePreview() {
  if (currentPresetType === "gesture") {
    sendGesturePreview();
    return;
  }
  const preset = expressionPresets[currentPresetName];
  if (!preset) {
    console.log("[Preview] Skipped: no preset found");
    return;
  }
  if (!preset.parameters || Object.keys(preset.parameters).length === 0) {
    console.log("[Preview] Skipped: no parameters to preview");
    return;
  }

  console.log("[Preview] Sending preview for", currentPresetName, preset.parameters);

  ensurePreviewSocket(sendLivePreviewMessage);
}

function ensurePreviewSocket(onReady) {
  if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
    onReady();
    return;
  }

  pendingPreviewSocketCallbacks.push(onReady);
  if (wsConnection && wsConnection.readyState === WebSocket.CONNECTING) return;

  console.log("[Preview] Creating new WebSocket connection");
  const wsUrl = location.protocol === "https:" ? "wss" : "ws";
  wsConnection = new WebSocket(`${wsUrl}://${location.host}/client-ws`);

  wsConnection.addEventListener("open", () => {
    console.log("[Preview] WebSocket connected, registering as console");
    wsConnection.send(JSON.stringify({
      type: "client-capabilities",
      client_kind: "console",
    }));
    setTimeout(flushPreviewSocketCallbacks, 200);
  });

  wsConnection.addEventListener("error", (err) => {
    console.error("[Preview] WebSocket error:", err);
  });

  wsConnection.addEventListener("close", () => {
    console.log("[Preview] WebSocket closed");
    wsConnection = null;
    pendingPreviewSocketCallbacks = [];
  });
  wsConnection.addEventListener("message", handlePreviewSocketMessage);
}

function flushPreviewSocketCallbacks() {
  const callbacks = pendingPreviewSocketCallbacks;
  pendingPreviewSocketCallbacks = [];
  for (const callback of callbacks) callback();
}

function handlePreviewSocketMessage(event) {
  try {
    const payload = JSON.parse(event.data);
    if (payload.type === "live2d-param-preview-ack") {
      console.log("[Preview] Backend ack:", payload);
    } else if (payload.type === "live2d-param-preview-result") {
      console.log("[Preview] Overlay result:", payload);
    } else if (payload.type === "live2d-gesture-preview-ack") {
      console.log("[Gesture Preview] Backend ack:", payload);
    } else if (payload.type === "live2d-gesture-preview-result") {
      console.log("[Gesture Preview] Overlay result:", payload);
    }
  } catch (_error) {
    // Ignore non-JSON messages from the shared websocket.
  }
}

function sendLivePreviewMessage() {
  const preset = expressionPresets[currentPresetName];
  if (!preset || !wsConnection || wsConnection.readyState !== WebSocket.OPEN) {
    console.log("[Preview] Cannot send: connection not ready or preset missing");
    return;
  }

  const message = {
    type: "live2d-param-preview",
    parameters: preset.parameters,
    ttl_ms: 1500,
  };

  console.log("[Preview] Sending message:", message);
  wsConnection.send(JSON.stringify(message));
  console.log("[Preview] Message sent successfully");
}

function sendGesturePreview() {
  const gesture = gestureMap[currentPresetName];
  if (!gesture) {
    console.log("[Gesture Preview] Skipped: no gesture found");
    return;
  }
  ensurePreviewSocket(sendGesturePreviewMessage);
}

function sendGesturePreviewMessage() {
  const gesture = gestureMap[currentPresetName];
  if (!gesture || !wsConnection || wsConnection.readyState !== WebSocket.OPEN) {
    console.log("[Gesture Preview] Cannot send: connection not ready or gesture missing");
    return;
  }
  const message = {
    type: "live2d-gesture-preview",
    name: currentPresetName,
    gesture,
  };
  console.log("[Gesture Preview] Sending message:", message);
  wsConnection.send(JSON.stringify(message));
}
