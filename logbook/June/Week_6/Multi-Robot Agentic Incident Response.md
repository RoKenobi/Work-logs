---
aliases:
  - Weekly_W6
  - 2026-W27
---

# Weekly

## June 26, 2026

**Graph Nodes:** [[Praxis Platform]], [[Praxis Agents]], [[Unitree Go2]], [[Agibot X2 Ultra]], [[RobotEra Q5]], [[Jetson Orin]] · #vLLM #Gemma #GoogleADK #LiteLLM #AWSBedrock #Docker #HuggingFace #OpenAIcompatibleAPI #ToolCalling #PagedAttention #ContinuousBatching #IncidentResponse #VendorAbstraction #MQTT

**Theme:** [[Robotics Integration Infrastructure]] (16 shared)

### Summary
Shipped the agentic layer that sits on top of the multi-robot integration work from weeks 3–5. Mon–Tue: stood up a self-hosted vLLM-served Gemma 26B on the workstation Blackwell GPU with an OpenAI-compatible HTTP API, resolving the CUDA Error 803 cuda-compat shadow on the way. Wed: built `impact_agent` — a Google ADK + LiteLLM agent driving the Praxis platform through a fixed incident-response playbook with 21 tools and a recipe-style 200-line prompt. Thu: hardened the prompt against role swaps, wrong-destination bugs, and missed post-`video_reasoning` updates. Fri: live demo to leadership — 2m 9.4s end-to-end multi-robot fallen-boxes incident response, greenlit for the Impact event.

### Shipped
- **`local_llm` self-hosted vLLM project** — Docker Compose template + Makefile of per-model presets. `gemma-e4b` preset retired in favour of `gemma-4-26B-A4B-it` after E4B regressed on the agent workload. OpenAI-compatible `/v1/chat/completions` endpoint on `:9090`, byte-stable via pinned `vllm-openai:v0.21.0` image, host-mounted HF cache, `--enable-auto-tool-choice --tool-call-parser gemma4` for structured tool calls.
- **`praxis_agents/agents/impact_agent/` package** — `Agent(model=LiteLlm(...), tools=tools + _config.toolsets)`, LiteLLM provider routing (`openai/google/gemma-4-26B-A4B-it` → local vLLM, `bedrock/global.anthropic.claude-sonnet-4-6` → AWS Bedrock), 21 tools across 6 groups (Actions, Devices, Telemetry, Vision, Incidents, Geometry), recipe-style prompt with fixed robot roles + mandatory post-`video_reasoning` update chain.
- **Provider-agnostic VLM client** at `praxis_agents/tools/impact_local_vlm/` reading `VLM_*` / `OPENAI_*` env vars, OpenAI-shaped vision endpoint, structured `{risk_level, description, objects_detected}` output.
- **Hardened recipe prompt** — fixed roles (`unitree-go2 = SCOUT`, `agibot-x2-ultra = ANNOUNCER`, `robotera-q5 = INTERVENER`), same-location dispatch (no more X2 to "demo hall"), narration discipline (2 narration moments only), `video_reasoning` retry-once-then-degrade error recovery, fixed-template final report.
- **Boss demo run, recorded** — `fallen_boxes-incident-inference-2026-06-26T02:41:16` session: 26 agent events, 2m 9.4s end-to-end, three robots orchestrated through identical Praxis action schemas, staged confidence escalation 50 → 75 → 95%, greenlit for the Impact event.

### Technical Highlights
- **Self-hosted vLLM as the platform inversion.** Hosted APIs charge per token and let the provider change the model behind the same name. Self-hosting flips both: fixed amortized GPU cost (zero marginal per token), byte-stable model behaviour via pinned image + pinned weights. The Praxis stack's central LLM dependency is now a config-knob in our control. The two reasons the change was achievable: vLLM ships an OpenAI-compatible HTTP API (no client code changes), and `PagedAttention` + continuous batching make the GPU work hard enough that a 26B-active model can compete with hosted Claude on wall-clock for our workload.
- **PagedAttention + continuous batching = real throughput.** Two well-engineered ideas. PagedAttention splits KV cache into fixed-size blocks allocated lazily per sequence — sequences only use the VRAM they actually need; fragmentation collapses; the GPU holds many more concurrent requests for the same memory budget. Continuous batching schedules at the *token* level: a sequence's `<eos>` frees its slot mid-forward-pass and a queued request slides in. Both are why an agentic workload (26+ tool calls per incident, bursty) gets near-hosted-API throughput out of a single GPU.
- **Blackwell + cuda-compat = CUDA Error 803 at startup, single-line fix.** The vLLM image's `cuda-compat` layer ships `libcuda.so.1` built for drivers `< 571`. Our host runs driver 580. The compat lib intended to let newer CUDA run on older drivers; here the host driver is newer than the compat lib expects, so the stale lib *shadows* the real one. Fix: prepend host library paths to `LD_LIBRARY_PATH` in compose so the loader picks up the real `libcuda.so.1` first. Class-of-failure-mode that looks like a GPU problem but is a linker priority problem.
- **Recipe-style prompts beat abstraction for any model size.** The breakthrough on Wednesday: the *same* prompt that handled the fallen-boxes scenario when written abstractly ("dispatch the appropriate robot for visual recon") failed on Gemma and was unreliable even on Claude. Rewriting it as a literal recipe — fixed role table, literal payload JSON, "in this exact order", "in the SAME TURN as `video_reasoning`, call X then Y then Z", bad-vs-good narration examples — collapsed the failure surface. Same model, same task, ~100x more reliable. The algorithmic insight: *prompt specificity inversely correlates with required model capability*. A 4B-active model with a 200-line recipe outperforms a 4B-active model with a 30-line abstraction. Maps to behavioural cloning's "detailed action sequence" framing.
- **Staged-verification confidence (50 → 75 → 95%) as the algorithmic story.** Camera detection at 50%, Go2 scout's `video_reasoning` at 75%, X2 announcer's casualty check at 95%. Each tier is a different robot's evidence; the staged trace makes the prior, the likelihood, and the posterior all auditable. Generic template for any future incident type — tier 1 = source signal, tier 2 = first-tier robot confirms visual, tier 3 = second-tier robot rules out human harm.
- **Parallel tool calls are the wall-clock lever.** Demo trace shows Claude batching 3 `get_action_schema`, then 3 `send_action`, then 3 `add_incident_action` + `update_incident_status`, then 3 `monitor_action_execution` — all in single turns. The 26-event trace is dominated by *thinking* time (~9 LLM calls × 5–13 s each), not tool-call time. Serialised, the demo would run 6–8 minutes; parallelised, 2m 9.4s. Gemma 4 can't batch tool calls (model-capability ceiling); Claude can. Engineering response: the demo runtime is Claude on Bedrock; Gemma stays available as the air-gapped fallback.
- **Vendor-agnostic action schemas validated under multi-robot orchestration.** The agent dispatches Unitree Go2, Agibot X2 Ultra, and RobotEra Q5 through *identical* Praxis action schemas — same `send_action(device_id, action_name, payload)`, same `monitor_action_execution(task_id)`, same response shape. Three vendors, three on-robot SDKs (Unitree SDK / AIMDK / XOS), three locomotion API models (continuous odom / streaming velocity with arbitration / FSM-gated TwistStamped), one platform-level API surface. The integration work from weeks 3–5 paid off in this single demo.

