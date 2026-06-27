---
aliases:
  - 25-06-26
  - 2026-06-25
---

# Daily

## June 25, 2026

**Graph Nodes:** [[Praxis Platform]], [[Praxis Agents]], [[Unitree Go2]], [[Agibot X2 Ultra]], [[RobotEra Q5]] · #GoogleADK #Gemma #AWSBedrock #ToolCalling #IncidentResponse #VendorAbstraction

**Theme:** [[Robotics Integration Infrastructure]] (10 shared)

### Summary
Spent the day hardening the `impact_agent` prompt and the integration plumbing against the model failures the agent kept hitting. Three classes of bug: (i) the X2 was navigating to the wrong location, (ii) Gemma was serialising tool calls one-at-a-time vs Claude batching them in parallel, (iii) role assignment was occasionally swapping. By end of day the recipe-style prompt is locked, narration discipline is enforced, and the agent runs a clean 8-phase trace on Claude. Gemma still has the parallel-tool-calls ceiling but the playbook is correct.

### Shipped
- **X2 destination fix in the prompt** — earlier prompt sent the announcer to the demo hall (a generic fallback), now it explicitly sends X2 to the *same location as the scout*. Same pose, same floor plan, same incident anchor. Removed the "demo hall" string entirely so the model can't fall back to it
- **Mandatory parallel-call hint for Claude** — prompt now lists the parallel-call opportunities explicitly: "in the same turn, call `get_action_schema` × 3 for navigate / TTS / motion_replay", "in the same turn, call `send_action` × 3 to dispatch all three robots", "in the same turn, monitor all three actions". Claude takes the hint and batches; Gemma still serialises but at least doesn't drop the calls
- **Role-assignment hardening** — prompt now opens with a "ROBOT ROLES (DO NOT REASSIGN)" block: `unitree-go2 = SCOUT — first dispatch always`, `agibot-x2-ultra = ANNOUNCER — second dispatch, with TTS`, `robotera-q5 = INTERVENER — grabaid + first-aid navigation`. Removed any language inviting the model to "select the appropriate robot"
- **Narration discipline** — exactly two narration moments now enforced by example: (a) on Go2 arrival: "*unitree-go2* has arrived at *location*. Capturing visual now.", (b) on casualty detection or absence: "CASUALTY DETECTED — escalating." or "Area clear — no casualties." Narration never ends a turn; bad-vs-good examples are inline in the prompt
- **`video_reasoning` retry** — prompt now says: on error, retry once; on second failure, post `add_incident_update("video_reasoning unavailable — manual review required")` and continue the playbook rather than abandoning the incident
- **Final report template** baked into the prompt — fixed Markdown shape with incident ID, status, confidence, dispatch log table, TTS announcement text, visual verification results, casualty check. The agent emits this verbatim at end of playbook, so the output is auditable in a fixed schema rather than free-form prose

