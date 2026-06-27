"use strict";

const $ = (id) => document.getElementById(id);

let state = {
  cfg: null,
  log: { sessionId: null, insight: null },
  catchup: { sessionId: null, target: null, highlights: [] },
  rollup: { targetKey: null, sourceDates: [] },
};

// ---------- helpers ----------

async function api(path, body) {
  const opts = { method: "GET", headers: { "Content-Type": "application/json" } };
  if (body !== undefined) {
    opts.method = "POST";
    opts.body = JSON.stringify(body);
  }
  const r = await fetch(path, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}

function toast(msg, kind = "ok") {
  const el = $("toast");
  el.textContent = msg;
  el.className = "toast" + (kind === "error" ? " error" : "");
  setTimeout(() => el.classList.add("hidden"), 4000);
}

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }

function bubble(thread, who, text) {
  const b = document.createElement("div");
  b.className = `bubble ${who}`;
  b.innerHTML = `<span class="who">${who === "user" ? "you" : "claude"}</span>`;
  const body = document.createElement("div");
  body.textContent = text;
  b.appendChild(body);
  thread.appendChild(b);
  thread.scrollTop = thread.scrollHeight;
}

function status(el, msg, kind = "") {
  el.textContent = msg;
  el.className = "status" + (kind ? " " + kind : "");
}

function setBusy(button, busy, busyText = "Working...") {
  if (busy) {
    button.dataset.label = button.textContent;
    button.textContent = busyText;
    button.disabled = true;
  } else {
    if (button.dataset.label) button.textContent = button.dataset.label;
    button.disabled = false;
  }
}

// ---------- mode switching ----------

function setMode(mode) {
  document.querySelectorAll("#mode-nav button").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === mode);
  });
  ["log", "rollup", "catchup"].forEach((m) => {
    const el = $(`mode-${m}`);
    if (m === mode) show(el);
    else hide(el);
  });
}

document.querySelectorAll("#mode-nav button").forEach((b) => {
  b.addEventListener("click", () => setMode(b.dataset.mode));
});

// ---------- init ----------

async function init() {
  state.cfg = await api("/api/config");
  // Default custom-range start/end = last 7 days
  const today = new Date(state.cfg.today);
  const past = new Date(today);
  past.setDate(past.getDate() - 7);
  $("rollup-end").value = state.cfg.today;
  $("rollup-start").value = past.toISOString().slice(0, 10);
  await refreshToday();
}

async function refreshToday() {
  try {
    const t = await api("/api/today");
    const el = $("today-status");
    if (t.exists) {
      status(el, `An entry for today (${t.date}) already exists — saving will AMEND it.`, "ok");
    } else {
      status(el, `No entry yet for ${t.date}.`);
    }
  } catch (e) { status($("today-status"), e.message, "error"); }
}

// ---------- LOG flow ----------

async function logStart(terse = false) {
  const dump = $("log-dump").value.trim();
  if (!dump) { toast("Brain dump is empty", "error"); return; }
  const btn = terse ? $("log-terse-btn") : $("log-start-btn");
  setBusy(btn, true);
  try {
    const r = await api("/api/log/start", { brain_dump: dump, terse });
    state.log.sessionId = r.session_id;
    hide($("log-start"));
    show($("log-chat"));
    const thread = $("log-thread");
    bubble(thread, "user", dump);
    if (r.done) { showLogPreview(r.preview, r.insight, r.topic); }
    else { bubble(thread, "assistant", r.question); show($("log-answer-row")); $("log-answer").focus(); }
  } catch (e) { toast(e.message, "error"); }
  finally { setBusy(btn, false); }
}

async function logAnswer() {
  const ans = $("log-answer").value.trim();
  if (!ans) { toast("Empty answer", "error"); return; }
  const btn = $("log-answer-btn");
  setBusy(btn, true);
  try {
    bubble($("log-thread"), "user", ans);
    $("log-answer").value = "";
    const r = await api("/api/log/answer", { session_id: state.log.sessionId, answer: ans });
    if (r.done) { hide($("log-answer-row")); showLogPreview(r.preview, r.insight, r.topic); }
    else { bubble($("log-thread"), "assistant", r.question); $("log-answer").focus(); }
  } catch (e) { toast(e.message, "error"); }
  finally { setBusy(btn, false); }
}

