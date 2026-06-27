"""Flask server for work-logs. Serves index.html + JSON API.

Sessions are in-memory; one process = one user. Run: python server.py
"""

import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import core

app = Flask(__name__, static_folder="static", static_url_path="")

CFG = core.load_config()
CLIENT, MODEL = core.create_client()

# session_id -> { messages, framing, target, mode, kind }
SESSIONS: dict[str, dict] = {}

QUESTIONS_COMPLETE = "[QUESTIONS_COMPLETE]"


def _new_session(kind, framing, target, extra=None):
    sid = secrets.token_urlsafe(12)
    SESSIONS[sid] = {
        "kind": kind,
        "framing": framing,
        "target": target,
        "messages": [],
        **(extra or {}),
    }
    return sid


def _system_for(sess):
    framing = sess["framing"]
    if sess["kind"] == "log":
        return core.build_system_prompt(CFG, framing)
    if sess["kind"] == "catchup":
        return CFG["framings"][framing]["catchup_system"]
    raise ValueError(f"unknown kind: {sess['kind']}")


# ---------- static ---------------------------------------------------------

@app.get("/")
def root():
    return send_from_directory("static", "index.html")


# ---------- meta -----------------------------------------------------------

@app.get("/api/config")
def api_config():
    return jsonify({
        "framings": list(CFG["framings"].keys()),
        "defaults": CFG.get("defaults", {}),
        "rollup_cadences": ["weekly", "biweekly", "monthly", "final-report"],
        "today": date.today().isoformat(),
    })


@app.get("/api/today")
def api_today():
    """Return today's daily entry (if any) so the UI knows whether to amend."""
    existing = core.read_existing_entry(CFG, "daily")
    return jsonify({
        "date": date.today().isoformat(),
        "exists": existing is not None,
        "content": existing or "",
    })


# ---------- log flow -------------------------------------------------------

@app.post("/api/log/start")
def api_log_start():
    """Start a daily log session. Body: { brain_dump, framing?, terse? }."""
    data = request.get_json(force=True)
    brain_dump = (data.get("brain_dump") or "").strip()
    if not brain_dump:
        return jsonify({"error": "brain_dump required"}), 400

    framing = data.get("framing") or CFG["defaults"]["framing"]
    target = "daily"
    existing = core.read_existing_entry(CFG, target)
    mode = "amend" if existing else "fresh"

    sid = _new_session("log", framing, target, {
        "existing": existing,
    })
    sess = SESSIONS[sid]
    sess["messages"].append({
        "role": "user",
        "content": f"Here's my brain dump:\n\n{brain_dump}",
    })

    # Terse escape hatch: skip QA entirely.
    if data.get("terse"):
        return _finalize_log(sid)

    assistant_text = core.ask_next_question(
        CLIENT, MODEL, _system_for(sess), sess["messages"],
    )
    if QUESTIONS_COMPLETE in assistant_text:
        return _finalize_log(sid)

    sess["messages"].append({"role": "assistant", "content": assistant_text})
    return jsonify({
        "session_id": sid,
        "done": False,
        "question": assistant_text,
        "mode": mode,
    })


@app.post("/api/log/answer")
def api_log_answer():
    """Body: { session_id, answer }."""
    data = request.get_json(force=True)
    sid = data.get("session_id")
    sess = SESSIONS.get(sid)
    if not sess:
        return jsonify({"error": "unknown session"}), 404

    answer = (data.get("answer") or "").strip()
    if not answer:
        return jsonify({"error": "answer required"}), 400

    sess["messages"].append({"role": "user", "content": answer})
    assistant_text = core.ask_next_question(
        CLIENT, MODEL, _system_for(sess), sess["messages"],
    )
    if QUESTIONS_COMPLETE in assistant_text:
        return _finalize_log(sid)

    sess["messages"].append({"role": "assistant", "content": assistant_text})
    return jsonify({"session_id": sid, "done": False, "question": assistant_text})


@app.post("/api/log/done")
def api_log_done():
    """User-triggered early finish. Body: { session_id }."""
    sid = request.get_json(force=True).get("session_id")
    if sid not in SESSIONS:
        return jsonify({"error": "unknown session"}), 404
    return _finalize_log(sid)


