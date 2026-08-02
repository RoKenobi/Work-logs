---
date: 2026-07-02
---

# Daily

## July 02, 2026

**Graph Nodes:** [[Praxis Platform]], [[Praxis Agents]], [[Unitree Go2]], [[Agibot X2 Ultra]], [[RobotEra Q5]] · #vLLM #Gemma #GoogleADK #IncidentResponse #StagedVerification #RecipestylePrompt

**Theme:** [[Robotics Integration Infrastructure]]

### Summary
CEO consultation confirmed the final scenario shape and the local-LLM decision. Spent the bulk of the day refining the `impact_agent` prompt to make the fallen-boxes flow watertight under demo conditions — tightening sequencing, hardening against edge cases, and ensuring the local Gemma 26B handles the full playbook without the parallel-tool-call limitations causing visible breakage. The scenario is now locked: CCTV triggers, Go2 investigates, X2 announces, Q5 retrieves the first-aid kit.

### Shipped
- **Scenario locked post-CEO sign-off:**
  1. CCTV camera's VA detects fallen boxes → triggers an incident at 50% confidence
  2. Praxis `impact_agent` dispatches Go2 to the scene
  3. Go2 arrives, captures image, sends for video analysis → confidence escalates to 75%
  4. Agibot X2 dispatched, arrives with TTS: *"Please move away, keep clear of the area"*
  5. X2 camera captures casualty check → confidence escalates to 95%
  6. RobotEra Q5 performs `grabaid` motion, retrieves first-aid kit, navigates to scene
  7. Incident marked resolved via CommanderAI / Praxis dashboard
- **Local LLM decision confirmed** — CEO backed the vLLM-served Gemma 26B path specifically because internet-dependent Bedrock would be unreliable in the NCS event venue. The tradeoff (slower, no parallel tool calls) is acceptable given the no-internet-dependency requirement.
- **Prompt hardened for Gemma limitations:**
  - X2 arrival-before-Go2 race condition fixed: explicit ordering gate ("do not dispatch X2 until Go2 `video_reasoning` has completed and confidence has been updated")
  - Retry path for `video_reasoning` failures made more explicit — retry once, then post manual-review update and continue rather than halt
  - Narration reduced to exactly two moments (Go2 arrival + X2 announce) — fewer agent decisions under Gemma's weaker reasoning capacity
  - Timeout and fallback paths explicitly named in the prompt body so Gemma doesn't invent them

### Technical Highlights
- **The CCTV-triggered-incident flow is a new agentic capability.** Previous demos were manually triggered from the ADK web UI. The final scenario starts with the CCTV camera's VA (running on the local vLLM or a vision-capable endpoint) detecting the fallen-boxes incident and posting directly to the Praxis incident API — no human in the loop until the robots are already moving. This is the difference between "a demo" and "an autonomous incident-response system."
- **Local LLM as an architectural constraint shapes the whole prompt design.** Gemma 26B can follow a recipe but can't plan. So the prompt is a recipe. Every step is numbered and explicit; the model is never asked to reason about ordering — the order is given. The tradeoff is that the prompt is longer and more brittle to new scenarios, but it's robust on the one scenario we're demoing. Recipe-style for correctness, not abstraction for flexibility.
- **Two-tier confidence escalation as the CEO's soundbite.** The CEO specifically highlighted the staged verification as the narrative hook: "the system doesn't just react, it *builds confidence* before escalating." 50% → 75% (Go2 visual confirmation) → 95% (X2 casualty clear) maps onto how a real emergency protocol would work — first responder scouts, second responder confirms, intervention only when confident. That framing is what gets remembered.
- **Gemma vs Claude on this scenario.** Claude batches 3 tool calls per turn and completes the scenario in ~2 min. Gemma serialises them and takes ~6 min. For the demo we're running on Gemma (no internet dependency), so the visible latency is a design constraint we work around with narration: the TTS announcements from X2 fill the silence while the agent is polling. The demo is *designed* to feel deliberate, not slow.

### Impact
- Scenario design is final and CEO-approved. No further changes to the fundamental flow.
- Local-LLM-first architecture is locked in for the event. Bedrock remains available as a fallback if the venue has stable internet, but the demo is designed to not need it.
- Prompt v3 is the cleanest it's been — Gemma handled the full 8-phase scenario end-to-end in testing today without any mis-sequencing or dropped steps.
- CommanderAI's scenario trigger panel updated to reflect the CCTV-triggered start (no manual "fallen boxes" button needed — the CCTV VA fires it automatically).

### Academic Connections
- **AI agents / orchestration.** Fully agentic incident-response: from sensor trigger → multi-robot dispatch → confidence escalation → physical intervention, with no human in the loop. Recipe-style prompts as a correctness guarantee for weaker models; narration discipline to fill agent-latency gaps in a live demo.
- **Decision theory / Bayesian reasoning.** Staged confidence (50 → 75 → 95) as an auditable evidence chain; the CEO framing of "builds confidence before escalating" maps exactly onto the Bayesian update structure of multi-sensor evidence accumulation.
- **Human-factors / demo design.** Designing the demo so that model latency (Gemma's 6-min wall clock) reads as *deliberate staged response* rather than slowness — using TTS announcements, robot movement, and visual confidence updates to keep observers engaged during inference pauses.
- **Systems engineering.** No-internet-dependency as a hard requirement that reshapes the architecture (local vLLM over Bedrock); CEO sign-off as a forcing function for scope lock, preventing last-minute scenario changes that would destabilize the tested prompt.

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
