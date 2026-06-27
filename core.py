"""Core logic for work-logs: config, Claude client, prompts, file I/O.

Shared by server.py. No UI here.
"""

import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml
from anthropic import AnthropicBedrock

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"
ENV_PATH = SCRIPT_DIR / ".env"

INSIGHT_MARKER = "===INSIGHT==="
HIGHLIGHTS_MARKER = "===HIGHLIGHTS==="
HIGHLIGHT_DATE_RE = re.compile(r"^===DATE:\s*(\d{4}-\d{2}-\d{2})\s*===\s*$", re.M)
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# Matches DD-MM-YY at the start of a filename (the new daily naming).
DD_MM_YY_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{2})\b")

# Default if config.yaml doesn't override.
DEFAULT_INTERNSHIP_START = date(2026, 5, 18)

# Characters illegal in filenames across major filesystems / Obsidian.
_TOPIC_BAD = re.compile(r'[\\/:*?"<>|\[\]#^]')


def slugify_topic(topic, max_words=7, max_chars=64):
    """Normalise an LLM-suggested topic into a filename-safe fragment.

    Returns "" if the input is empty so callers can fall back to a date-only
    filename.
    """
    if not topic:
        return ""
    t = _TOPIC_BAD.sub(" ", topic).strip().strip(".")
    t = re.sub(r"\s+", " ", t)
    words = t.split(" ")[:max_words]
    return " ".join(words)[:max_chars].rstrip(" .")


# ---------- week math -----------------------------------------------------

def internship_start(cfg=None):
    """Return the configured internship-start date, or the default."""
    if cfg:
        s = cfg.get("internship_start")
        if isinstance(s, date):
            return s
        if isinstance(s, str):
            try:
                return datetime.strptime(s, "%Y-%m-%d").date()
            except ValueError:
                pass
    return DEFAULT_INTERNSHIP_START


def _week_anchor_monday(start):
    """Monday of the calendar week that contains the internship-start date.

    Week 1 begins on this Monday. Internship-start days mid-week (e.g. a
    Wednesday) still produce Week 1 = the Mon-Sun containing that day.
    """
    return start - timedelta(days=start.weekday())


