---
date: 2026-06-24
---

# Daily

## June 24, 2026

**Graph Nodes:** [[Praxis Platform]], [[Praxis Agents]], [[Unitree Go2]], [[Agibot X2 Ultra]], [[RobotEra Q5]] · #GoogleADK #LiteLLM #Gemma #AWSBedrock #vLLM #Docker #MQTT #ToolCalling #VendorAbstraction #IncidentResponse

**Theme:** [[Robotics Integration Infrastructure]] (12 shared)

### Summary
Built `impact_agent` — a Google ADK agent that drives the Praxis multi-robot platform through a fixed incident-response playbook. Unlike the existing generic `robot_agent` (Claude Sonnet via Bedrock, one-off commands), this one runs a recipe-style multi-step scenario: observe → scout → verify → announce → casualty-check → report. Wired up to either local Gemma-26B (via the vLLM endpoint stood up yesterday) or Bedrock Claude through the same LiteLLM abstraction. 21 tools registered against the Praxis API.

### Shipped
- **`praxis_agents/agents/impact_agent/` package** — `agent.py` (`Agent(model=LiteLlm(_config.model), name="impact_agent", instruction=AGENT_INSTRUCTION, tools=tools + _config.toolsets)`), `config.json` (LiteLLM-prefixed model id), `prompt.py` (the 200-line recipe), `README.md`
- **LiteLLM provider routing** — `openai/google/gemma-4-26B-A4B-it` routes to the local vLLM via `OPENAI_API_BASE=http://localhost:9090/v1`; `bedrock/global.anthropic.claude-sonnet-4-6` routes to AWS Bedrock. Same `Agent` definition, model swap = config-only
- **21 tools wired** across 6 groups: Actions (`list_actions`, `send_action`, `cancel_action`, `monitor_action_execution`, `get_action_schema`), Devices (`list_registered_devices`, `list_online_devices`, `get_device_info`), Telemetry (`query_data`, `list_schemas`, `list_schema_aliases`, `get_alias_data`), Vision (`list_camera_info`, `capture_image`, `video_reasoning`), Incidents (`create_incident`, `add_incident_update`, `update_incident_status`, `update_incident_confidence`, `add_incident_action`), Geometry (`create_adjacent_pose`)
- **Provider-agnostic VLM client** at `praxis_agents/tools/impact_local_vlm/` — OpenAI-compatible vision endpoint client reading `VLM_*` env vars (falling back to `OPENAI_*`). Output is structured `{risk_level, description, objects_detected, confidence?}`. Works against the local vLLM, any hosted vision API, or whatever we put behind the env vars later
- **Recipe-style prompt** at `prompt.py` — fixed robot roles (Go2 = SCOUT first, X2 = ANNOUNCER second), literal payload structures (`pose.frame = {"type": "floor_plan", "id": ""}`), mandatory post-`video_reasoning` chain (`add_incident_update` → `update_incident_confidence` → `update_incident_status`), error recovery (retry once, then "manual review required"), narration discipline (exactly two narration moments: scout arrival + casualty detected)
- **Docker Compose plumbing** — `praxis_agents` service attaches to the external `praxis_robots_default` network so it can reach the robots API by hostname. Mounts `./praxis_agents` as a volume so prompt edits hot-reload via `docker compose restart praxis-agents` without an image rebuild