def _finalize_log(sid):
    sess = SESSIONS[sid]
    framing = sess["framing"]
    target = sess["target"]
    existing = sess.get("existing")

    if existing:
        gen_prompt = core.build_amend_prompt(CFG, framing, target, existing)
    else:
        gen_prompt = core.build_generation_prompt(CFG, framing, target)

    generated = core.generate_entry(CLIENT, MODEL, sess["messages"], gen_prompt)
    entry, insight = core.split_entry_and_insight(generated)

    topic = ""
    template = CFG["targets"][target].get("path", "")
    if "{topic}" in template:
        try:
            topic = core.pick_topic(CLIENT, MODEL, entry)
        except Exception:
            topic = ""

    return jsonify({
        "session_id": sid,
        "done": True,
        "preview": entry,
        "insight": insight,
        "topic": topic,
    })


@app.post("/api/log/save")
def api_log_save():
    """Body: { session_id, edited_preview?, save_insight }."""
    data = request.get_json(force=True)
    sid = data.get("session_id")
    sess = SESSIONS.get(sid)
    if not sess:
        return jsonify({"error": "unknown session"}), 404

    entry = (data.get("edited_preview") or "").strip()
    if not entry:
        return jsonify({"error": "edited_preview required"}), 400

    topic = (data.get("topic") or "").strip()
    path = core.write_target(CFG, sess["target"], entry, topic=topic or None)
    core.save_raw_input(CFG, sess["messages"], kind="log")

    insight_path = None
    if data.get("save_insight") and data.get("insight"):
        ip = core.append_insight(CFG, data["insight"])
        insight_path = str(ip.relative_to(core.SCRIPT_DIR))

    del SESSIONS[sid]
    return jsonify({
        "saved": str(path.relative_to(core.SCRIPT_DIR)),
        "insight_saved": insight_path,
    })


@app.post("/api/log/cancel")
def api_log_cancel():
    sid = request.get_json(force=True).get("session_id")
    SESSIONS.pop(sid, None)
    return jsonify({"ok": True})


# ---------- rollup ---------------------------------------------------------

@app.post("/api/rollup")
def api_rollup():
    """Body: { cadence: weekly|biweekly|monthly|final-report,
               start?: YYYY-MM-DD, end?: YYYY-MM-DD,
               framing?: ... }
    If start/end provided, it's a custom-range rollup.
    """
    data = request.get_json(force=True)
    cadence = data.get("cadence")
    framing = data.get("framing") or CFG["defaults"]["framing"]

    target_key = core.cadence_to_target_key(cadence)
    if not target_key:
        return jsonify({"error": f"unknown cadence: {cadence}"}), 400

    if data.get("start") and data.get("end"):
        try:
            start = datetime.strptime(data["start"], "%Y-%m-%d").date()
            end = datetime.strptime(data["end"], "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "bad date format"}), 400
        entries = core.collect_dailies_in_range(CFG, start, end)
        period_label = f"{start.isoformat()} to {end.isoformat()}"
    elif cadence == "final-report":
        # All daily entries.
        entries = core.collect_dailies_in_range(CFG, date(1970, 1, 1), date.today())
        period_label = "the entire internship"
    else:
        window = CFG["targets"][target_key].get("rollup_window_days", 14)
        entries = core.collect_recent_dailies(CFG, window)
        period_label = f"the last {window} days"

    if not entries:
        return jsonify({"error": f"No daily entries found for {period_label}"}), 400

    concat = "\n\n".join(
        f"=== {d.strftime('%Y-%m-%d')} ===\n\n{text}" for d, text in entries
    )
    system, generation = core.build_rollup_prompts(
        CFG, framing, cadence, target_key, period_label
    )

    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": f"Daily entries:\n\n{concat}\n\n{generation}"}],
    )
    return jsonify({
        "preview": response.content[0].text,
        "target_key": target_key,
        "entry_count": len(entries),
        "period": period_label,
        "source_dates": [d.isoformat() for d, _ in entries],
    })


@app.post("/api/rollup/save")
def api_rollup_save():
    """Body: { target_key, edited_preview, source_dates? }."""
    data = request.get_json(force=True)
    target_key = data.get("target_key")
    content = (data.get("edited_preview") or "").strip()
    if not target_key or not content:
        return jsonify({"error": "target_key and edited_preview required"}), 400
    path = core.write_target(CFG, target_key, content)

    dailies = []
    for s in data.get("source_dates") or []:
        try:
            dailies.append((datetime.strptime(s, "%Y-%m-%d").date(), ""))
        except ValueError:
            continue
    if dailies:
        core.link_rollup_to_dailies(CFG, target_key, dailies)

    return jsonify({"saved": str(path.relative_to(core.SCRIPT_DIR))})


