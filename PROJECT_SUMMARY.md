# Project Summary — work-logs

A localhost web UI for capturing daily work as structured markdown, rolling entries into weekly / biweekly / monthly / final reports, and building a richly-connected Obsidian knowledge graph. Notes land in an Obsidian vault at `./logbook/`; conversation is driven by Claude via AWS Bedrock; sections, prompts, paths, and rollup cadences all live in `config.yaml`.

This summary covers the full transformation from a "tidy notes" tool into an actual knowledge graph with semantic naming, hierarchical entities, and Louvain community detection.

---

## 1. Project Overview

- **Backend**: Flask (`server.py`) + shared core logic (`core.py`); Claude via AWS Bedrock.
- **Frontend**: Vanilla JS single-page UI (`static/index.html`, `static/app.js`).
- **Vault**: `./logbook/` — Obsidian vault, hierarchically organised.
- **Config**: `config.yaml` — paths, sections, framings, rollup cadences, internship anchor, public holidays.

Run with `python server.py` → `http://127.0.0.1:5000`.

---

## 2. Implemented Features

### 2.1 Report framing (high-achiever, no blockers)
- Sections across daily / weekly / biweekly: **Summary · Shipped · Technical Highlights · Impact · Academic Connections**
- Monthly: **Executive Summary · Major Themes · Technical Highlights · Impact · Academic Reflections**
- Framing prompts (system, generation, amend, rollup, catchup) explicitly drop blockers. Resolved problems are framed as Impact wins.

### 2.2 Raw input persistence
- `core.save_raw_input(cfg, messages, kind, when)` appends the full brain-dump + Q&A turns to `logbook/{Month}/Week_{N}/raw/{DD-MM-YY}.md` on save.
- Called from both `/api/log/save` and `/api/catchup/save`. Skipped on cancel.