### Technical Highlights
- **Recipe-style prompts beat abstraction for smaller models.** Side-by-side trace: Claude (`robot_agent`) handled the fallen-boxes scenario cleanly with parallel tool calls, correct role assignment, and confidence escalation after `video_reasoning`. Local Gemma running the *same* abstract prompt did **none** of those things — single-threaded calls, never escalated confidence, swapped robot roles, bailed on the first `video_reasoning` error. The fix wasn't a smarter model; it was a more concrete prompt. Literal tool names instead of "the camera tool", literal payload JSON instead of "construct a pose", "in this exact order" instead of "consider doing X", bad-vs-good narration examples instead of abstract style guidance.
- **Mandatory chain after `video_reasoning` is the single highest-leverage prompt rule.** Without it, the agent gets visual evidence and then *forgets to record it* — confidence stays at 50 %, status never reaches `verified`, the incident record is half-empty. With it (`add_incident_update` + `update_incident_confidence` to 75 % or 95 % + `update_incident_status` if a person is detected, all in the same turn as the `video_reasoning` call), the incident record is always synchronised with what the robot actually saw.
- **Two-tier staged verification: 50 → 75 → 95 % confidence.** The numbers aren't arbitrary. 50 % = camera-only initial detection (the source signal that triggered the workflow). 75 % = Go2 scout's `video_reasoning` confirms the visual. 95 % = X2 announcer's casualty check rules out human harm. Each tier requires a different robot's evidence; the staged-verification pattern is the algorithmic contribution. Auditing the incident later, the confidence trace tells you *which sensor* produced *which evidence*, not just a final score.
- **Fixed role assignment beats letting the model pick.** Earlier traces had the agent dispatching the X2 first because the prompt asked it to "choose the appropriate robot." Hardcoding `unitree-go2` = SCOUT and `agibot-x2-ultra` = ANNOUNCER removes a degree of freedom the model was reliably getting wrong. Lost flexibility; gained correctness. For the demo Boss is about to see, correctness wins.
- **Provider-agnostic LiteLLM at the model boundary.** The agent's tool layer doesn't know whether it's talking to Claude on Bedrock or Gemma on vLLM — same `Agent` class, same `AGENT_INSTRUCTION`, same tools. Provider switch is a one-line `config.json` change. This is the lever that lets us A/B model strategies without rewriting agent code, and it's the same abstraction pattern as Praxis SDK's vendor-agnostic action schemas at the *robot* layer.
- **Hot-reload via volume mount.** Prompt iteration is the dominant work in agent development. Mounting `./praxis_agents` as a volume means `docker compose restart praxis-agents` picks up `prompt.py` edits in 2–3 s instead of a 30–60 s image rebuild. Critical for the prompt-tuning loop that's about to dominate the next two days.

### Impact
- `impact_agent` selectable in the ADK web UI at `http://localhost:8001`. Discovery and single-action execution work reliably on both Claude and Gemma. The full 8-phase scenario (Praxis multi-robot incident response) is wireable end-to-end starting tomorrow.
- Provides the *control plane* for the upcoming Boss demo — natural-language command in, three-robot choreographed response out, fully recorded in the Praxis Incident system. The whole point of the integration work from weeks 3–5 (vendor abstraction, schema-driven SDK, capability-based dispatch) gets validated when this agent dispatches Go2, X2, and Q5 through identical schemas without knowing they're different vendors.
- Local-Gemma path means the demo can run *air-gapped* — no Bedrock dependency for the actual incident-response loop, important for both cost (no per-token billing during repeated rehearsals) and reliability (no internet dependency during the Boss demo or the impact event).
- Confidence staging (50 → 75 → 95) is now a reusable pattern. Any future incident type — fire, intrusion, equipment failure — slots into the same staged-verification template: source-signal confidence → first-tier robot confirms → second-tier robot rules out human harm. The schema is workflow-agnostic.

### Academic Connections
- **AI agents / orchestration.** Recipe-style prompts as a forcing function for smaller models — the algorithmic insight is that *prompt specificity inversely correlates with required model capability*. A 4B-active model with a 200-line recipe outperforms a 4B-active model with a 30-line abstraction. Maps to imitation learning's "behavioural cloning with detailed action sequences."
- **Software architecture.** LiteLLM as a model-provider abstraction layer at the agent boundary — the *agent* code stays vendor-neutral, the *provider* string is the only thing that knows it's Bedrock vs OpenAI-compatible vs Anthropic-native. Same pattern as Praxis SDK's vendor-agnostic action schemas at the robot boundary. Composable abstractions stack: vendor-neutral robots × vendor-neutral models = workflow-neutral incident responses.
- **Distributed systems.** Tool layer as a service mesh between the agent's reasoning and the Praxis platform's MQTT/REST surface. Async Python tools with structured request/response shapes; failure-modes propagate as exceptions that the agent reasons over rather than crashing.
- **Decision theory / Bayesian updating.** Staged-verification confidence escalation (50 → 75 → 95) is the agentic implementation of likelihood ratios: each new sensor's evidence multiplies into the posterior. The numbers are tunable per scenario and per sensor reliability.
- **Software engineering.** Hot-reload via volume mount is a small operational detail with large effect on iteration velocity. Same pattern as `colcon build --symlink-install` for ROS 2 Python entry points — when iteration is the bottleneck, optimise the inner loop, not the build system.

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