### Technical Highlights
- **Parallel tool calls are the dominant throughput lever on Claude.** Trace analysis shows Claude batching 3–5 tool calls per turn: `update_incident` + `list_schema_aliases` + `get_action_schema × 3` in the very first turn, then `update_incident` + `send_action × 3` to dispatch all three robots simultaneously, then `add_incident_action × 3 + update_incident_status` to record the dispatches. The 26-event end-to-end trace is dominated by *thinking* time, not tool-call time — 9 LLM calls of 5–13 s each, with each call doing batched tool work in parallel. Total: ~2 min for an incident that, if serialised, would take 6–8 min.
- **Gemma 4 can't batch tool calls.** Same prompt, same scenario: Gemma issues tool calls strictly one-per-turn. Not a prompting issue — model-capability ceiling. Sequential calls roughly 3× the wall-clock for the same incident on the same hardware. The pragmatic resolution: prompt is identical (still encourages batching), but expected runtime differs per model. Demo defaults to Claude on Bedrock for the live runtime, Gemma stays available as a fallback / air-gapped path.
- **The "X2 goes to demo hall" bug was a prompt-leak failure.** Earlier prompt had an example where the announcer demonstrated TTS from a demo location. Model latched onto "demo hall" as the X2's *destination* despite the example being about TTS content. Fix is mechanical (delete the string) but the lesson is general: prompt examples leak into model behaviour at runtime, especially with smaller models. Examples should be sanitised of any operationally-meaningful strings the model could mistake for instructions.
- **Vendor-agnostic schemas validated in anger.** The agent dispatches Go2 (`navigate_to_pose`), X2 (`navigate_to_pose` + `set_volume` + `play_tts`), and Q5 (`motion_replay grabaid9` + `navigate_to_pose`) through *identical* Praxis action schemas. The agent's code path doesn't branch on robot vendor — same `send_action(device_id, action_name, payload)`, same `monitor_action_execution(task_id)`, same response shape. This is the validation moment for the SDK design work from weeks 3–5: the abstraction holds under multi-robot orchestration.
- **Same-turn enforcement vs sequential enforcement.** Earlier prompt said "after `video_reasoning`, update the incident." Model interpreted this as "eventually." Replacing with "in the SAME TURN as `video_reasoning`, call X then Y then Z" turned a 70 %-reliable behaviour into a 100 %-reliable one. The model honours *same-turn* sequencing because each tool call inside a turn is a structured emission, not a planning decision. Single most leveraged prompt change of the day.
- **Tool-call latency observations.** Per-call wall clock from the trace: `update_incident` ~500–800 ms, `get_action_schema` ~800 ms, `send_action` ~2.1–2.8 s, `monitor_action_execution` ~800 ms–1.1 s, `capture_image` ~4.3–4.4 s, `video_reasoning` ~4.3–8.4 s. The vision calls dominate; everything else is sub-3-second. Consolidation candidate: `list_camera_info + capture_image + video_reasoning` → one "see what's in front of me" tool would shave ~6 s per scout / announcer turn. Logged for the server-side tool-consolidation work next sprint.

### Impact
- 8-phase end-to-end scenario now runs cleanly on Claude with the hardened prompt. Trace shape: incident creation (50 %) → parallel dispatch (Go2 + X2 + Q5 simultaneously) → Go2 visual reasoning (75 %) → X2 TTS + casualty check (95 %) → Q5 grabaid + first-aid navigation → final report. Ready for the Boss demo tomorrow.
- Prompt is now a *contract* between the model and the playbook, not a suggestion. Every robot-role swap, every missed update, every wrong destination is a prompt regression we can diff against the current version. Iteration is now reliable.
- Confidence staging (50 → 75 → 95) is the algorithmic story the demo tells: "look how the system *earns* its confidence from each new sensor's evidence." It's also the story leadership will repeat back when describing what the agent does.
- Gemma's ceiling (no parallel tool calls + harmony-format token leaks) now has a clear engineering plan: server-side tool consolidation collapses 3 calls into 1 where it matters; the harmony-format leak gets a server-side chat-template fix; both are tracked. The demo doesn't depend on either landing — Claude handles the live runtime — but the local-LLM path stays viable for the air-gapped case.

### Academic Connections
- **AI agents / orchestration.** Same-turn vs sequential tool-call enforcement maps to immediate-vs-deferred action semantics in robotic task planning. The model handles immediate sequencing reliably because each step is mechanical; deferred sequencing requires planning over state the model doesn't always re-evaluate. Lesson generalises to any LLM-driven workflow.
- **Software engineering.** Prompt-as-contract: every behavioural requirement becomes a prompt clause; every regression is a failing clause; iteration is diff-able. Same discipline as test-driven development applied to LLM behaviour.
- **Distributed systems.** Parallel-vs-sequential tool calls is the agent-layer analogue to pipelined-vs-serialised RPC. The throughput win is identical: 3× wall-clock improvement for batch-able work. Maps directly to gRPC streaming and HTTP/2 multiplexing.
- **Decision theory.** Staged-verification confidence (50 → 75 → 95) as Bayesian update with vendor-diverse evidence sources. The robot-layer abstraction makes the *evidence* fungible — Go2's camera and X2's camera contribute identically to the posterior — while preserving the *order* in which they arrive at the agent.
- **Human-factors / narration.** Narration discipline as a constraint on agent loquacity. Two narration moments, both at high-information points (arrival, casualty detection). Everything else is silent tool calls. This is the difference between an agent that *narrates its own debugging* and one that *reports its findings* — operationally significant when leadership is watching.

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