def week_number(when, cfg=None):
    """Internship week number for `when` against the May-18 (or configured)
    anchor. Week 1 is Mon-Sun containing the anchor; weeks are calendar weeks
    (Mon-Sun).

    Returns an integer >= 1 for dates on or after the anchor's Monday;
    returns 0 for dates before that (shouldn't normally happen, but safe).
    """
    start = internship_start(cfg)
    anchor_mon = _week_anchor_monday(start)
    target_mon = when - timedelta(days=when.weekday())
    delta_days = (target_mon - anchor_mon).days
    if delta_days < 0:
        return 0
    return (delta_days // 7) + 1


def cycle_day(when, cfg=None):
    """Return (cycle_index, day_in_cycle) for `when`.

    A cycle is two consecutive internship weeks: weeks 1+2 form cycle 1,
    weeks 3+4 form cycle 2, etc. `day_in_cycle` is 1..14 (1 = Monday of the
    first week, 14 = Sunday of the second).
    """
    start = internship_start(cfg)
    anchor_mon = _week_anchor_monday(start)
    delta_days = (when - anchor_mon).days
    if delta_days < 0:
        return (0, 0)
    cycle_idx = (delta_days // 14) + 1
    day = (delta_days % 14) + 1
    return (cycle_idx, day)


def cycle_weeks(cycle_idx):
    """Return (week_a, week_b) integers for the cycle. Cycle 1 -> (1, 2)."""
    return (cycle_idx * 2 - 1, cycle_idx * 2)


def _path_format_args(when, cfg=None, topic=None):
    """Common kwargs available to path templates:
      {date}        — datetime.date with strftime
      {month}       — full month name (e.g. "June")
      {week}        — internship week number (int)
      {week_pair}   — "1-2", "3-4" etc. for the cycle containing this date
      {cycle_month} — month name of cycle-day 14 (used to place biweeklies)
      {topic}       — sanitised LLM topic (only daily uses it today)
    """
    cyc, _ = cycle_day(when, cfg)
    week_a, week_b = cycle_weeks(cyc)
    start = internship_start(cfg)
    anchor_mon = _week_anchor_monday(start)
    cycle_last_day = anchor_mon + timedelta(days=cyc * 14 - 1)
    return {
        "date": when,
        "month": when.strftime("%B"),
        "week": week_number(when, cfg),
        "week_pair": f"{week_a}-{week_b}",
        "week_pair_full": f"W{week_a}-W{week_b}",
        "cycle_month": cycle_last_day.strftime("%B"),
        "topic": topic or "",
    }


def date_from_ddmmyy(stem):
    """If `stem` starts with DD-MM-YY, return a date; else None."""
    m = DD_MM_YY_RE.match(stem)
    if not m:
        return None
    dd, mm, yy = m.groups()
    try:
        return datetime.strptime(f"{dd}-{mm}-{yy}", "%d-%m-%y").date()
    except ValueError:
        return None


# ---------- env + client ---------------------------------------------------

def load_env_file():
    if not ENV_PATH.exists():
        raise FileNotFoundError(f".env file not found: {ENV_PATH}")
    env_vars = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip().strip("\"'")
    return env_vars


def load_settings():
    env = load_env_file()
    token = env.get("AWS_BEARER_TOKEN_BEDROCK")
    if not token:
        raise RuntimeError("AWS_BEARER_TOKEN_BEDROCK not found in .env")
    region = env.get("AWS_REGION", "us-east-1")
    model = env.get(
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    )
    return token, region, model


def create_client():
    token, region, model = load_settings()
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = token
    return AnthropicBedrock(aws_region=region), model


# ---------- config ---------------------------------------------------------

def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found: {CONFIG_PATH}")
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    cfg["_vault"] = (SCRIPT_DIR / cfg.get("vault_path", "./logbook")).resolve()
    return cfg


def vault_path(cfg, *parts):
    return cfg["_vault"].joinpath(*parts)


# ---------- prompts --------------------------------------------------------

def render_section_blocks(sections):
    return "\n\n".join(f"### {s}\n- (bullet points)" for s in sections)


def build_system_prompt(cfg, framing):
    return cfg["framings"][framing]["system"]


def build_generation_prompt(cfg, framing, target):
    f = cfg["framings"][framing]
    t = cfg["targets"][target]
    return f["generation"].format(
        section_blocks=render_section_blocks(t["sections"]),
        footer=t.get("footer", ""),
    )


def build_amend_prompt(cfg, framing, target, existing_entry):
    f = cfg["framings"][framing]
    t = cfg["targets"][target]
    return f["amend"].format(
        existing_entry=existing_entry,
        section_blocks=render_section_blocks(t["sections"]),
        footer=t.get("footer", ""),
    )


def build_rollup_prompts(cfg, framing, cadence, target_key, period_label):
    f = cfg["framings"][framing]
    t = cfg["targets"][target_key]
    system = f["rollup_system"].format(cadence=cadence, period=period_label)
    generation = f["rollup_generation"].format(
        cadence=cadence,
        section_blocks=render_section_blocks(t.get("sections", [])),
        footer=t.get("footer", ""),
    )
    return system, generation


def build_catchup_prompts(cfg, framing, target_key):
    f = cfg["framings"][framing]
    t = cfg["targets"][target_key]
    system = f["catchup_system"]
    generation = f["catchup_generation"].format(
        target_name=target_key,
        section_blocks=render_section_blocks(t["sections"]),
        footer=t.get("footer", ""),
    )
    return system, generation


# ---------- Claude calls ---------------------------------------------------

def ask_next_question(client, model, system_prompt, messages):
    """Send conversation, get either a question or [QUESTIONS_COMPLETE]."""
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text


def classify_entities(client, model, cfg, user_answer, conversation_text):
    """Run the Graph Nodes classifier. Returns
    `{resolved: [entity_dict, ...], proposed: [entity_dict, ...]}`.

    `user_answer` is the operator's freeform answer to the final "what
    hardware/platforms/concepts did you focus on today?" question. May be
    empty/"none" — in that case the classifier infers from
    `conversation_text` instead.

    Resolved entities are existing registry entries (matched by canonical
    name or alias). Proposed entities are new candidates the LLM thinks
    should be added; they're surfaced to the user for approval before being
    written to the registry.
    """
    entities = load_entities(cfg)
    idx = build_entity_index(entities)

    # Compact registry view for the LLM context (don't dump descriptions).
    registry_lines = []
    for e in entities:
        aliases = ", ".join(e["aliases"]) if e["aliases"] else ""
        registry_lines.append(f"- {e['name']} ({e['kind']}){' [aliases: ' + aliases + ']' if aliases else ''}")
    registry_blob = "\n".join(registry_lines) if registry_lines else "(empty registry)"

    system = (
        "You classify graph-node entities for a daily engineering log. The vault "
        "has a canonical registry of names + aliases. Your job: from the user's "
        "answer (and the conversation context) extract the entities they focused "
        "on today, MATCH them against the registry first, and only PROPOSE new "
        "ones when nothing in the registry fits.\n\n"
        "Kinds:\n"
        "  hardware  — physical robots, dev boards, sensors → wikilinks\n"
        "  platform  — orchestration platforms, fleet managers → wikilinks\n"
        "  software  — languages, runtimes, libraries → tags\n"
        "  protocol  — wire/transport/RPC protocols → tags\n"
        "  concept   — algorithms, patterns, abstract ideas → tags\n\n"
        "Output STRICTLY this JSON shape and nothing else:\n"
        "{\n"
        '  "resolved": [{"name": "<canonical name from registry>"}, ...],\n'
        '  "proposed": [{"name": "<new canonical>", "kind": "<kind>",'
        ' "aliases": [...]}, ...]\n'
        "}\n"
        "Rules:\n"
        "- Only put a name in `resolved` if it appears in the registry exactly.\n"
        "- Use the registry's exact `name` field, NOT an alias.\n"
        "- If the user's answer is empty/'none'/'skip', infer from the "
        "  conversation. If still nothing concrete, return empty arrays.\n"
        "- Prefer fewer, higher-signal entities (8 is a lot; 3-5 is typical).\n"
        "- Never include generic words like 'work', 'progress', 'integration'.\n"
    )

    prompt = (
        f"REGISTRY:\n{registry_blob}\n\n"
        f"CONVERSATION (for context):\n{conversation_text[:6000]}\n\n"
        f"USER'S ANSWER:\n{user_answer or '(empty)'}\n\n"
        "Return the JSON now."
    )

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    # Strip code fences if the model wrapped the JSON.
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n", "", raw)
        raw = raw.rstrip("` \n")
    import json
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"resolved": [], "proposed": []}

    resolved = []
    seen_names = set()
    for r in parsed.get("resolved") or []:
        name = (r.get("name") or "").strip()
        if not name:
            continue
        hit = find_entity(name, entities, idx)
        if hit is None:
            continue
        if hit["name"] in seen_names:
            continue
        seen_names.add(hit["name"])
        resolved.append(hit)

    proposed = []
    for p in parsed.get("proposed") or []:
        name = (p.get("name") or "").strip()
        kind = (p.get("kind") or "").strip().lower()
        if not name or kind not in (WIKILINK_KINDS | TAG_KINDS):
            continue
        # Skip if it's already in the registry (LLM hallucinated a "new" one).
        if find_entity(name, entities, idx) is not None:
            continue
        aliases = [a for a in (p.get("aliases") or []) if isinstance(a, str)]
        proposed.append({
            "name": name,
            "kind": kind,
            "aliases": aliases,
        })

    return {"resolved": resolved, "proposed": proposed}


def pick_topic(client, model, entry_markdown):
    """Ask Claude for a 2-5 word topic for a finalised daily entry. Returns
    a filename-safe slug (empty string on failure / refusal).
    """
    prompt = (
        "Below is a finalised daily engineering log. Give me a 2 to 5 word "
        "topic that names what the engineer was working on. The topic will "
        "be used in a filename, so:\n"
        "- Use Title Case-ish or plain capitalisation, your call.\n"
        "- No quotes, no trailing punctuation.\n"
        "- No filesystem-illegal characters (/, :, *, ?, etc.).\n"
        "- Lead with the concrete thing (e.g. 'RTSP auth fix', "
        "'Go2 end-to-end demo', 'SE(2) dead-reckoning').\n"
        "- Avoid generic words like 'work' or 'progress'.\n\n"
        "Respond with ONLY the topic, nothing else.\n\n"
        f"ENTRY:\n\n{entry_markdown}"
    )
    response = client.messages.create(
        model=model,
        max_tokens=64,
        system="You produce concise filename-ready topic labels. Output only the label.",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    # The model might wrap in quotes despite instructions — strip them.
    raw = raw.strip("\"'`").strip()
    # Take only the first line in case it adds commentary.
    raw = raw.splitlines()[0] if raw else ""
    return slugify_topic(raw)


def generate_entry(client, model, messages, generation_prompt):
    """Final generation step — appends generation prompt and returns markdown."""
    msgs = messages + [{"role": "user", "content": generation_prompt}]
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system="You are a technical writing assistant that produces clean, well-structured Markdown.",
        messages=msgs,
    )
    return response.content[0].text


# ---------- entry parsing --------------------------------------------------

def split_entry_and_insight(generated):
    if INSIGHT_MARKER not in generated:
        return generated.strip(), None
    entry, _, insight = generated.partition(INSIGHT_MARKER)
    return entry.strip(), insight.strip()


def split_catchup(generated):
    """Split into (summary, [(date, highlight_body), ...])."""
    if HIGHLIGHTS_MARKER not in generated:
        return generated.strip(), []
    summary, _, highlights_blob = generated.partition(HIGHLIGHTS_MARKER)

    # Split highlights by ===DATE: YYYY-MM-DD=== markers
    parts = HIGHLIGHT_DATE_RE.split(highlights_blob)
    # parts = ['preamble', 'date1', 'body1', 'date2', 'body2', ...]
    highlights = []
    for i in range(1, len(parts), 2):
        d_str = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        try:
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        highlights.append((d, body))
    return summary.strip(), highlights


# ---------- writing --------------------------------------------------------

def _template_has_topic(template):
    return "{topic}" in template


def _render_template(template, when, cfg=None, topic=None):
    """Render a path template against the {date}/{month}/{week}/{topic} keys."""
    args = _path_format_args(when, cfg=cfg, topic=slugify_topic(topic) if topic else "")
    return template.format(**args).rstrip()


def resolve_target_path(cfg, target_key, when=None, topic=None):
    """Return the path where a target's content should live.

    If the path template uses `{topic}` and no topic is supplied, falls back
    to find_existing_target_path so amends/lookups still resolve. If nothing
    exists yet, returns the path with an empty-topic placeholder so the caller
    can probe `.exists()` cheaply.
    """
    when = when or date.today()
    template = cfg["targets"][target_key]["path"]

    if _template_has_topic(template):
        if topic:
            return vault_path(cfg, _render_template(template, when, cfg, topic))
        found = find_existing_target_path(cfg, target_key, when)
        if found is not None:
            return found
        # No existing entry, no topic — return a date-only placeholder so
        # `.exists()` returns False without raising on the format call.
        return vault_path(cfg, _render_template(template, when, cfg, topic=""))

    return vault_path(cfg, _render_template(template, when, cfg))


def find_existing_target_path(cfg, target_key, when=None):
    """Find an on-disk file for `when`'s daily/raw entry.

    Strategy:
      1. If the path template has no `{topic}`, just check the rendered path.
      2. Otherwise glob the parent folder and look for any `.md` whose
         frontmatter aliases include `when.isoformat()` or
         `when.strftime("%d-%m-%y")`. The dailies always carry both as
         aliases, so this is the canonical lookup-by-date.
      3. Falls back to the legacy date-prefix glob (DD-MM-YY then YYYY-MM-DD)
         for files migrated before alias frontmatter was added.
    """
    when = when or date.today()
    template = cfg["targets"][target_key]["path"]
    if not _template_has_topic(template):
        path = vault_path(cfg, _render_template(template, when, cfg))
        return path if path.exists() else None

    placeholder = vault_path(cfg, _render_template(template, when, cfg, topic=""))
    parent = placeholder.parent
    if not parent.exists():
        return None

    needles = (when.isoformat(), when.strftime("%d-%m-%y"))
    for p in sorted(parent.glob("*.md")):
        # Cheap frontmatter scan: read up to ~20 lines and look for our date.
        try:
            with open(p) as f:
                head = "".join(f.readline() for _ in range(30))
        except OSError:
            continue
        if not head.startswith("---"):
            continue
        for needle in needles:
            if f"- {needle}" in head:
                return p

    # Legacy fallback: filename prefix glob.
    prefixes = [
        when.strftime("%d-%m-%y"),
        when.strftime("%Y-%m-%d"),
    ]
    for prefix in prefixes:
        matches = sorted(parent.glob(f"{prefix}*.md"))
        if matches:
            return matches[0]
    return None


def read_existing_entry(cfg, target_key, when=None):
    path = resolve_target_path(cfg, target_key, when)
    return path.read_text() if path.exists() else None


def write_target(cfg, target_key, content, when=None, force_mode=None, topic=None):
    """Write `content` to the target. Returns the path written.

    For targets whose path template uses `{topic}`, an `aliases:` frontmatter
    block referencing the date is auto-prepended so that `[[YYYY-MM-DD]]`
    wikilinks in rollups still resolve after the filename gains a topic.
    """
    when = when or date.today()
    template = cfg["targets"][target_key]["path"]
    uses_topic = _template_has_topic(template)

    # If the path uses {topic} and we got a new topic, rename any existing
    # date-prefixed file in place so we don't end up with two notes per day.
    if uses_topic and topic:
        existing = find_existing_target_path(cfg, target_key, when)
        new_path = resolve_target_path(cfg, target_key, when, topic=topic)
        if existing is not None and existing != new_path:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            existing.rename(new_path)
        path = new_path
    else:
        path = resolve_target_path(cfg, target_key, when, topic=topic)

    path.parent.mkdir(parents=True, exist_ok=True)
    mode = force_mode or cfg["targets"][target_key].get("mode", "append")
    header = f"## {when.strftime('%B %d, %Y')}"

    frontmatter = ""
    if uses_topic:
        # Aliases let date-shaped wikilinks ([[YYYY-MM-DD]] or [[DD-MM-YY]])
        # still resolve to a topic-named file. Both forms are recorded.
        frontmatter = (
            "---\n"
            "aliases:\n"
            f"  - {when.isoformat()}\n"
            f"  - {when.strftime('%d-%m-%y')}\n"
            "---\n\n"
        )

    if mode == "amend":
        title = target_key.replace("_", " ").title()
        path.write_text(
            f"{frontmatter}# {title}\n\n{header}\n\n{content.strip()}\n\n---\n"
        )
    elif path.exists() and mode in ("write_or_append", "append"):
        with open(path, "a") as f:
            extra = ""
            if mode == "write_or_append":
                extra = f" (additional entry at {datetime.now().strftime('%H:%M')})"
            f.write(f"\n\n{header}{extra}\n\n{content.strip()}\n\n---\n")
    else:
        title = target_key.replace("_", " ").title()
        path.write_text(
            f"{frontmatter}# {title}\n\n{header}\n\n{content.strip()}\n\n---\n"
        )

    return path


def save_raw_input(cfg, messages, kind="log", when=None):
    """Append the raw brain dump + Q&A turns to logbook/raw/{date}.md.

    `messages` is the full session message list (user/assistant turns).
    `kind` distinguishes log vs catchup sessions in the file header.
    """
    if "raw" not in cfg.get("targets", {}):
        return None
    when = when or date.today()
    path = resolve_target_path(cfg, "raw", when)
    path.parent.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%H:%M")
    lines = [f"## {when.strftime('%B %d, %Y')} — {kind} session @ {stamp}\n"]
    for m in messages:
        role = m.get("role", "?")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        label = "Me" if role == "user" else "Assistant"
        lines.append(f"**{label}:**\n\n{content}\n")
    block = "\n".join(lines) + "\n---\n"

    if path.exists():
        with open(path, "a") as f:
            f.write("\n" + block)
    else:
        path.write_text(f"# Raw input — {when.isoformat()}\n\n{block}")
    return path


def append_insight(cfg, insight_block):
    path = resolve_target_path(cfg, "final_report")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            "# Final Report — Technical Insights\n\n"
            "> Running collection of academic-aligned technical insights.\n\n"
        )
    with open(path, "a") as f:
        f.write("\n" + insight_block.strip() + "\n\n")
    return path


