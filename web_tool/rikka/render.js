import { $, age, button, clear, el, kvList, prettyJson, setPill, text, toneForState } from "./dom.js";
import { captureRows, eventIsDiagnostic, latestFrontendAction, micRows, proactiveRows, readiness } from "./diagnostics.js";
import { renderConfigForm, renderSettingsForm } from "./settings.js";
import { state, viewMeta } from "./state.js";

const stageLabels = {
  event: "事件",
  normalize: "归一",
  planner: "LLM",
  validate: "校验",
  memory: "记忆",
  delivery: "投递",
  tts: "TTS",
  live2d: "Live2D",
  actions: "动作",
  complete: "完成",
};

function formatDurationMs(value) {
  const duration = Number(value);
  if (!Number.isFinite(duration)) return "耗时 -";
  if (duration < 1000) return `耗时 ${Math.round(duration)} ms`;
  return `耗时 ${(duration / 1000).toFixed(duration < 10000 ? 2 : 1)} s`;
}

function displayDurationMs(item) {
  if (item?.status === "running" && item.at_ms) {
    return Math.max(0, Date.now() - Number(item.at_ms));
  }
  return item?.duration_ms;
}

function eventFlowId(event) {
  return event?.payload?.flow_id || event?.flow_id || "";
}

function eventLabel(event) {
  return `${event?.type || event?.kind || "event"} / ${event?.source || event?.platform || "unknown"}`;
}

function eventDetail(event) {
  return `${event?.text || event?.message || event?.detail || ""} ${event?.created_at_ms ? age(event.created_at_ms) : ""}`.trim();
}

function groupRecentEvents(events) {
  const groups = [];
  const byFlow = new Map();
  events.forEach((event, index) => {
    const flowId = eventFlowId(event);
    if (!flowId) {
      groups.push({
        key: `event-${index}`,
        flowId: "",
        items: [{ event, index }],
      });
      return;
    }
    if (!byFlow.has(flowId)) {
      const group = { key: `flow-${flowId}`, flowId, items: [] };
      byFlow.set(flowId, group);
      groups.push(group);
    }
    byFlow.get(flowId).items.push({ event, index });
  });
  return groups;
}

function groupPrimaryEvent(group) {
  return (
    group.items.find((item) => !eventIsDiagnostic(item.event)) ||
    group.items[0] ||
    { event: {}, index: -1 }
  );
}

function validationDiagnosticsFromFlow(active) {
  const candidates = [
    active?.stages?.validate?.metadata,
    active?.stages?.planner?.metadata,
    ...((active?.timeline || []).map((entry) => entry.metadata).reverse()),
  ];
  return candidates.find((metadata) => metadata?.failure_kind || metadata?.raw_response_hash) || null;
}

function diagnosticValue(value) {
  if (Array.isArray(value)) return value.length ? value.join("\n") : "[]";
  if (typeof value === "object" && value) return prettyJson(value);
  return value == null ? "" : String(value);
}

function diagnosticRow(label, value, { long = false } = {}) {
  if (value === undefined || value === null || value === "") return null;
  const row = el("div", `diagnostic-row${long ? " long" : ""}`);
  row.append(el("span", "diagnostic-label", label));
  row.append(el(long ? "pre" : "span", "diagnostic-value", diagnosticValue(value)));
  return row;
}

// ---- 渲染去抖：内容指纹 + 滚动位置保护 ----
// 轮询每 2.5s 触发 renderFlow，若每次都 clear()+重建会丢失滚动位置。
// 用稳定字段算指纹，指纹未变则跳过该区域重建；需要重建时保存/恢复
// 容器自身 scrollTop（现已改为固定高度内部滚动容器）。

function stageGridFingerprint(stages) {
  return Object.entries(stageLabels)
    .map(([key]) => {
      const stage = stages[key] || {};
      return `${key}:${stage.status || ""}|${stage.detail || stage.reason || ""}`;
    })
    .join("##");
}