async function logDone() {
  const btn = $("log-done-btn");
  setBusy(btn, true, "Generating...");
  try {
    const r = await api("/api/log/done", { session_id: state.log.sessionId });
    hide($("log-answer-row"));
    showLogPreview(r.preview, r.insight, r.topic);
  } catch (e) { toast(e.message, "error"); }
  finally { setBusy(btn, false); }
}

function showLogPreview(entry, insight, topic) {
  $("log-preview-ta").value = entry;
  $("log-topic").value = topic || "";
  state.log.insight = insight;
  if (insight) {
    show($("log-insight-block"));
    $("log-insight-ta").value = insight;
  } else { hide($("log-insight-block")); }
  show($("log-preview"));
}

async function logSave() {
  const btn = $("log-save-btn");
  setBusy(btn, true, "Saving...");
  try {
    const body = {
      session_id: state.log.sessionId,
      edited_preview: $("log-preview-ta").value,
      save_insight: $("log-save-insight").checked,
      insight: $("log-insight-ta").value,
      topic: $("log-topic").value,
    };
    const r = await api("/api/log/save", body);
    toast(`Saved: ${r.saved}` + (r.insight_saved ? ` + ${r.insight_saved}` : ""));
    resetLog();
    await refreshToday();
  } catch (e) { toast(e.message, "error"); }
  finally { setBusy(btn, false); }
}

async function logCancel() {
  if (state.log.sessionId) {
    try { await api("/api/log/cancel", { session_id: state.log.sessionId }); }
    catch (e) { /* ignore */ }
  }
  resetLog();
}

function resetLog() {
  state.log = { sessionId: null, insight: null };
  $("log-dump").value = "";
  $("log-answer").value = "";
  $("log-thread").innerHTML = "";
  hide($("log-chat"));
  hide($("log-answer-row"));
  hide($("log-preview"));
  show($("log-start"));
}

$("log-start-btn").onclick = () => logStart(false);
$("log-terse-btn").onclick = () => logStart(true);
$("log-answer-btn").onclick = logAnswer;
$("log-done-btn").onclick = logDone;
$("log-save-btn").onclick = logSave;
$("log-cancel-btn").onclick = logCancel;
$("log-answer").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); logAnswer(); }
});

// ---------- ROLLUP flow ----------

$("rollup-custom").addEventListener("change", (e) => {
  $("rollup-range").classList.toggle("hidden", !e.target.checked);
});

$("rollup-run-btn").onclick = async () => {
  const btn = $("rollup-run-btn");
  setBusy(btn, true, "Generating...");
  status($("rollup-status"), "");
  try {
    const body = { cadence: $("rollup-cadence").value };
    if ($("rollup-custom").checked) {
      body.start = $("rollup-start").value;
      body.end = $("rollup-end").value;
    }
    const r = await api("/api/rollup", body);
    state.rollup.targetKey = r.target_key;
    state.rollup.sourceDates = r.source_dates || [];
    $("rollup-preview-ta").value = r.preview;
    status($("rollup-status"), `Synthesized ${r.entry_count} daily entries from ${r.period}.`, "ok");
    show($("rollup-preview"));
  } catch (e) { status($("rollup-status"), e.message, "error"); }
  finally { setBusy(btn, false); }
};

$("rollup-save-btn").onclick = async () => {
  const btn = $("rollup-save-btn");
  setBusy(btn, true, "Saving...");
  try {
    const r = await api("/api/rollup/save", {
      target_key: state.rollup.targetKey,
      edited_preview: $("rollup-preview-ta").value,
      source_dates: state.rollup.sourceDates,
    });
    toast(`Saved: ${r.saved}`);
    hide($("rollup-preview"));
    $("rollup-preview-ta").value = "";
  } catch (e) { toast(e.message, "error"); }
  finally { setBusy(btn, false); }
};

$("rollup-discard-btn").onclick = () => {
  hide($("rollup-preview"));
  $("rollup-preview-ta").value = "";
};

// ---------- CATCHUP flow ----------

