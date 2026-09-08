(function () {
  "use strict";

  function endpointDefaults() {
    var protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    var host = window.location.host || "127.0.0.1:12395";
    return {
      baseUrl: window.location.origin,
      wsUrl: protocol + "//" + host + "/client-ws",
    };
  }

  function setJson(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.warn("[Rikka] Failed to write frontend default", key, error);
    }
  }

  function absoluteUrl(path) {
    if (!path || typeof path !== "string") return path;
    try {
      return new URL(path, window.location.origin).href;
    } catch (error) {
      return path;
    }
  }

  function replaceOldEndpoint(key, nextValue) {
    try {
      var current = window.localStorage.getItem(key);
      if (!current || current.indexOf("12393") !== -1 || current.indexOf("localhost") !== -1) {
        setJson(key, nextValue);
      }
    } catch (error) {
      setJson(key, nextValue);
    }
  }

  function defaultRikkaModelInfo() {
    return {
      name: "rikka_mikazuki",
      description: "Local prepared Yayotsuki Rikka Live2D model.",
      url: absoluteUrl("/live2d-models/rikka_mikazuki/rikka_mikazuki.model3.json"),
      kScale: 0.28,
      initialXshift: 0,
      initialYshift: 0,
      kXOffset: 1150,
      idleMotionGroupName: "Idle",
      scrollToResize: true,
      pointerInteractive: true,
    };
  }

  function ensureModelDefault() {
    try {
      var raw = window.localStorage.getItem("modelInfo");
      var modelInfo = raw ? JSON.parse(raw) : null;
      var url = modelInfo && typeof modelInfo.url === "string" ? modelInfo.url : "";
      var name = modelInfo && typeof modelInfo.name === "string" ? modelInfo.name : "";
      if (!modelInfo || !url || !name || url.indexOf("undefined") !== -1 || name === "undefined") {
        setJson("modelInfo", defaultRikkaModelInfo());
      } else if (url.indexOf("http://") !== 0 && url.indexOf("https://") !== 0) {
        modelInfo.url = absoluteUrl(url);
        setJson("modelInfo", modelInfo);
      }
    } catch (error) {
      setJson("modelInfo", defaultRikkaModelInfo());
    }
  }

  var defaults = endpointDefaults();
  window.RikkaConnectionDefaults = defaults;
  replaceOldEndpoint("wsUrl", defaults.wsUrl);
  replaceOldEndpoint("baseUrl", defaults.baseUrl);
  ensureModelDefault();

  try {
    var background = window.localStorage.getItem("backgroundUrl");
    if (background && background.indexOf("12393") !== -1) {
      window.localStorage.removeItem("backgroundUrl");
    }
  } catch (error) {
    // Non-critical: a stale background URL should not block the main websocket.
  }
})();
