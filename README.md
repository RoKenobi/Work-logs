# work-logs

A localhost web UI for capturing daily work as structured markdown, then rolling
entries up into weekly / biweekly / monthly / custom-range / final reports.
Notes land in an Obsidian vault (`./logbook/`). Conversation is driven by Claude
via AWS Bedrock; sections, prompts, and paths live in `config.yaml`.

## Layout

```
work_logs/
├── server.py         # Flask backend
├── core.py           # config, Claude client, file I/O (shared)
├── config.yaml       # sections, framings, paths, rollup windows
├── static/
│   ├── index.html    # single-page UI
│   ├── style.css
│   └── app.js
├── .env              # AWS_BEARER_TOKEN_BEDROCK lives here (gitignored)
└── logbook/          # Obsidian vault — all generated notes land here
    ├── daily/
    ├── weekly/
    ├── biweekly/
    ├── monthly/
    └── final_report.md
```

## Setup

```bash
pip install flask rich anthropic pyyaml
```

Create `.env` in the repo root:

```
AWS_BEARER_TOKEN_BEDROCK="your_token"
AWS_REGION=us-east-1
ANTHROPIC_DEFAULT_SONNET_MODEL=us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

## Run

```bash
python server.py
```

Then open <http://127.0.0.1:5000>.

## Three modes

- **Today** — drop a brain dump, answer follow-ups, preview & save a daily entry.
  - "Just save this, no questions" — skip Q&A entirely (terse / lazy-day mode).
  - "That's all" — finish Q&A early when you've covered everything.
  - Re-running on the same day **amends** the existing entry (one clean file per day).
- **Rollup** — synthesize daily entries into a weekly / biweekly / monthly /
  final-report file. Or check "custom date range" and pick any window.
- **Catchup** — for "I haven't logged in a month" days. Brain-dump the whole
  period; Claude generates one summary file PLUS dated highlight entries for
  3-5 memorable days. Uncheck any highlights you don't want kept.

Every save shows a preview first — edit before it lands in the vault.

## Configuration

`config.yaml` controls everything that isn't code:

- **`framings`** — system + generation prompts. Two are shipped: `internship`
  (academic / CS-theory framing, supervisor-clearance footer) and you can add
  more.
- **`targets`** — output files. Each has a `path` template, write `mode`
  (`amend`, `append`, or `write_or_append`), and `sections` that become the
  `###` headings in the generated entry.

Question count is **adaptive** — there are no fixed quotas. If the brain dump
is short or says "nothing happened today", Claude asks 0–1 questions and stops.

## Token notes

- Daily entries: typically 1 system prompt + 1–4 short conversation turns +
  one ~2k-token generation. Light days cost almost nothing.
- Rollups concatenate the raw daily entries in a single non-conversational
  call — most expensive operation, but you only run them on demand.
- `max_tokens` is set to 2048 for log/rollup generation, 4096 only for catchup
  (which produces summary + multiple highlight entries).
