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

# Characters illegal in filenames across major filesystems / Obsidian.
_TOPIC_BAD = re.compile(r'[\\/:*?"<>|\[\]#^]')


def slugify_topic(topic, max_words=5, max_chars=48):
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
            slug = slugify_topic(topic)
            rendered = template.format(date=when, topic=slug).rstrip()
            return vault_path(cfg, rendered)
        found = find_existing_target_path(cfg, target_key, when)
        if found is not None:
            return found
        # No existing entry, no topic — return a date-only placeholder so
        # `.exists()` returns False without raising on the format call.
        rendered = template.format(date=when, topic="").rstrip()
        return vault_path(cfg, rendered)

    return vault_path(cfg, template.format(date=when))


def find_existing_target_path(cfg, target_key, when=None):
    """Find an on-disk file matching the date prefix, regardless of topic
    suffix. Returns None if nothing is found.
    """
    when = when or date.today()
    template = cfg["targets"][target_key]["path"]
    if not _template_has_topic(template):
        path = vault_path(cfg, template.format(date=when))
        return path if path.exists() else None

    # Render the template with an empty topic to figure out the parent dir
    # and date prefix, then glob in that dir.
    rendered = template.format(date=when, topic="")
    placeholder = vault_path(cfg, rendered)
    parent = placeholder.parent
    if not parent.exists():
        return None
    prefix = when.strftime("%Y-%m-%d")
    matches = sorted(parent.glob(f"{prefix}*.md"))
    return matches[0] if matches else None


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
        frontmatter = f"---\naliases:\n  - {when.isoformat()}\n---\n\n"

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

def collect_dailies_in_range(cfg, start_date, end_date):
    """Read all daily entries with dates in [start_date, end_date].

    Walks `daily/` recursively so month-nested layouts (daily/YYYY-MM/...)
    and flat layouts both work.
    """
    daily_dir = vault_path(cfg, "daily")
    if not daily_dir.exists():
        return []
    entries = []
    for p in sorted(daily_dir.rglob("*.md")):
        m = DATE_RE.search(p.name)
        if not m:
            continue
        try:
            d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if start_date <= d <= end_date:
            entries.append((d, p.read_text()))
    return entries


def collect_recent_dailies(cfg, window_days):
    end = date.today()
    start = end - timedelta(days=window_days)
    return collect_dailies_in_range(cfg, start, end)


def rollup_stem(target_key, when=None):
    """The wikilink stem for a rollup of the given target on `when`.

    Mirrors the `path` template's filename, sans extension, so Obsidian
    wikilinks resolve to the correct note.
    """
    when = when or date.today()
    return {
        "weekly": when.strftime("%Y-W%V"),
        "biweekly": when.strftime("%Y-W%V"),
        "monthly": when.strftime("%Y-%m"),
        "final_report": "final_report",
    }.get(target_key)


def link_rollup_to_dailies(cfg, target_key, dailies, when=None):
    """After a rollup is saved, write bidirectional wikilinks so the Obsidian
    graph view connects the rollup node to each daily node.

    `dailies` is a list of (date, _text) tuples as returned by
    collect_dailies_in_range — text is ignored, only the dates are used.
    """
    if not dailies:
        return
    stem = rollup_stem(target_key, when)
    if not stem:
        return

    rollup_path = resolve_target_path(cfg, target_key, when)
    if rollup_path.exists():
        links = " ".join(f"[[{d.isoformat()}]]" for d, _ in dailies)
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


def cadence_to_target_key(cadence):
    return {
        "weekly": "weekly",
        "biweekly": "biweekly",
        "monthly": "monthly",
        "final-report": "final_report",
    }.get(cadence)