function timelineFingerprint(active) {
  return (active.timeline || [])
    .slice(-12)
    .map((entry) => `${entry.stage || ""}|${entry.status || ""}|${entry.at_ms || ""}|${entry.detail || ""}`)
    .join("##");
}

function eventListFingerprint(groups) {
  return groups
    .slice(0, 16)
    .map((group) => {
      const primary = groupPrimaryEvent(group).event;
      return `${group.key}|${primary?.type || ""}|${primary?.source || ""}|${primary?.text || ""}|${group.items.length}`;
    })
    .join("##");
}

// 在重建容器前保存其 scrollTop，重建后恢复。仅对滚动容器有意义。
function withScrollPreserved(node, rebuild) {
  const savedScrollTop = node.scrollTop;
  rebuild();
  node.scrollTop = savedScrollTop;
}

function renderValidationDiagnostics(active) {
  const metadata = validationDiagnosticsFromFlow(active);
  if (!metadata) return null;
  const panel = el("div", "stage-cell validation-diagnostics");
  panel.append(el("strong", "", `LLM 诊断: ${metadata.failure_kind || "validation"}`));
  const list = el("div", "validation-diagnostics-list");
  [
    diagnosticRow("长度 / hash", `${metadata.raw_response_length ?? "-"} / ${metadata.raw_response_hash || "-"}`),
    diagnosticRow("安全摘录", metadata.raw_response_excerpt, { long: true }),
    diagnosticRow("模型原始返回", metadata.raw_response_text, { long: true }),
    diagnosticRow("本地修复", metadata.repair_notes, { long: true }),
    diagnosticRow("校验错误", metadata.errors, { long: true }),
    diagnosticRow("fallback", metadata.fallback_reason_code || (metadata.fallback ? "used" : "none")),
    diagnosticRow("fallback 预览", metadata.fallback_spoken_preview || metadata.fallback_subtitle_preview, { long: true }),
    diagnosticRow("图片数量", metadata.attached_image_count ?? 0),
  ].filter(Boolean).forEach((row) => list.append(row));
  panel.append(list);
  return panel;
}

export function renderAll() {
  renderChrome();
  renderOverview();
  renderLab();
  renderFlow();
  renderConfig();
  renderLogs();
}