$("catchup-start-btn").onclick = async () => {
  const dump = $("catchup-dump").value.trim();
  if (!dump) { toast("Brain dump is empty", "error"); return; }
  const btn = $("catchup-start-btn");
  setBusy(btn, true);
  try {
    const r = await api("/api/catchup/start", {
      brain_dump: dump,
      target_key: $("catchup-target").value,
    });
    state.catchup.sessionId = r.session_id;
    state.catchup.target = $("catchup-target").value;
    hide($("catchup-start"));
    show($("catchup-chat"));
    bubble($("catchup-thread"), "user", dump);
    if (r.done) { showCatchupPreview(r); }
    else { bubble($("catchup-thread"), "assistant", r.question); show($("catchup-answer-row")); $("catchup-answer").focus(); }
  } catch (e) { toast(e.message, "error"); }
  finally { setBusy(btn, false); }
};

$("catchup-answer-btn").onclick = async () => {
  const ans = $("catchup-answer").value.trim();
  if (!ans) return;
  const btn = $("catchup-answer-btn");
  setBusy(btn, true);
  try {
    bubble($("catchup-thread"), "user", ans);
    $("catchup-answer").value = "";
    const r = await api("/api/catchup/answer", { session_id: state.catchup.sessionId, answer: ans });
    if (r.done) { hide($("catchup-answer-row")); showCatchupPreview(r); }
    else { bubble($("catchup-thread"), "assistant", r.question); $("catchup-answer").focus(); }
  } catch (e) { toast(e.message, "error"); }
  finally { setBusy(btn, false); }
};

$("catchup-done-btn").onclick = async () => {
  const btn = $("catchup-done-btn");
  setBusy(btn, true, "Generating...");
  try {
    const r = await api("/api/catchup/done", { session_id: state.catchup.sessionId });
    hide($("catchup-answer-row"));
    showCatchupPreview(r);
  } catch (e) { toast(e.message, "error"); }
  finally { setBusy(btn, false); }
};

function showCatchupPreview(r) {
  $("catchup-summary-ta").value = r.summary_preview;
  state.catchup.highlights = r.highlights || [];

  const wrap = $("catchup-highlights");
  wrap.innerHTML = "";
  if (state.catchup.highlights.length) {
    const label = document.createElement("label");
    label.textContent = "Highlights";
    label.innerHTML += ` <span class="hint">— uncheck any you don't want saved as a daily entry.</span>`;
    wrap.appendChild(label);
  }

  state.catchup.highlights.forEach((h, i) => {
    const card = document.createElement("div");
    card.className = "highlight-card";

    const top = document.createElement("div");
    top.className = "row";
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.checked = true; cb.id = `hl-keep-${i}`;
    const cbl = document.createElement("label");
    cbl.className = "check";
    cbl.htmlFor = cb.id;
    cbl.append(cb, document.createTextNode(" keep"));
    const di = document.createElement("input");
    di.type = "date"; di.value = h.date; di.id = `hl-date-${i}`;
    top.append(cbl, di);
    card.append(top);

    const body = document.createElement("textarea");
    body.rows = 8;
    body.value = h.body;
    body.id = `hl-body-${i}`;
    card.append(body);

    wrap.append(card);
  });

  show($("catchup-preview"));
}

$("catchup-save-btn").onclick = async () => {
  const btn = $("catchup-save-btn");
  setBusy(btn, true, "Saving...");
  try {
    const highlights = state.catchup.highlights.map((_, i) => ({
      date: $(`hl-date-${i}`).value,
      body: $(`hl-body-${i}`).value,
      keep: $(`hl-keep-${i}`).checked,
    }));
    const r = await api("/api/catchup/save", {
      session_id: state.catchup.sessionId,
      edited_summary: $("catchup-summary-ta").value,
      highlights,
    });
    toast(`Saved: ${r.summary_saved} + ${r.highlights_saved.length} highlight(s)`);
    resetCatchup();
  } catch (e) { toast(e.message, "error"); }
  finally { setBusy(btn, false); }
};

$("catchup-discard-btn").onclick = resetCatchup;

function resetCatchup() {
  state.catchup = { sessionId: null, target: null, highlights: [] };
  $("catchup-dump").value = "";
  $("catchup-answer").value = "";
  $("catchup-thread").innerHTML = "";
  $("catchup-highlights").innerHTML = "";
  hide($("catchup-chat"));
  hide($("catchup-answer-row"));
  hide($("catchup-preview"));
  show($("catchup-start"));
}

init().catch((e) => toast(e.message, "error"));
