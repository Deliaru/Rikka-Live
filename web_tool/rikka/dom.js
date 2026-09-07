export const $ = (id) => document.getElementById(id);

export function text(node, value) {
  if (!node) return;
  node.textContent = value == null || value === "" ? "" : String(value);
}

export function clear(node) {
  if (!node) return;
  node.replaceChildren();
}

export function el(tag, className = "", textValue = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (textValue !== "") node.textContent = textValue;
  return node;
}

export function button(label, className = "button", disabled = false) {
  const node = el("button", className, label);
  node.type = "button";
  node.disabled = disabled;
  return node;
}

export function setPill(node, label, tone = "") {
  if (!node) return;
  node.className = `status-pill ${tone || ""}`.trim();
  node.textContent = label || "unknown";
}

export function kvList(node, rows) {
  clear(node);
  rows
    .filter(([, value]) => value !== undefined && value !== null && value !== "")
    .forEach(([key, value]) => {
      const row = el("div", "kv-row");
      row.append(el("span", "", key), el("span", "", formatValue(value)));
      node.append(row);
    });
}

export function formatValue(value) {
  if (Array.isArray(value)) return value.length ? value.join(", ") : "[]";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "object" && value) return JSON.stringify(value);
  return String(value);
}

export function prettyJson(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function age(atMs) {
  const numeric = Number(atMs);
  if (!Number.isFinite(numeric) || numeric <= 0) return "never";
  const delta = Math.max(0, Date.now() - numeric);
  if (delta < 1000) return "just now";
  if (delta < 60_000) return `${Math.round(delta / 1000)}s ago`;
  if (delta < 3_600_000) return `${Math.round(delta / 60_000)}m ago`;
  return `${Math.round(delta / 3_600_000)}h ago`;
}

export function toneForState(state) {
  const normalized = String(state || "").toLowerCase();
  if (["ok", "ready", "connected", "complete", "captured", "accepted", "applied"].includes(normalized)) return "ok";
  if (["running", "waiting", "waiting_for_target", "skipped", "disabled", "idle", "queued_stub"].includes(normalized)) return "warn";
  if (["error", "failed", "blocked", "unavailable", "denied", "rejected", "asr_disabled"].includes(normalized)) return "bad";
  return "info";
}