export function renderChrome() {
  const [title, subtitle] = viewMeta[state.view] || viewMeta.overview;
  text($("view-title"), title);
  text($("view-subtitle"), subtitle);
  document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${state.view}`));
  document.querySelectorAll(".nav-button").forEach((nav) => nav.classList.toggle("active", nav.dataset.view === state.view));
  setPill($("app-status"), state.health?.ok ? "backend connected" : "connecting", state.health?.ok ? "ok" : "warn");
  text($("last-refresh"), `刷新 ${new Date().toLocaleTimeString()}`);
}

export function renderOverview() {
  const summary = readiness(state);
  const grid = $("overview-grid");
  clear(grid);
  summary.metrics.forEach((metric) => {
    const card = el("section", "panel metric-card");
    card.append(el("span", "metric-label", metric.label));
    card.append(el("strong", "metric-value", metric.value));
    card.append(el("p", "metric-detail", metric.detail));
    card.append(status(metric.state));
    grid.append(card);
  });

  setPill($("blocker-tone"), summary.blocker.key, summary.blocker.tone);
  text($("blocker-title"), summary.blocker.title);
  text($("blocker-detail"), summary.blocker.detail);

  const actions = $("next-actions");
  clear(actions);
  actions.append(actionLink("打开 Overlay", "/overlay/"));
  const lab = button("进入测试台", "button primary");
  lab.addEventListener("click", () => setView("lab"));
  actions.append(lab);

  const action = latestFrontendAction(state.flow);
  setPill($("frontend-action-age"), action ? age(action.at_ms) : "none", action ? toneForState(action.status) : "warn");
  kvList($("frontend-action-detail"), action ? [
    ["flow", action.flow_id || "none"],
    ["kind", action.kind || "unknown"],
    ["status", action.status || "unknown"],
    ["detail", action.detail || ""],
    ["metadata", action.metadata || {}],
  ] : [["状态", "尚无 Overlay 前端动作回执"]]);
}

export function renderLab() {
  const clients = state.clients || {};
  const capture = state.capture || {};
  const proactive = state.proactive || {};
  const mic = state.mic || {};
  const settings = state.settings || {};
  const micAction = latestFrontendAction(state.flow, "mic");
  const wakeAction = latestFrontendAction(state.flow, "wake");

  const liveCount = Number(clients.connected_clients || 0);
  setPill($("live2d-state"), liveCount > 0 ? "connected" : "offline", liveCount > 0 ? "ok" : "warn");
  text($("live2d-detail"), `${liveCount} client(s), bridge ${clients.live2d_bridge_ready ? "ready" : "not ready"}`);

  setPill($("capture-state"), capture.capture?.status || "unknown", toneForState(capture.capture?.status));
  kvList($("capture-detail"), captureRows(capture));

  const proactiveState = proactive.proactive?.last_decision || proactive.proactive?.status || "unknown";
  setPill($("proactive-state"), proactiveState, toneForState(proactiveState));
  kvList($("proactive-detail"), proactiveRows(proactive));

  const micState = wakeAction?.detail || micAction?.detail || mic.status || "unknown";
  setPill($("mic-state"), micState, toneForState(wakeAction?.status || micAction?.status || mic.status));
  if ($("mic-owner-state")) {
    const ownerLabel = mic.owner?.client_kind
      ? `${mic.owner.client_kind}${mic.owner.client_uid === mic.clientUid ? " owner" : " owner elsewhere"}`
      : "no owner";
    setPill($("mic-owner-state"), ownerLabel, mic.owner?.client_uid === mic.clientUid ? "ok" : "warn");
  }
  kvList($("mic-detail"), micRows(mic, settings, { mic: micAction, wake: wakeAction }));
}

export function renderFlow() {
  const flow = state.flow || {};
  const active = flow.active || flow.flows?.[0] || {};
  setPill($("flow-state"), active.status || "no active flow", toneForState(active.status));

  const stages = active.stages || {};

  // ---- stage grid：按指纹决定是否重建 ----
  const stageGrid = $("flow-stage-grid");
  const stageFp = stageGridFingerprint(stages);
  if (state.flowFingerprints.stageGrid !== stageFp) {
    clear(stageGrid);
    Object.entries(stageLabels).forEach(([key, label]) => {
      const stage = stages[key] || {};
      const cell = el("div", "stage-cell");
      cell.append(el("strong", "", `${label}: ${stage.status || "pending"} · ${formatDurationMs(displayDurationMs(stage))}`));
      cell.append(el("small", "", stage.detail || stage.reason || ""));
      stageGrid.append(cell);
    });
    const validationPanel = renderValidationDiagnostics(active);
    if (validationPanel) stageGrid.append(validationPanel);
    state.flowFingerprints.stageGrid = stageFp;
  }

  // ---- timeline：按指纹决定是否重建，重建时保护 scrollTop ----
  const timeline = $("flow-timeline");
  const timelineFp = timelineFingerprint(active);
  if (state.flowFingerprints.timeline !== timelineFp) {
    withScrollPreserved(timeline, () => {
      clear(timeline);
      (active.timeline || []).slice(-12).reverse().forEach((entry) => {
        const row = el("div", "timeline-row");
        row.append(el("strong", "", `${stageLabels[entry.stage] || entry.stage || "stage"} / ${entry.status || "unknown"}`));
        row.append(el("small", "", `${age(entry.at_ms)} · ${formatDurationMs(displayDurationMs(entry))} ${entry.detail || ""}`));
        timeline.append(row);
      });
      if (!timeline.children.length) timeline.append(el("div", "timeline-row", "暂无 flow timeline"));
    });
    state.flowFingerprints.timeline = timelineFp;
  }

  // ---- event-list：按指纹决定是否重建，重建时保护 scrollTop ----
  const groups = groupRecentEvents(state.events || []);
  const events = $("recent-events");
  const eventListFp = eventListFingerprint(groups.reverse());
  if (state.flowFingerprints.eventList !== eventListFp) {
    withScrollPreserved(events, () => {
      clear(events);
      groups.slice(0, 16).forEach((group) => {
        const primary = groupPrimaryEvent(group);
        const diagnostic = eventIsDiagnostic(primary.event);
        const row = el(group.items.length > 1 ? "details" : "div", "event-row event-group");
        row.dataset.diagnostic = diagnostic ? "true" : "false";
        if (group.flowId) row.dataset.flowId = group.flowId;
        if (row.tagName === "DETAILS") {
          row.open = state.expandedEventGroups.has(group.key);
          row.addEventListener("toggle", () => {
            if (row.open) {
              state.expandedEventGroups.add(group.key);
            } else {
              state.expandedEventGroups.delete(group.key);
            }
          });
        }

        const header = group.items.length > 1 ? el("summary", "event-summary") : el("div", "event-summary");
        const title = el("div", "event-title");
        title.append(el("strong", "", eventLabel(primary.event)));
        title.append(el("small", "", eventDetail(primary.event)));
        header.append(title);
        header.append(el("span", "status-pill info", group.flowId ? `flow ${group.items.length}` : "single"));
        row.append(header);

        if (group.items.length > 1) {
          const detailList = el("div", "event-group-items");
          group.items.slice().reverse().forEach(({ event }) => {
            const item = el("div", "event-child");
            item.dataset.diagnostic = eventIsDiagnostic(event) ? "true" : "false";
            item.append(el("strong", "", eventLabel(event)));
            item.append(el("small", "", eventDetail(event)));
            detailList.append(item);
          });
          row.append(detailList);
        }

        const replay = button(diagnostic ? "诊断事件不可回放" : "回放为 Debug Speak", "button", diagnostic);
        replay.dataset.eventIndex = String(primary.index);
        row.append(replay);
        events.append(row);
      });
      if (!events.children.length) events.append(el("div", "event-row", "暂无 Recent Events"));
    });
    state.flowFingerprints.eventList = eventListFp;
  }
}

export function renderConfig() {
  const configForm = $("config-form");
  const editingConfig = Boolean(
    configForm && document.activeElement && configForm.contains(document.activeElement)
  );
  if (!editingConfig) {
    if (state.settings) renderSettingsForm(state.settings);
    if (state.config) renderConfigForm(state.config);
  }
  const providers = state.health?.providers || {};
  const asr = state.config?.asr || {};
  const sherpa = asr.sherpa_onnx_asr || {};
  const bilibiliStatus = state.bilibili?.status || providers.bilibili || {};
  const configuredBilibiliRooms = state.bilibili?.configured_room_ids || state.config?.live?.bilibili_live?.room_ids || [];
  setPill($("llm-ready"), providers.llm?.api_key_configured === false ? "key missing" : "ready", providers.llm?.api_key_configured === false ? "warn" : "ok");
  setPill($("tts-ready"), providers.tts?.last_error ? "error" : providers.tts?.provider || "unknown", providers.tts?.last_error ? "bad" : "ok");
  setPill($("asr-ready"), asr.provider || "none", asr.provider === "sherpa_onnx_asr" ? (sherpa.ready ? "ok" : "warn") : "info");
  setPill($("bilibili-ready"), bilibiliStatus.state || "idle", toneForState(bilibiliStatus.state));
  setPill($("overlay-ready"), state.clients?.connected_clients ? "client online" : "client offline", state.clients?.connected_clients ? "ok" : "warn");
  setPill($("capture-ready"), state.capture?.capture?.status || "unknown", toneForState(state.capture?.capture?.status));
  setPill($("proactive-ready"), state.proactive?.proactive?.last_decision || "unknown", toneForState(state.proactive?.proactive?.last_decision));
  setPill($("mic-ready"), state.mic?.status || "unknown", toneForState(state.mic?.status));
  const providerErrors = [
    ...(state.errors?.provider_errors || []),
    ...(state.errors?.errors || []),
  ];
  const diagnosticEvents = (state.events || []).filter(eventIsDiagnostic);
  kvList($("bilibili-detail"), [
    ["已配置房间", configuredBilibiliRooms],
    ["当前房间", bilibiliStatus.active_room_id || bilibiliStatus.last_active_room_id || "none"],
    ["依赖", bilibiliStatus.library?.available ? "bili-listener ready" : bilibiliStatus.library?.import_error || "unavailable"],
    ["连接详情", bilibiliStatus.state_detail || ""],
    ["真实弹幕", bilibiliStatus.received_real_events ?? 0],
    ["测试弹幕", bilibiliStatus.received_test_events ?? 0],
    ["最近包", bilibiliStatus.last_packet_type || "none"],
    ["投递", bilibiliStatus.last_delivery?.reason || (bilibiliStatus.last_delivery?.ok ? "ok" : "none")],
    ["冷却", `${bilibiliStatus.danmaku_reply_cooldown_remaining_ms ?? 0} ms`],
  ]);
  setPill($("logs-ready"), providerErrors.length ? `${providerErrors.length} issue(s)` : "guarded", providerErrors.length ? "warn" : "ok");
  kvList($("config-diagnostics-detail"), [
    ["provider errors", providerErrors.length],
    ["log files", state.logs?.files?.length || 0],
    ["diagnostic events", diagnosticEvents.length],
    ["ASR provider", asr.provider || "none"],
    ["Sherpa ONNX", sherpa.reason || "disabled"],
    ["Sherpa streaming", sherpa.streaming_status || "unknown"],
    ["Sherpa missing files", Array.isArray(sherpa.missing_files) ? sherpa.missing_files.length : 0],
    ["replay guard", "diagnostic events disabled"],
  ]);
}

export function renderLogs() {
  if (state.view !== "logs") return;
  const errors = $("error-list");
  clear(errors);
  const errorItems = [
    ...(state.errors?.provider_errors || []),
    ...(state.errors?.errors || []),
  ];
  errorItems.slice(0, 24).forEach((item) => {
    const row = el("div", "timeline-row");
    row.append(el("strong", "", item.source || item.file || "error"));
    row.append(el("small", "", item.message || item.line || prettyJson(item)));
    errors.append(row);
  });
  if (!errors.children.length) errors.append(el("div", "timeline-row", "暂无 provider errors"));

  const logs = $("log-list");
  clear(logs);
  (state.logs?.files || []).forEach((file) => {
    const row = el("article", "log-file");
    row.append(el("strong", "", file.name || "log"));
    row.append(el("small", "", `${file.path || ""} ${file.updated_at_ms ? age(file.updated_at_ms) : ""}`));
    row.append(el("pre", "log-lines", (file.lines || []).join("\n")));
    logs.append(row);
  });
  if (!logs.children.length) logs.append(el("div", "timeline-row", "暂无日志文件"));
}

export function setView(view) {
  const nextView = viewMeta[view] ? view : "overview";
  state.view = nextView;
  if (location.hash !== `#${nextView}`) history.replaceState(null, "", `#${nextView}`);
  renderChrome();
}

function status(stateName) {
  return el("span", `status-pill ${stateName || ""}`, stateName || "unknown");
}

function actionLink(label, href) {
  const link = el("a", "button ghost", label);
  link.href = href;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  return link;
}