### Impact
- **Live multi-robot incident-response demo greenlit for the Impact event.** The story leadership can tell: warehouse incident detected by a fixed camera → natural-language command to the agent → three robots coordinate response with audited confidence escalation → casualties verified absent → first aid positioned, all in 2m 9.4s. The pitch writes itself.
- **The agentic-layer dependency is now self-hosted.** Praxis no longer requires an internet connection for the live runtime to function — the same `impact_agent` works against locally-served Gemma 26B via LiteLLM's provider-string swap. Cost predictability (no per-token billing during repeated rehearsals) + reliability (no internet dependency during the Boss demo or the Impact event) + data residency (prompts and completions never leave the host).
- **Recipe-style prompt is now a transferable artefact.** Any team building an LLM-driven robotic workflow can lift the same shape: fixed role assignment block, literal payload JSON, "in this exact order" sequencing, mandatory post-action update chains, narration discipline, fixed-template final report. The behavioural-cloning-via-prompt pattern is reusable.
- **Provider-agnostic LiteLLM + vendor-agnostic Praxis SDK = composable abstractions.** Model switch is a config-line change in `config.json`. Robot switch is a `device_id` change in the payload. The agent code is invariant across both axes. The composition: vendor-neutral robots × vendor-neutral models = workflow-neutral incident responses.
- **vLLM runbook and failure-modes documentation** are now the institutional memory for every Blackwell-host bring-up that comes after. The next engineer onboarding a Blackwell box gets the `LD_LIBRARY_PATH` fix, the image pinning rationale, the `MAX_MODEL_LEN` / `GPU_MEMORY_UTILIZATION` sizing rules, and the `/health` polling discipline — without having to rediscover any of them.

### Academic Connections
- **Operating systems / virtual memory.** PagedAttention as direct application of OS-style paging to KV cache — page tables, lazy block allocation, copy-on-write for prompt prefix reuse. Continuous batching as token-level preemption analogous to tick-driven scheduler preemption.
- **Computer architecture.** GPU memory hierarchy and the bf16-weights-vs-KV-cache trade-off; `GPU_MEMORY_UTILIZATION` as a soft VRAM cap; tensor-parallel scaling vs single-GPU latency penalty.
- **Systems / linker semantics.** `LD_LIBRARY_PATH` resolution order, library shadowing, dynamic-linker priority — the Blackwell fix is a textbook ld.so problem.
- **AI agents / orchestration.** Recipe-style prompts as behavioural-cloning at the prompt layer; same-turn vs sequential tool-call enforcement; parallel tool calls as agent-layer fork-join concurrency; staged-verification as multi-sensor Bayesian update with auditable evidence attribution.
- **Distributed systems.** OpenAI-compatible REST as vendor-neutral interface contract; LiteLLM as provider abstraction at the model boundary; Praxis SDK as vendor abstraction at the robot boundary; their composition as a workflow-neutral substrate.
- **Decision theory / Bayesian reasoning.** Staged-verification confidence (50 → 75 → 95%) as literal Bayesian update with multi-sensor, multi-vendor likelihood composition.
- **Software engineering.** Image pinning + bind-mounted state + pre-flight verification as a hygiene pattern for stateful workloads in stateless containers; failure-modes taxonomy as forcing-function documentation; hot-reload via volume mount as iteration-loop optimisation.

## Source dailies

[[22-06-26]] · [[23-06-26]] · [[24-06-26]] · [[25-06-26]] · [[26-06-26]]

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