### 2.3 Folder structure (month + week-nested)
- `internship_start: 2026-05-18` anchor, **Mon–Sun calendar weeks**.
- Dailies: `{Month}/Week_{N}/{topic}.md`
- Weeklies: `{Month}/Week_{N}/{topic}.md`
- Biweeklies: `{cycle_month}/{topic}.md` (cycle_month = month containing cycle's last day)
- Monthlies: `{Year}/Monthly_{Month}.md`
- Raw input: `{Month}/Week_{N}/raw/{DD-MM-YY}.md`

### 2.4 Semantic filenames (topic-only, LLM-picked)
- `core.pick_topic(client, model, entry_markdown)` asks Claude for a 2–7 word filename topic.
- `core.slugify_topic()` strips filesystem-illegal chars, caps at 7 words / 64 chars.
- **Aliases frontmatter** auto-injected in every daily/weekly/biweekly so legacy `[[YYYY-MM-DD]]`, `[[DD-MM-YY]]`, `[[Weekly_W4]]`, `[[2026-W26]]` wikilinks still resolve.

### 2.5 Workday-aware biweekly auto-fire
- `core.cycle_day(when)` returns `(cycle_idx, day_in_cycle 1..14)`.
- `core.cycle_window(when)` returns `(Mon, Sun)` for the 14-day cycle.
- `core.is_workday(d)` = Mon–Fri AND not in SG public holidays.
- `core.last_workday_of_cycle(when)` walks back from cycle Sunday until a workday.
- `/api/log/save` triggers `generate_biweekly_preview` when `today == last_workday_of_cycle(today)` — typically the **last Friday of the cycle**.
- Preview returned inline in save response; UI shows editable card; user edits and saves to `/api/rollup/save` with `anchor_date` so file lands in cycle's end-month folder.

### 2.6 Bidirectional rollup ↔ daily backlinks
- `core.link_rollup_to_dailies(cfg, target_key, dailies, when)` writes:
  - `## Source dailies` block in rollup with `[[DD-MM-YY]]` wikilinks
  - `## Rolled up into` line in each daily with `[[<rollup stem>]]` wikilink
- Idempotent — re-runs don't duplicate.

### 2.7 Graph Nodes question + LLM classifier
- After Q&A completes, server asks one final question: *"What core hardware, platforms, and abstract concepts did you focus on today?"*
- User answers via `/api/log/graph_nodes` (or skips → infers from conversation).
- `core.classify_entities()` runs against the canonical registry, returns `{resolved, proposed}`.
- Generation prompt is augmented to inject `**Graph Nodes:** [[X]], [[Y]] · #a #b` directly under the date heading.

### 2.8 Entity registry (`logbook/.entities.yaml`)
- **74 entities total** across 5 kinds:
  - `hardware` / `platform` → rendered as `[[Wikilinks]]`, get stub files in `logbook/entities/<Name>.md`
  - `software` / `protocol` / `concept` → rendered as `#tags`, no stub files
- Each entity: `name`, `kind`, `aliases`, `parent` (optional), `description` (optional).
- New entities proposed by the classifier surface as checkbox approvals on the preview screen; only approved ones land in the registry.
- Hardware/platform auto-create stub files via `core.ensure_entity_stub()` so wikilinks resolve to real graph nodes.

### 2.9 Entity hierarchies (parent ↔ child)
- 21 parent assignments across the registry. Examples:
  - `Unitree` → `Unitree Go2`
  - `Agibot` → `Agibot A2 Ultra`, `Agibot X2 Ultra`, `Agibot D1 Max`, `AIMDK`
  - `RobotEra` → `RobotEra Q5`, `XOS Runtime`
  - `Praxis Platform` → `Praxis SDK`, `Praxis Agents`
  - `ROS 2` → `ROS Topic`, `ROS Service`, `ROS Action`, `Multi-threaded Executor`, `QoS`, `colcon`
  - `DDS` → `CycloneDDS`
  - `Dead Reckoning` → `SE(2) Composition`, `Quaternion to Euler`, `EMA Filter`, `Deadband Threshold`, `Two-phase Translate-Rotate`
  - `Google ADK` → `LiteLLM`
  - `OpenAI-compatible API` → `Tool Calling`
  - `Incident Response` → `Staged Verification`
  - `Vendor Abstraction` → `Provider Abstraction`
- Entity stubs render `## Parent` + `## Children` blocks for bidirectional graph edges.

### 2.10 Louvain community detection
- `core.collect_entity_notes(cfg)` walks the vault, parses `**Graph Nodes:**` lines, returns `[(path, [entity_dict, ...]), ...]`.
- `core.build_cooccurrence_graph(notes)` builds weighted undirected graph (nodes = entities, edges = co-mentions).
- `core.louvain_communities(graph)` — pure-Python implementation, two-phase (local-move + aggregate), modularity-maximizing.
- `core.name_cluster(client, model, members)` asks Claude for a 2–4 word theme name.
- `core.ensure_theme_stub(cfg, theme_name, members)` writes `logbook/themes/<name>.md` with `## Members` block.
- Notes with ≥3 entities in a cluster get `**Theme:** [[<name>]] (N shared)` line under their Graph Nodes line.

### 2.11 Singapore 2026 public holidays
Hardcoded in `config.yaml`:
- Jan 1 (New Year), Feb 17–18 (CNY), Mar 21 (Hari Raya Puasa), Apr 3 (Good Friday), May 1 (Labour Day), May 27 (Hari Raya Haji), Jun 1 (Vesak observed), Aug 10 (National observed), Nov 9 (Deepavali observed), Dec 25 (Christmas)

---

## 3. Files Changed

| File | Purpose |
|---|---|
| `config.yaml` | Internship anchor, public holidays, path templates with `{month}/{week}/{topic}/{cycle_month}/{week_pair_full}` tokens |
| `core.py` | Week math, cycle math, workday helpers, path resolver, entity registry, classifier, Louvain, biweekly preview, theme stubs |
| `server.py` | New endpoints: `/api/log/graph_nodes`; modified `/api/log/save` for biweekly auto-fire + entity approval; `/api/rollup` returns `topic` + `source_dates`; `/api/rollup/save` accepts `anchor_date` + `topic` |
| `static/index.html` | Topic input field, biweekly preview card, Graph Nodes proposals checklist |
| `static/app.js` | Topic threading, graph-nodes Q&A flow, biweekly preview rendering, proposal approval state |
| `logbook/.entities.yaml` | 74-entity canonical registry with aliases + parent hierarchy |
| `logbook/.obsidian/graph.json` | `showTags: true` to surface tag nodes in graph view |

One-shot scripts used during this session (not part of the runtime):
- `backfill_graph_nodes.py` — injected Graph Nodes into existing dailies
- `backfill_weekly_graph_nodes.py` — same for weeklies
- `build_themes.py` — ran Louvain + materialised theme stubs

---

## 4. Key Decisions

| Decision | Rationale |
|---|---|
| **Topic-only filenames** for everything (no date prefixes) | Obsidian graph view uses filename as node label; semantic names beat dates |
| **Aliases frontmatter** carries every historical wikilink form | Preserves backwards-compat: `[[2026-06-08]]`, `[[08-06-26]]`, `[[Weekly_W4]]` all still resolve |
| **Biweeklies/monthlies excluded from Graph Nodes** | Aggregators duplicate their constituents' entities — noise without information |
| **Hardware/platform → wikilinks, everything else → tags** | Hardware are the central visual hubs; tags filter the graph noise and enable metadata search |
| **Bidirectional parent/child** in entity stubs | Doubles graph edges, tightens visual clustering |
| **Recipe-style prompts** over abstract | *Prompt specificity inversely correlates with required model capability* — the methodological insight |
| **Self-hosted vLLM + LiteLLM** | Cost predictability, data residency, latency floor, no silent model drift, provider-agnostic |
| **Vendor-agnostic Praxis SDK** | Three robots × three SDKs × three locomotion API models = one platform schema |
| **Workday-aware biweekly fire** | Fires on cycle's last Friday (skipping SG holidays) so weekend off doesn't miss the trigger |
| **Manual approval for new entities** | Prevents registry fragmentation from LLM-coined variants |

---

## 5. Issues Resolved

| Issue | Resolution |
|---|---|
| Original report was thin compared to source material | Rewrote biweekly with Mermaid architecture diagram, full driver depth, Praxis-as-hub framing |
| Date-prefixed graph node labels were unreadable | Migrated to topic-only filenames; aliases preserve old wikilinks |
| Weeklies/biweeklies inconsistently named (`Weekly_W4`, `Biweekly_W5-W6`) | LLM-picked topic names for rollups too; `pick_topic` integrated into `/api/rollup` + `generate_biweekly_preview` |
| Graph view was empty | Added bidirectional backlinks; enabled `showTags: true`; populated entity stubs |
| Entity names fragmenting (`[[Go2]]` vs `[[Unitree Go2]]`) | Canonical registry with aliases; classifier matches case-insensitively |
| `find_existing_target_path` returned wrong file for weekly fallback | Restricted alias-based date lookup to `target_key == "daily"` |
| Day-14 biweekly trigger would miss weekends | Replaced with `today == last_workday_of_cycle(today)` |
| Filename truncation on slug cap | Bumped `slugify_topic` from 5 words / 48 chars to 7 / 64 |
| Topic resolution returned empty `.md` for rollups without topic | `_render_template` falls back to `rollup_stem(target_key)` → `Weekly_W4` etc. |
| Stale `daily/` and `biweekly/` directories from old layout | Cleaned up during migration |

---

## 6. Vault Inventory (Final State)

```
logbook/
├── .entities.yaml                  (74-entity registry)
├── .obsidian/                      (Obsidian config, graph.json)
├── entities/                       (21 stub files for hardware/platform)
├── themes/                         (6 Louvain-detected themes)
├── May/
│   ├── Unitree Go2 ROS 2 Integration.md       (Biweekly_W1-W2 catchup)
│   ├── Week_1/Q5 data collection bring-up.md
│   └── Week_2/SE(2) dead-reckoning bug.md
└── June/
    ├── Multi-Robot Incident Response Integration.md  (Biweekly_W5-W6)
    ├── Week_3/  (Jun 1–7)
    │   ├── RTSP auth fix.md
    │   └── Go2 end-to-end demo.md
    ├── Week_4/  (Jun 8–14, Agibot A2 week)
    │   ├── A2 systemd substrate.md
    │   ├── A2 discrete dead-reckoning.md
    │   ├── A2 BMS service and QoS.md
    │   ├── A2 map-id and FastDDS profile.md
    │   ├── X2 multi-source arbitration.md
    │   ├── X2 IMU pose and whole-body joints.md
    │   └── Agibot A2 Ultra ROS2 Integration.md  (Weekly_W4)
    ├── Week_5/  (Jun 15–21, X2 + Q5 week)
    │   ├── X2 TTS and image streaming.md
    │   ├── Q5 FSM and CycloneDDS.md
    │   ├── Q5 TwistStamped and dead-reckoning.md
    │   ├── Q5 motion replay settle detection.md
    │   └── Agibot X2 and RobotEra Q5 Integration.md  (Weekly_W5)
    └── Week_6/  (Jun 22–26, agentic-layer week)
        ├── Gemma E4B vLLM bring-up.md
        ├── Gemma 26B on Blackwell.md
        ├── impact_agent ADK build.md
        ├── Prompt and integration debug.md
        ├── Fallen boxes live demo.md
        └── Multi-Robot Agentic Incident Response.md  (Weekly_W6)
```

**Totals:** 14 dailies · 3 weeklies · 2 biweeklies · 21 entity stubs · 6 theme stubs · 74 registry entries

---

## 7. Louvain Themes (Auto-detected)

Ran across 22 notes (54-node, 691-edge co-occurrence graph). 3 final clusters with modularity Q ≈ 0.12:

| Theme | Members | Notes tagged |
|---|---|---|
| `ROS 2 Robotics Middleware` | 28 | A2 / X2 / Q5 driver dailies + middleware-heavy weeklies |
| `Robotics Integration Infrastructure` | 20 | Platform-side dailies + agentic-layer dailies |
| `Video Streaming Infrastructure` | 6 | RTSP / V4L2 / FFmpeg-heavy entries |

Older theme stubs from earlier runs (`Praxis Integration Toolchain`, `Robot Middleware Integration`, `Robotics Middleware Infrastructure`) are still on disk and can be pruned if stale.

---

## 8. Current Status

✅ **Shipped and pushed to GitHub** (`origin/latest-naming` at HEAD `db1de0a`).

- All four chunks of the original redesign complete: layout refactor, day-14 biweekly auto-fire, entity registry + stubs, Graph Nodes classifier
- Plus: entity hierarchies, Louvain clustering, topic-named rollups, SG workday-aware trigger
- Week 6 (Jun 22–26) dailies + Weekly_W6 + Biweekly_W5–W6 written
- Boss demo greenlit for the Impact event

---

## 9. Next Steps (Possible Future Work)

- **Monthly rollup** — same `pick_topic` flow, fires manually via `/api/rollup`
- **Final report** — synthesises all biweeklies + monthlies at internship end
- **Theme re-clustering on a cadence** — currently a manual one-shot; could fire monthly
- **Server-side tool consolidation** for `impact_agent` — collapse `list_camera_info + capture_image + video_reasoning` into one tool to close the Gemma parallel-tool-calls gap
- **Decide model strategy** between Bedrock Claude and local Gemma 26B for production
- **`prompt.py` reconciliation** for `impact_agent` — on-disk 199 lines vs memory's described 95-line rewrite
- **Pruning stale Louvain theme stubs** from earlier clustering runs
- **Automation cron** for theme re-detection + monthly rollup

---

*Generated 2026-06-28 from session conversation. See individual daily/weekly/biweekly notes for full technical depth.*