# ---------- catchup --------------------------------------------------------

@app.post("/api/catchup/start")
def api_catchup_start():
    """Body: { brain_dump, target_key (weekly|monthly), framing? }."""
    data = request.get_json(force=True)
    brain_dump = (data.get("brain_dump") or "").strip()
    target_key = data.get("target_key", "monthly")
    framing = data.get("framing") or CFG["defaults"]["framing"]

    if not brain_dump:
        return jsonify({"error": "brain_dump required"}), 400
    if target_key not in CFG["targets"]:
        return jsonify({"error": f"unknown target: {target_key}"}), 400

    sid = _new_session("catchup", framing, target_key)
    sess = SESSIONS[sid]
    sess["messages"].append({
        "role": "user",
        "content": f"I haven't logged the last while. Here's my recap brain dump:\n\n{brain_dump}",
    })

    assistant_text = core.ask_next_question(
        CLIENT, MODEL, _system_for(sess), sess["messages"],
    )
    if QUESTIONS_COMPLETE in assistant_text:
        return _finalize_catchup(sid)

    sess["messages"].append({"role": "assistant", "content": assistant_text})
    return jsonify({"session_id": sid, "done": False, "question": assistant_text})


@app.post("/api/catchup/answer")
def api_catchup_answer():
    data = request.get_json(force=True)
    sid = data.get("session_id")
    sess = SESSIONS.get(sid)
    if not sess:
        return jsonify({"error": "unknown session"}), 404
    answer = (data.get("answer") or "").strip()
    if not answer:
        return jsonify({"error": "answer required"}), 400

    sess["messages"].append({"role": "user", "content": answer})
    assistant_text = core.ask_next_question(
        CLIENT, MODEL, _system_for(sess), sess["messages"],
    )
    if QUESTIONS_COMPLETE in assistant_text:
        return _finalize_catchup(sid)

    sess["messages"].append({"role": "assistant", "content": assistant_text})
    return jsonify({"session_id": sid, "done": False, "question": assistant_text})


@app.post("/api/catchup/done")
def api_catchup_done():
    sid = request.get_json(force=True).get("session_id")
    if sid not in SESSIONS:
        return jsonify({"error": "unknown session"}), 404
    return _finalize_catchup(sid)


def _finalize_catchup(sid):
    sess = SESSIONS[sid]
    system, generation = core.build_catchup_prompts(CFG, sess["framing"], sess["target"])
    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system,
        messages=sess["messages"] + [{"role": "user", "content": generation}],
    )
    summary, highlights = core.split_catchup(response.content[0].text)
    return jsonify({
        "session_id": sid,
        "done": True,
        "summary_preview": summary,
        "target_key": sess["target"],
        "highlights": [
            {"date": d.isoformat(), "body": body} for d, body in highlights
        ],
    })


@app.post("/api/catchup/save")
def api_catchup_save():
    """Body: { session_id, edited_summary, highlights: [{date, body, keep}] }."""
    data = request.get_json(force=True)
    sid = data.get("session_id")
    sess = SESSIONS.get(sid)
    if not sess:
        return jsonify({"error": "unknown session"}), 404

    summary = (data.get("edited_summary") or "").strip()
    if not summary:
        return jsonify({"error": "edited_summary required"}), 400

    summary_path = core.write_target(CFG, sess["target"], summary)
    core.save_raw_input(CFG, sess["messages"], kind="catchup")

    highlight_paths = []
    for h in data.get("highlights", []):
        if not h.get("keep"):
            continue
        try:
            when = datetime.strptime(h["date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        body = (h.get("body") or "").strip()
        if not body:
            continue
        topic = (h.get("topic") or "").strip()
        if not topic and "{topic}" in CFG["targets"]["daily"].get("path", ""):
            try:
                topic = core.pick_topic(CLIENT, MODEL, body)
            except Exception:
                topic = ""
        p = core.write_target(
            CFG, "daily", body, when=when, force_mode="amend",
            topic=topic or None,
        )
        highlight_paths.append(str(p.relative_to(core.SCRIPT_DIR)))

    del SESSIONS[sid]
    return jsonify({
        "summary_saved": str(summary_path.relative_to(core.SCRIPT_DIR)),
        "highlights_saved": highlight_paths,
    })


# ---------- main -----------------------------------------------------------

if __name__ == "__main__":
    Path(__file__).resolve().parent.joinpath("static").mkdir(exist_ok=True)
    app.run(host="127.0.0.1", port=5000, debug=False)
