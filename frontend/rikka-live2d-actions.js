(function () {
  "use strict";

  var PRIORITY = {
    idle: 1,
    normal: 2,
    force: 3,
  };
  var PARAM_ALIASES = {
    ParamAngleX: ["ParamAngleX", "PARAM_ANGLE_X"],
    ParamAngleY: ["ParamAngleY", "PARAM_ANGLE_Y"],
    ParamAngleZ: ["ParamAngleZ", "PARAM_ANGLE_Z"],
    ParamEyeBallX: ["ParamEyeBallX", "PARAM_EYE_BALL_X"],
    ParamEyeBallY: ["ParamEyeBallY", "PARAM_EYE_BALL_Y"],
    ParamMouthForm: ["ParamMouthForm", "PARAM_MOUTH_FORM"],
    ParamMouthOpenY: ["ParamMouthOpenY", "PARAM_MOUTH_OPEN_Y"],
  };

  var motionCooldownUntil = new Map();
  var gazeToken = 0;
  var currentFlowId = null;
  var inspectedEvents = typeof WeakSet === "function" ? new WeakSet() : null;
  var onMessageHandlers = typeof WeakMap === "function" ? new WeakMap() : null;
  var inspectedPayloadKeys = new Map();
  var consoleLogPatched = false;

  function getAdapter() {
    return typeof window.getLAppAdapter === "function"
      ? window.getLAppAdapter()
      : null;
  }

  function getModel() {
    var adapter = getAdapter();
    return adapter && typeof adapter.getModel === "function"
      ? adapter.getModel()
      : null;
  }

  function priorityValue(value) {
    if (typeof value === "number") return value;
    return PRIORITY[String(value || "normal").toLowerCase()] || PRIORITY.normal;
  }

  function motionStarted(result) {
    return result !== false && result !== -1 && result !== null && result !== undefined;
  }

  function postAction(kind, status, detail, metadata) {
    var payload = {
      flow_id: currentFlowId,
      kind: kind,
      status: status,
      detail: detail || "",
      metadata: metadata || {},
    };
    window.RikkaLive2DActions.lastTelemetry = payload;
    try {
      fetch("/rikka/debug/frontend-action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(function () {});
    } catch (error) {
      // Telemetry must never break audio or Live2D playback.
    }
  }

  function hasMotion(adapter, group, index) {
    if (!adapter || !Number.isInteger(index)) return true;
    if (typeof adapter.getMotionCount !== "function") return true;
    try {
      return index >= 0 && index < adapter.getMotionCount(group);
    } catch (error) {
      return true;
    }
  }

  function motionMetadata(adapter, motion, group, index) {
    var groups = [];
    var count = null;
    try {
      if (adapter && typeof adapter.getMotionGroups === "function") {
        groups = adapter.getMotionGroups();
      }
      if (adapter && typeof adapter.getMotionCount === "function") {
        count = adapter.getMotionCount(group);
      }
    } catch (error) {
      // Metadata only.
    }
    return {
      name: motion && motion.name,
      group: group,
      index: index,
      motion_count: count,
      groups: groups,
    };
  }

  function applyMotion(motion, attempt) {
    if (!motion || typeof motion !== "object") return false;
    attempt = attempt || 0;

    var name = String(motion.name || motion.group || "motion");
    var cooldownMs = Number(motion.cooldown_ms || 1200);
    var now = Date.now();
    if (motionCooldownUntil.get(name) > now) {
      postAction("motion", "skipped", "cooldown", { name: name });
      return false;
    }

    var adapter = getAdapter();
    var model = adapter && typeof adapter.getModel === "function"
      ? adapter.getModel()
      : getModel();

    var group = String(motion.group || "");
    var priority = priorityValue(motion.priority);
    var index = Number(motion.index);
    var metadata = motionMetadata(adapter, motion, group, index);
    if ((!model && !adapter) || (adapter && !model)) {
      if (attempt < 20) {
        window.setTimeout(function () {
          applyMotion(motion, attempt + 1);
        }, 350);
      } else {
        postAction("motion", "error", "Live2D adapter/model not ready", metadata);
      }
      return false;
    }
    var ok = false;

    try {
      if (Number.isInteger(index) && hasMotion(adapter, group, index)) {
        if (adapter && typeof adapter.startMotion === "function") {
          ok = motionStarted(adapter.startMotion(group, index, priority));
        } else if (model && typeof model.startMotion === "function") {
          ok = motionStarted(model.startMotion(group, index, priority));
        }
      }
      if (!ok && model && typeof model.startRandomMotion === "function") {
        ok = motionStarted(model.startRandomMotion(group, priority));
      }
    } catch (error) {
      console.warn("[RikkaLive2D] motion failed", error);
      postAction("motion", "error", error.message || String(error), metadata);
      ok = false;
    }

    if (ok) motionCooldownUntil.set(name, now + cooldownMs);
    window.RikkaLive2DActions.lastMotion = {
      motion: motion,
      ok: ok,
      at: now,
    };
    postAction(
      "motion",
      ok ? "ok" : "error",
      ok ? "motion applied" : "motion API returned invalid handle",
      metadata,
    );
    return ok;
  }

  function parameterAliases(parameterId) {
    var id = String(parameterId);
    return PARAM_ALIASES[id] || [id];
  }

  function setParameter(model, adapter, parameterId, value) {
    var cubismModel = model && model._model;
    if (!cubismModel) return false;

    var idManager = adapter && typeof adapter.getIdManager === "function"
      ? adapter.getIdManager()
      : null;
    var aliases = parameterAliases(parameterId);

    for (var i = 0; i < aliases.length; i += 1) {
      var alias = aliases[i];
      var id = idManager && typeof idManager.getId === "function"
        ? idManager.getId(alias)
        : alias;
      try {
        if (typeof cubismModel.setParameterValueById === "function") {
          cubismModel.setParameterValueById(id, value);
          return true;
        }
        if (typeof cubismModel.addParameterValueById === "function") {
          cubismModel.addParameterValueById(id, value);
          return true;
        }
      } catch (error) {
        // Try the next alias. Some models mix Cubism's canonical IDs with
        // exported uppercase IDs in their motion files.
      }
    }
    return false;
  }

  function applyGaze(gaze, attempt) {
    if (!gaze || typeof gaze !== "object" || !gaze.parameters) return false;
    attempt = attempt || 0;

    var model = getModel();
    var adapter = getAdapter();
    if (!model || !adapter) {
      if (attempt < 20) {
        window.setTimeout(function () {
          applyGaze(gaze, attempt + 1);
        }, 350);
      } else {
        postAction("gaze", "error", "Live2D adapter/model not ready", {
          name: gaze.name,
        });
      }
      return false;
    }

    gazeToken += 1;
    var token = gazeToken;
    var parameters = gaze.parameters;
    var fadeMs = Math.max(0, Number(gaze.fade_ms || 220));
    var holdMs = Math.max(0, Number(gaze.hold_ms || 1200));
    var restoreMs = Math.max(0, Number(gaze.restore_ms || 700));
    var startedAt = performance.now();
    var totalMs = fadeMs + holdMs + restoreMs;

    function weightAt(elapsed) {
      if (fadeMs > 0 && elapsed < fadeMs) return elapsed / fadeMs;
      if (elapsed < fadeMs + holdMs) return 1;
      if (restoreMs <= 0) return 0;
      return Math.max(0, 1 - (elapsed - fadeMs - holdMs) / restoreMs);
    }

    function step(now) {
      if (token !== gazeToken) return;
      var elapsed = now - startedAt;
      var weight = weightAt(elapsed);
      Object.keys(parameters).forEach(function (key) {
        var target = Number(parameters[key]);
        if (Number.isFinite(target)) {
          setParameter(model, adapter, key, target * weight);
        }
      });
      if (elapsed < totalMs) {
        window.requestAnimationFrame(step);
      }
    }

    window.requestAnimationFrame(step);
    window.RikkaLive2DActions.lastGaze = {
      gaze: gaze,
      ok: true,
      at: Date.now(),
    };
    postAction("gaze", "ok", "gaze applied", {
      name: gaze.name,
      parameters: Object.keys(parameters),
    });
    return true;
  }

  function apply(actions) {
    if (!actions || typeof actions !== "object") return;
    if (Array.isArray(actions.motions)) {
      actions.motions.forEach(applyMotion);
    }
    if (actions.gaze) {
      applyGaze(actions.gaze);
    }
  }

  function shouldInspectPayload(payload) {
    if (!payload || typeof payload !== "object") return false;
    var type = String(payload.type || "");
    if (!type) return false;
    var flowId = (payload.flow && payload.flow.id)
      || (payload.event && payload.event.id)
      || currentFlowId
      || "";
    var key = payloadDedupKey(payload, type, flowId);
    var now = Date.now();
    inspectedPayloadKeys.forEach(function (at, existingKey) {
      if (now - at > 2500) inspectedPayloadKeys.delete(existingKey);
    });
    if (inspectedPayloadKeys.has(key)) return false;
    inspectedPayloadKeys.set(key, now);
    return true;
  }

  function payloadDedupKey(payload, type, flowId) {
    if (type === "audio") {
      var actions = payload.actions || {};
      var motionNames = Array.isArray(actions.motions)
        ? actions.motions.map(function (motion) {
            return [
              motion && motion.name,
              motion && motion.group,
              motion && motion.index,
            ].join("@");
          }).join(",")
        : "";
      var gazeName = actions.gaze && actions.gaze.name;
      var volumeCount = Array.isArray(payload.volumes) ? payload.volumes.length : 0;
      var text = payload.display_text && payload.display_text.text;
      return [type, flowId, volumeCount, motionNames, gazeName || "", String(text || "").slice(0, 48)].join(":");
    }
    if (type === "rikka-response") {
      var response = payload.response || {};
      return [
        type,
        flowId,
        response.reason_code || "",
        response.motion || "",
        response.gaze || "",
        String(response.subtitle_text || "").slice(0, 48),
      ].join(":");
    }
    if (type === "rikka-live-event") {
      return [
        type,
        flowId,
        payload.event && payload.event.type,
        String(payload.event && payload.event.text || "").slice(0, 48),
      ].join(":");
    }
    return [type, flowId].join(":");
  }

  function handleSocketMessage(event) {
    if (inspectedEvents && inspectedEvents.has(event)) return;
    if (inspectedEvents) inspectedEvents.add(event);
    inspectMessage(event);
  }

  function inspectMessage(event) {
    var raw = event && event.data;
    if (typeof raw !== "string") return;
    var payload;
    try {
      payload = JSON.parse(raw);
    } catch (error) {
      return;
    }
    inspectPayload(payload);
  }

  function inspectPayload(payload) {
    if (!shouldInspectPayload(payload)) return;
    if (payload && payload.type === "rikka-live-event") {
      currentFlowId = (payload.flow && payload.flow.id) || (payload.event && payload.event.id) || currentFlowId;
      postAction("receive", "ok", "frontend received Rikka event", {
        event_type: payload.event && payload.event.type,
        source: payload.event && payload.event.source,
      });
    } else if (payload && payload.type === "audio") {
      currentFlowId = (payload.flow && payload.flow.id) || currentFlowId;
      postAction("audio", "ok", payload.actions ? "audio with actions received" : "audio received", {
        has_audio: Boolean(payload.audio),
        has_actions: Boolean(payload.actions),
        volume_points: Array.isArray(payload.volumes) ? payload.volumes.length : 0,
      });
      if (payload.actions) {
        apply(payload.actions);
      }
    } else if (payload && payload.type === "rikka-response") {
      currentFlowId = (payload.flow && payload.flow.id) || currentFlowId;
      postAction("response", "ok", "frontend received structured response", {
        reason_code: payload.response && payload.response.reason_code,
        motion: payload.response && payload.response.motion,
        gaze: payload.response && payload.response.gaze,
        has_actions: Boolean(payload.actions),
      });
    }
  }

  function patchOnMessageSetter(NativeWebSocket) {
    var descriptor = null;
    var cursor = NativeWebSocket.prototype;
    while (cursor && !descriptor) {
      descriptor = Object.getOwnPropertyDescriptor(cursor, "onmessage");
      cursor = Object.getPrototypeOf(cursor);
    }
    if (NativeWebSocket.prototype.__rikkaOnMessagePatched) return;
    try {
      Object.defineProperty(NativeWebSocket.prototype, "onmessage", {
        configurable: true,
        enumerable: descriptor ? descriptor.enumerable : true,
        get: function () {
          if (descriptor && typeof descriptor.get === "function") {
            return descriptor.get.call(this);
          }
          var stored = onMessageHandlers && onMessageHandlers.get(this);
          return stored ? stored.handler : null;
        },
        set: function (handler) {
          if (typeof handler !== "function" || handler.__rikkaActionWrapped) {
            if (descriptor && typeof descriptor.set === "function") {
              descriptor.set.call(this, handler);
            }
            return;
          }
          var wrapped = function (event) {
            handleSocketMessage(event);
            return handler.call(this, event);
          };
          wrapped.__rikkaActionWrapped = true;
          if (descriptor && typeof descriptor.set === "function") {
            descriptor.set.call(this, wrapped);
            return;
          }
          var previous = onMessageHandlers && onMessageHandlers.get(this);
          if (previous && previous.wrapped) {
            this.removeEventListener("message", previous.wrapped);
          }
          if (onMessageHandlers) {
            onMessageHandlers.set(this, { handler: handler, wrapped: wrapped });
          }
          this.addEventListener("message", wrapped);
        },
      });
      NativeWebSocket.prototype.__rikkaOnMessagePatched = true;
    } catch (error) {
      console.warn("[RikkaLive2D] failed to patch WebSocket.onmessage", error);
    }
  }

  function patchWebSocket() {
    var NativeWebSocket = window.WebSocket;
    if (!NativeWebSocket || NativeWebSocket.__rikkaActionPatched) return;

    patchOnMessageSetter(NativeWebSocket);

    function RikkaWebSocket(url, protocols) {
      var socket = protocols === undefined
        ? new NativeWebSocket(url)
        : new NativeWebSocket(url, protocols);
      socket.addEventListener("message", handleSocketMessage);
      return socket;
    }

    RikkaWebSocket.prototype = NativeWebSocket.prototype;
    Object.setPrototypeOf(RikkaWebSocket, NativeWebSocket);
    ["CONNECTING", "OPEN", "CLOSING", "CLOSED"].forEach(function (key) {
      try {
        Object.defineProperty(RikkaWebSocket, key, {
          configurable: true,
          enumerable: true,
          value: NativeWebSocket[key],
        });
      } catch (error) {
        // The native constructor exposes these constants through its prototype
        // chain in modern Chromium; copying them is only best-effort metadata.
      }
    });
    RikkaWebSocket.__rikkaActionPatched = true;
    window.WebSocket = RikkaWebSocket;
  }

  function patchConsoleLog() {
    if (consoleLogPatched || !window.console || typeof window.console.log !== "function") return;
    var nativeLog = window.console.log.bind(window.console);
    window.console.log = function () {
      var first = arguments.length > 0 ? arguments[0] : null;
      var payload = arguments.length > 1 ? arguments[1] : null;
      if (first === "Received message from server:" && payload && typeof payload === "object") {
        try {
          inspectPayload(payload);
        } catch (error) {
          console.warn("[RikkaLive2D] inspectPayload from console hook failed", error);
        }
      }
      return nativeLog.apply(null, arguments);
    };
    consoleLogPatched = true;
  }

  window.RikkaLive2DActions = {
    apply: apply,
    applyMotion: applyMotion,
    applyGaze: applyGaze,
    inspectPayload: inspectPayload,
  };
  patchWebSocket();
  patchConsoleLog();
  window.setTimeout(function () {
    postAction("bridge", "ok", "Live2D action bridge loaded", {
      patched: Boolean(window.WebSocket && window.WebSocket.__rikkaActionPatched),
      console_hook: consoleLogPatched,
    });
  }, 0);
})();