# ---------- rollup ---------------------------------------------------------

_ALIAS_DATE_RE = re.compile(
    r"^\s*-\s*(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{2})\s*$",
    re.M,
)


def _date_from_frontmatter(text):
    """Extract a date from a file's YAML frontmatter `aliases:` list.

    Recognises both YYYY-MM-DD and DD-MM-YY forms. Returns the date or None.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    head = text[:end]
    for m in _ALIAS_DATE_RE.finditer(head):
        token = m.group(1)
        for fmt in ("%Y-%m-%d", "%d-%m-%y"):
            try:
                return datetime.strptime(token, fmt).date()
            except ValueError:
                continue
    return None


def collect_dailies_in_range(cfg, start_date, end_date):
    """Read all daily entries with dates in [start_date, end_date].

    Walks the whole vault recursively. Each `.md` is matched in this order:
      1. Frontmatter `aliases:` containing a YYYY-MM-DD or DD-MM-YY entry
         (the canonical lookup for the topic-only filename layout).
      2. Filename starts with DD-MM-YY (transitional layout).
      3. Filename contains YYYY-MM-DD anywhere (legacy `daily/2026-MM/` layout).

    Files inside rollup directories (`entities/`, anything starting with
    `Weekly_`, `Biweekly_`, `Monthly_`) and dotfiles are skipped.
    """
    vault = cfg["_vault"]
    if not vault.exists():
        return []

    rollup_prefixes = ("Weekly_", "Biweekly_", "Monthly_")
    entries = []
    seen_dates = set()

    for p in sorted(vault.rglob("*.md")):
        if any(part.startswith(".") for part in p.relative_to(vault).parts):
            continue
        if p.name.startswith(rollup_prefixes):
            continue
        if "entities" in p.relative_to(vault).parts[:1]:
            continue

        text = p.read_text()

        d = _date_from_frontmatter(text)
        if d is None:
            d = date_from_ddmmyy(p.stem)
        if d is None:
            m = DATE_RE.search(p.name)
            if m:
                try:
                    d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                except ValueError:
                    d = None
        if d is None:
            continue

        if not (start_date <= d <= end_date):
            continue
        if d in seen_dates:
            continue
        seen_dates.add(d)
        entries.append((d, text))

    entries.sort(key=lambda t: t[0])
    return entries


def collect_recent_dailies(cfg, window_days):
    end = date.today()
    start = end - timedelta(days=window_days)
    return collect_dailies_in_range(cfg, start, end)


def rollup_stem(target_key, when=None, cfg=None):
    """The wikilink stem for a rollup of the given target on `when`.

    Mirrors the `path` template's filename, sans extension, so Obsidian
    wikilinks resolve to the correct note. Uses the internship-week
    numbering off the May-18 anchor.
    """
    when = when or date.today()
    if target_key == "weekly":
        return f"Weekly_W{week_number(when, cfg)}"
    if target_key == "biweekly":
        cyc, _ = cycle_day(when, cfg)
        wa, wb = cycle_weeks(cyc)
        return f"Biweekly_W{wa}-W{wb}"
    if target_key == "monthly":
        return f"Monthly_{when.strftime('%B')}"
    if target_key == "final_report":
        return "final_report"
    return None


def link_rollup_to_dailies(cfg, target_key, dailies, when=None):
    """After a rollup is saved, write bidirectional wikilinks so the Obsidian
    graph view connects the rollup node to each daily node.

    `dailies` is a list of (date, _text) tuples as returned by
    collect_dailies_in_range — text is ignored, only the dates are used.
    """
    if not dailies:
        return
    stem = rollup_stem(target_key, when, cfg)
    if not stem:
        return

    rollup_path = resolve_target_path(cfg, target_key, when)
    if rollup_path.exists():
        # New layout uses DD-MM-YY filenames; the legacy YYYY-MM-DD alias is
        # carried in the daily's frontmatter for backwards compatibility.
        links = " ".join(f"[[{d.strftime('%d-%m-%y')}]]" for d, _ in dailies)
        block = f"\n## Source dailies\n\n{links}\n"
        existing = rollup_path.read_text()
        if "## Source dailies" not in existing:
            with open(rollup_path, "a") as f:
                f.write(block)

    rollup_link = f"[[{stem}]]"
    for d, _ in dailies:
        daily_path = resolve_target_path(cfg, "daily", d)
        if not daily_path.exists():
            continue
        existing = daily_path.read_text()
        if rollup_link in existing:
            continue
        with open(daily_path, "a") as f:
            f.write(f"\n## Rolled up into\n\n{rollup_link}\n")


# ---------- graph-nodes parsing -------------------------------------------

# Match the `**Graph Nodes:** [[X]] · #y` line we inject under date headings.
GRAPH_NODES_LINE_RE = re.compile(
    r"^\*\*Graph Nodes:\*\*\s*(.+)$", re.M,
)
WIKILINK_RE = re.compile(r"\[\[([^\]\|]+?)(?:\|[^\]]*)?\]\]")
TAG_RE = re.compile(r"(?<![A-Za-z0-9_])#([A-Za-z][A-Za-z0-9_]*)")


def parse_graph_nodes_line(text):
    """Find the Graph Nodes line in `text` and return its raw payload string,
    or None if no such line. Returns the substring after `**Graph Nodes:**`.
    """
    m = GRAPH_NODES_LINE_RE.search(text)
    if not m:
        return None
    return m.group(1).strip()


def extract_entities_from_line(line, entities, index=None):
    """Parse a Graph Nodes payload back into a list of registry entity dicts.

    Wikilinks resolve to the registry by canonical name. Tags are matched by
    a normalised lookup of `#tag` → canonical name by stripping non-alphanum
    chars from each entity name and comparing.
    """
    if not line:
        return []
    if index is None:
        index = build_entity_index(entities)

    # Build a tag lookup: normalised-name -> entity
    tag_idx = {}
    for e in entities:
        if e["kind"] in TAG_KINDS:
            tag_idx[re.sub(r"[^0-9A-Za-z]+", "", e["name"]).lower()] = e

    found = []
    seen = set()

    for name in WIKILINK_RE.findall(line):
        hit = index.get(_norm(name))
        if hit and hit["name"] not in seen:
            seen.add(hit["name"])
            found.append(hit)

    for tag in TAG_RE.findall(line):
        hit = tag_idx.get(tag.lower())
        if hit and hit["name"] not in seen:
            seen.add(hit["name"])
            found.append(hit)

    return found


def collect_entity_notes(cfg):
    """Walk the vault and return `[(note_path, [entity_dict, ...]), ...]`
    for every daily AND weekly that has a Graph Nodes line.

    This is the input to co-occurrence analysis: each tuple is one observation
    of "these entities were used together."
    """
    entities = load_entities(cfg)
    idx = build_entity_index(entities)
    vault = cfg["_vault"]
    rollup_prefixes = ("Biweekly_", "Monthly_")  # Weekly_ is KEPT
    out = []
    for p in sorted(vault.rglob("*.md")):
        rel_parts = p.relative_to(vault).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        if rel_parts[0] in ("entities", "themes"):
            continue
        if p.name.startswith(rollup_prefixes):
            continue
        try:
            text = p.read_text()
        except OSError:
            continue
        line = parse_graph_nodes_line(text)
        if not line:
            continue
        ents = extract_entities_from_line(line, entities, idx)
        if ents:
            out.append((p, ents))
    return out


# ---------- entity registry -----------------------------------------------

ENTITY_REGISTRY_NAME = ".entities.yaml"
ENTITY_STUB_DIR = "entities"
WIKILINK_KINDS = {"hardware", "platform"}
TAG_KINDS = {"software", "protocol", "concept"}

# Targets whose generated entries get a `**Graph Nodes:**` line. Biweekly /
# monthly / final-report are deliberately excluded — they aggregate weeks
# of work and the entity list would just be the union of their constituents,
# adding noise to the graph view without any new information.
GRAPH_NODES_TARGETS = {"daily", "weekly"}


def entity_registry_path(cfg):
    return cfg["_vault"] / ENTITY_REGISTRY_NAME


def load_entities(cfg):
    """Load the entity registry. Returns a list of dicts: each has
    `name`, `kind`, `aliases` (list), `parent` (str or ""), and optional
    `description`.

    Missing/empty registry returns an empty list — the classifier will then
    propose every entity it finds as a new one for approval.
    """
    p = entity_registry_path(cfg)
    if not p.exists():
        return []
    with open(p) as f:
        data = yaml.safe_load(f) or {}
    entities = data.get("entities") or []
    out = []
    for e in entities:
        if not isinstance(e, dict) or "name" not in e or "kind" not in e:
            continue
        out.append({
            "name": e["name"],
            "kind": e["kind"],
            "aliases": list(e.get("aliases") or []),
            "parent": e.get("parent") or "",
            "description": e.get("description", ""),
        })
    return out


def build_children_map(entities):
    """Return parent_name -> [child entity dict, ...]. Skips entries without
    a parent. Children are sorted by name for stable output.
    """
    children = {}
    for e in entities:
        parent = e.get("parent")
        if not parent:
            continue
        children.setdefault(parent, []).append(e)
    for parent in children:
        children[parent].sort(key=lambda x: x["name"])
    return children


def save_entities(cfg, entities):
    """Persist the registry back to disk. Preserves the comment header by
    rewriting the YAML body below it.
    """
    p = entity_registry_path(cfg)
    header = ""
    if p.exists():
        text = p.read_text()
        body_start = text.find("entities:")
        if body_start > 0:
            header = text[:body_start]
    body = yaml.safe_dump(
        {"entities": entities},
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )
    p.write_text((header or "") + body)


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def build_entity_index(entities):
    """Return a dict mapping normalised name/alias -> entity dict. Used for
    fast case-insensitive lookup by the classifier.
    """
    idx = {}
    for e in entities:
        idx[_norm(e["name"])] = e
        for a in e.get("aliases", []):
            idx[_norm(a)] = e
    return idx


def find_entity(text, entities, index=None):
    """Resolve `text` to a registry entity by name or alias (case-insensitive).
    Returns the entity dict or None.
    """
    if index is None:
        index = build_entity_index(entities)
    return index.get(_norm(text))


def ensure_entity_stub(cfg, entity, children_map=None, entities=None):
    """Idempotently write `logbook/entities/<Name>.md` for a wikilinkable
    entity. Always rewrites so that hierarchy edges (Parent / Children) stay
    fresh after registry edits — this is cheap and keeps the graph honest.

    Stub files are written for hardware AND platform kinds. Software /
    protocol / concept entities use `#tag` form in dailies and don't get
    stubs (the tag itself is the graph node).

    `children_map` and `entities` are optional optimisations for batch runs.
    """
    if entity["kind"] not in WIKILINK_KINDS:
        return None
    if entities is None:
        entities = load_entities(cfg)
    if children_map is None:
        children_map = build_children_map(entities)
    idx = build_entity_index(entities)

    stem = entity["name"]
    p = cfg["_vault"] / ENTITY_STUB_DIR / f"{stem}.md"
    p.parent.mkdir(parents=True, exist_ok=True)

    aliases = entity.get("aliases") or []
    alias_lines = "\n".join(f"  - {a}" for a in aliases)
    fm = (
        "---\n"
        f"name: {stem}\n"
        f"kind: {entity['kind']}\n"
        + (f"aliases:\n{alias_lines}\n" if aliases else "")
        + "---\n\n"
    )

    desc = entity.get("description") or ""
    body = f"# {stem}\n\n"
    if desc:
        body += f"{desc}\n\n"

    # Parent edge — only render if the parent exists in the registry, so we
    # don't leak unresolved wikilinks into the graph.
    parent = entity.get("parent") or ""
    if parent:
        parent_entity = idx.get(_norm(parent))
        if parent_entity is not None:
            body += f"## Parent\n\n[[{parent_entity['name']}]]\n\n"

    # Children — wikilinks for wikilinkable kids, #tags for software/etc.
    kids = children_map.get(stem, [])
    if kids:
        body += "## Children\n\n"
        wikilink_kids, tag_kids = [], []
        for k in kids:
            if k["kind"] in WIKILINK_KINDS:
                wikilink_kids.append(f"[[{k['name']}]]")
            else:
                tag_kids.append(f"#{re.sub(r'[^0-9A-Za-z]+', '', k['name'])}")
        if wikilink_kids:
            body += " · ".join(wikilink_kids) + "\n\n"
        if tag_kids:
            body += " ".join(tag_kids) + "\n\n"

    body += (
        "> Stub auto-generated by the work-logs entity registry.\n"
        "> Parent / Children sections are owned by the registry — edits below\n"
        "> are safe.\n"
    )

    p.write_text(fm + body)
    return p


def ensure_all_entity_stubs(cfg, entities=None):
    """Sweep: rewrite every wikilinkable entity's stub so the hierarchy and
    aliases reflect the current registry. Returns the list of paths touched.
    """
    if entities is None:
        entities = load_entities(cfg)
    children_map = build_children_map(entities)
    written = []
    for e in entities:
        if e["kind"] not in WIKILINK_KINDS:
            continue
        p = ensure_entity_stub(cfg, e, children_map=children_map, entities=entities)
        if p is not None:
            written.append(p)
    return written


def append_entity(cfg, entity):
    """Append a new entity to the registry and create its stub if applicable.
    Idempotent — if the canonical name already exists, returns the existing
    entry without modification.
    """
    entities = load_entities(cfg)
    idx = build_entity_index(entities)
    existing = idx.get(_norm(entity["name"]))
    if existing is not None:
        return existing
    entities.append({
        "name": entity["name"],
        "kind": entity["kind"],
        "aliases": list(entity.get("aliases") or []),
        "description": entity.get("description", ""),
    })
    save_entities(cfg, entities)
    ensure_entity_stub(cfg, entity)
    return entity


def format_graph_nodes(resolved, proposed=None):
    """Format the inline `**Graph Nodes:**` line for a daily entry.

    `resolved` is a list of entity dicts (already classified). Wikilinkable
    kinds render as [[Name]]; tag kinds render as #PascalCaseName.
    `proposed` is an optional list of strings shown as bare text so the user
    notices them while reviewing.
    """
    links = []
    tags = []
    for e in resolved:
        if e["kind"] in WIKILINK_KINDS:
            links.append(f"[[{e['name']}]]")
        else:
            # Convert "SE(2) Composition" -> "#SE2Composition"
            tag = re.sub(r"[^0-9A-Za-z]+", "", e["name"])
            tags.append(f"#{tag}")
    parts = []
    if links:
        parts.append(", ".join(links))
    if tags:
        parts.append(" ".join(tags))
    out = " · ".join(parts)
    if proposed:
        out += f" · _proposed: {', '.join(proposed)}_"
    return out


# ---------- Louvain community detection ----------------------------------

def build_cooccurrence_graph(notes):
    """Given `[(path, [entity, ...]), ...]`, return an undirected weighted
    graph as `{node_name: {neighbor_name: weight}}`. Weight is the number of
    notes in which both nodes appear together.
    """
    graph = {}
    for _, ents in notes:
        names = sorted({e["name"] for e in ents})
        for i, a in enumerate(names):
            graph.setdefault(a, {})
            for b in names[i + 1:]:
                graph.setdefault(b, {})
                graph[a][b] = graph[a].get(b, 0) + 1
                graph[b][a] = graph[b].get(a, 0) + 1
    return graph


def _modularity(graph, communities, two_m):
    """Compute Q = (1/2m) Σ_ij [A_ij − k_i k_j / 2m] δ(c_i, c_j)."""
    if two_m == 0:
        return 0.0
    # node degree (sum of edge weights)
    degree = {n: sum(graph[n].values()) for n in graph}
    # group nodes by community
    members = {}
    for node, c in communities.items():
        members.setdefault(c, []).append(node)
    q = 0.0
    for nodes in members.values():
        for i in nodes:
            for j in nodes:
                a_ij = graph[i].get(j, 0)
                q += a_ij - (degree[i] * degree[j]) / two_m
    return q / two_m


def _louvain_phase1(graph, two_m, max_inner=100):
    """Local-move phase. Returns `{node: comm_id}` (each node in its own
    comm to start, then iteratively moved to maximise modularity gain).
    Loops until no node moves OR `max_inner` outer sweeps elapse.
    """
    node_to_comm = {n: i for i, n in enumerate(graph)}
    degree = {n: sum(graph[n].values()) for n in graph}
    # sigma_tot[c] = sum of degrees of nodes in community c
    sigma_tot = {i: degree[n] for n, i in node_to_comm.items()}

    inv_2m = 1.0 / two_m if two_m else 0.0

    for _ in range(max_inner):
        improved = False
        for node in graph:
            k_i = degree[node]
            own_comm = node_to_comm[node]

            # Compute weight from `node` into each neighbour-community.
            k_i_in = {}
            for nb, w in graph[node].items():
                c = node_to_comm[nb]
                k_i_in[c] = k_i_in.get(c, 0) + w
            # Self-loops on this node also contribute when own_comm is
            # the target (they count in the internal weight).
            self_loop = graph[node].get(node, 0)

            # "Remove" node from its own community for the gain calc.
            sigma_tot_own = sigma_tot[own_comm] - k_i
            own_k_in = k_i_in.get(own_comm, 0) - self_loop

            best_comm = own_comm
            best_gain = 0.0
            for c, w_in in k_i_in.items():
                if c == own_comm:
                    continue
                gain = (w_in - sigma_tot[c] * k_i * inv_2m) \
                     - (own_k_in - sigma_tot_own * k_i * inv_2m)
                if gain > best_gain:
                    best_gain = gain
                    best_comm = c

            if best_comm != own_comm and best_gain > 0:
                # Commit the move and update sigma_tot.
                sigma_tot[own_comm] -= k_i
                sigma_tot[best_comm] = sigma_tot.get(best_comm, 0) + k_i
                node_to_comm[node] = best_comm
                improved = True

        if not improved:
            break

    return node_to_comm


def _louvain_aggregate(graph, node_to_comm):
    """Phase 2 — collapse each community into a super-node. Returns
    `(new_graph, super_to_comm_id)` where the super-graph's nodes are the
    community IDs.
    """
    new_graph = {}
    for node, neigh in graph.items():
        c_node = node_to_comm[node]
        new_graph.setdefault(c_node, {})
        for nb, w in neigh.items():
            c_nb = node_to_comm[nb]
            new_graph[c_node][c_nb] = new_graph[c_node].get(c_nb, 0) + w
    return new_graph


def louvain_communities(graph, max_passes=20, min_modularity_gain=1e-6):
    """Run Louvain on an undirected weighted graph.

    `graph` shape: `{node: {neighbor: weight, ...}, ...}`. Returns
    `{node: community_id}` where community IDs are dense ints starting at 0.

    Multi-level: phase 1 (local move) then phase 2 (aggregate communities to
    super-nodes), repeated until modularity gain falls below
    `min_modularity_gain`. At every level, `current_graph` is keyed by the
    same labels as the previous level's phase-1 output, so composition into
    the `original_to_comm` map stays consistent.
    """
    if not graph:
        return {}

    two_m = sum(sum(neigh.values()) for neigh in graph.values())
    if two_m == 0:
        return {n: i for i, n in enumerate(graph)}

    # At every level, `original_to_current` maps each ORIGINAL node to its
    # node-label in `current_graph`. Initially identity.
    original_to_current = {n: n for n in graph}
    current_graph = {n: dict(neigh) for n, neigh in graph.items()}

    prev_q = _modularity(current_graph, {n: i for i, n in enumerate(current_graph)}, two_m)

    for _ in range(max_passes):
        # Phase 1: `{current_node: comm_id}`.
        node_to_comm = _louvain_phase1(current_graph, two_m)
        new_q = _modularity(current_graph, node_to_comm, two_m)
        if new_q - prev_q < min_modularity_gain:
            # No useful improvement; stop and use the previous composition.
            break
        prev_q = new_q

        # Compose: original_node -> comm_id at this level.
        original_to_current = {
            orig: node_to_comm[curr] for orig, curr in original_to_current.items()
        }

        # Aggregate current_graph using `node_to_comm`. Super-nodes are the
        # community IDs from phase 1, matching what original_to_current now
        # points at.
        current_graph = _louvain_aggregate(current_graph, node_to_comm)
        if len(current_graph) <= 1:
            break

    # Renumber communities to dense 0..K-1.
    remap = {}
    out = {}
    for n, c in original_to_current.items():
        if c not in remap:
            remap[c] = len(remap)
        out[n] = remap[c]
    return out


def name_cluster(client, model, members):
    """Ask Claude for a short, filename-safe theme name (2-4 words) that
    captures what the cluster's members have in common. Returns the slug.
    """
    bullets = "\n".join(f"  - {m}" for m in members)
    prompt = (
        "Here is a cluster of related engineering entities discovered by "
        "graph clustering across an internship log:\n\n"
        f"{bullets}\n\n"
        "Give this cluster a 2-4 word theme name that captures what they "
        "have in common. Examples of good names:\n"
        "  - 'Humanoid Locomotion Stack'\n"
        "  - 'Praxis Cloud Plane'\n"
        "  - 'Vendor Bring-up Patterns'\n"
        "Rules:\n"
        "- No quotes, no trailing punctuation, no filesystem-illegal chars.\n"
        "- Title Case-ish.\n"
        "- Specific, not generic ('Locomotion Stack' beats 'Robotics').\n"
        "Respond with ONLY the theme name."
    )
    response = client.messages.create(
        model=model,
        max_tokens=32,
        system="You produce concise theme labels. Output only the label.",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip().strip("\"'`").strip()
    raw = raw.splitlines()[0] if raw else ""
    return slugify_topic(raw, max_words=4, max_chars=48) or "Untitled Theme"


def ensure_theme_stub(cfg, theme_name, members, summary=""):
    """Idempotently write `logbook/themes/<name>.md` with a `## Members`
    block of wikilinks for hardware/platform members and tags for
    software/protocol/concept members. Returns the stub path.

    Members are expected to be a list of entity NAMES (strings); they're
    resolved against the live registry so we render the correct form.
    """
    entities = load_entities(cfg)
    idx = build_entity_index(entities)
    p = cfg["_vault"] / "themes" / f"{theme_name}.md"
    p.parent.mkdir(parents=True, exist_ok=True)

    wikilink_members = []
    tag_members = []
    for m in members:
        ent = idx.get(_norm(m))
        if ent is None:
            continue
        if ent["kind"] in WIKILINK_KINDS:
            wikilink_members.append(f"[[{ent['name']}]]")
        else:
            tag_members.append(f"#{re.sub(r'[^0-9A-Za-z]+', '', ent['name'])}")

    fm = (
        "---\n"
        f"name: {theme_name}\n"
        "kind: theme\n"
        "---\n\n"
    )
    body = f"# {theme_name}\n\n"
    if summary:
        body += f"{summary}\n\n"
    body += "## Members\n\n"
    if wikilink_members:
        body += " · ".join(wikilink_members) + "\n\n"
    if tag_members:
        body += " ".join(tag_members) + "\n\n"
    body += (
        "> Auto-generated by Louvain community detection over the entity\n"
        "> co-occurrence graph. Re-runs may add/remove members.\n"
    )
    p.write_text(fm + body)
    return p


def communities_to_clusters(node_to_comm, min_size=3):
    """Group `{node: comm_id}` into `[[node, ...], ...]` clusters, sorted by
    size descending. Singletons (or clusters smaller than `min_size`) are
    dropped.
    """
    by_comm = {}
    for n, c in node_to_comm.items():
        by_comm.setdefault(c, []).append(n)
    clusters = [sorted(members) for members in by_comm.values()
                if len(members) >= min_size]
    clusters.sort(key=len, reverse=True)
    return clusters


def public_holidays(cfg):
    """Return the set of date objects configured as public holidays."""
    out = set()
    for s in (cfg or {}).get("public_holidays") or []:
        if isinstance(s, date):
            out.add(s)
            continue
        try:
            out.add(datetime.strptime(str(s), "%Y-%m-%d").date())
        except ValueError:
            continue
    return out


def is_workday(d, cfg=None):
    """Mon-Fri excluding configured public holidays."""
    if d.weekday() >= 5:
        return False
    return d not in public_holidays(cfg)


def last_workday_of_cycle(when, cfg=None):
    """Walk backward from the cycle's Sunday until we hit a workday.
    Returns that date — the day the biweekly preview auto-fires on.
    """
    _, cycle_end = cycle_window(when, cfg)
    d = cycle_end
    # In the absurd case a whole cycle is non-workdays, bail out at the start.
    cycle_start, _ = cycle_window(when, cfg)
    while d >= cycle_start and not is_workday(d, cfg):
        d -= timedelta(days=1)
    return d


def cycle_window(when, cfg=None):
    """Return (start_date, end_date) of the two-week cycle containing `when`.

    Start = Monday of the cycle's first week; end = Sunday of the cycle's
    second week.
    """
    start = internship_start(cfg)
    anchor_mon = _week_anchor_monday(start)
    cyc, _ = cycle_day(when, cfg)
    if cyc <= 0:
        return (when, when)
    cycle_start = anchor_mon + timedelta(days=(cyc - 1) * 14)
    cycle_end = cycle_start + timedelta(days=13)
    return (cycle_start, cycle_end)


def generate_biweekly_preview(client, model, cfg, framing, when):
    """Run the rollup pipeline for the cycle containing `when` and return
    (preview_text, source_dates, target_key, period_label, cycle_anchor).

    `cycle_anchor` is the date the biweekly should be filed *against* (used
    as `when=` in write_target / link_rollup_to_dailies). It's the Sunday of
    the cycle so the file lands in the cycle's end-month folder.
    Returns None if no dailies were found in the cycle window.
    """
    cycle_start, cycle_end = cycle_window(when, cfg)
    entries = collect_dailies_in_range(cfg, cycle_start, cycle_end)
    if not entries:
        return None

    period_label = f"{cycle_start.isoformat()} to {cycle_end.isoformat()}"
    concat = "\n\n".join(
        f"=== {d.strftime('%Y-%m-%d')} ===\n\n{text}" for d, text in entries
    )
    system, generation = build_rollup_prompts(
        cfg, framing, "biweekly", "biweekly", period_label
    )
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[
            {"role": "user", "content": f"Daily entries:\n\n{concat}\n\n{generation}"},
        ],
    )
    return {
        "preview": response.content[0].text,
        "source_dates": [d.isoformat() for d, _ in entries],
        "target_key": "biweekly",
        "period": period_label,
        "cycle_anchor": cycle_end.isoformat(),
    }


def cadence_to_target_key(cadence):
    return {
        "weekly": "weekly",
        "biweekly": "biweekly",
        "monthly": "monthly",
        "final-report": "final_report",
    }.get(cadence)
