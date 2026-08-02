---
aliases:
  - Weekly_W8
---

# Weekly

## July 10, 2026

**Graph Nodes:** [[Praxis Platform]], [[Praxis Agents]], [[CommanderAI]], [[Unitree Go2]], [[Agibot X2 Ultra]], [[RobotEra Q5]], [[NCS Impact 2026]], [[TP-Link Omada]] · #vLLM #Gemma #MQTT #RTSP #Docker #systemd #IncidentResponse #StagedVerification #RecipestylePrompt #VendorAbstraction

### Summary
The NCS Impact week — from final integration sprint (Monday) through the three-day public demonstration at MBS Level 5 (Tue–Thu), followed by a day off (Fri). Monday delivered NovaSonic speech-to-speech on the Q5, event logistics, and a partial Fast Whisper integration on the spare X2. Setup day (Tue) was defined by a DFS-channel network block that consumed most of the afternoon, a late-night prompt session adding robot speech to the incident-response scenario, and the realisation that intelligible agentic AI requires a communication design layer, not just an orchestration layer. Days 1 and 2 of the event (Wed–Thu) ran multiple successful demos for NCS internal staff and C-suite/executive audiences, with zero failures on the main demo day. The conversational X2 was the most-remarked element by non-technical attendees. Eight weeks of integration work publicly validated.

### Shipped
- **NovaSonic speech-to-speech on Q5** — extended with NCS event knowledge base, Singapore LTA + OneMap API integration, event-appropriate prompt context. Full spoken conversation with the Q5 working at ~3–5 s round-trip latency. Latency is a vLLM-inference bottleneck, not an ASR or TTS bottleneck.
- **Fast Whisper speech recognition on spare X2** — started Monday, completed Wednesday. Full pipeline: microphone → Fast Whisper ASR → NovaSonic/Gemma LLM → TTS → X2 speaker. Conversational robot running continuously at the event from Day 1.
- **TP-Link Omada deployed at MBS** — enterprise APs live, DFS channels disabled after diagnosing a multi-hour connectivity blackout. All robots, server, and CCTV camera migrated to the new topology. X2's floating-IP problem permanently eliminated via MAC reservation at the venue.
- **Robot speech choreography added to the incident-response scenario** — Go2: siren + verbal incident confirmation; X2: crowd announcement TTS + casualty-check narration; Q5: verbal kit-retrieval confirmation and navigation announcement. Prompt v4 committed and deployed via hot-reload (`docker compose restart praxis-agents`) the same night.
- **CommanderAI presented publicly** — live robot status cards, video feeds, natural-language command box routing through `impact_agent`. Served as the single-page explanation of the entire integration stack for non-technical audiences.
- **Multiple fallen-boxes scenario runs** — all successful across Day 1 (internal NCS) and Day 2 (C-suite / external executives / professors). Confidence trace 50→75→95 visible in real time on the dashboard.
- **"Keep robots on all day" operational rule** — established after first-morning reconnection delays. Robots stay powered and charging continuously; Wi-Fi associations, MQTT connections, and RTSP streams all remain live. Zero cold-start failures for the rest of the event.

### Technical Highlights
- **DFS (802.11h) as a venue deployment footgun.** APs showed as connected in the Omada controller but passed zero traffic. Root cause: DFS channels require radar-scan windows before transmitting; in the MBS venue environment, scans fired repeatedly and kept channels silent for 60-second intervals. One Omada config change (DFS channels: off) resolved hours of blocked connectivity immediately. Lesson: venue deployments must pre-validate DFS settings; "connected" in the controller ≠ "traffic flowing."
- **Robot speech as a narrative UX layer, not a feature.** The underlying agentic loop was unchanged — same Praxis actions, same `impact_agent`, same MQTT/RTSP plumbing. Adding speech (Go2 siren + confirmation, X2–Q5 verbal exchange) made the scenario intelligible to any audience. The boss's boss's feedback ("it feels like nothing") before the speech additions and the C-suite engagement after them is the empirical proof: invisible reasoning is architecturally correct and experientially inert. Designing for interpretability is as important as designing for capability.
- **Synthetic multi-robot dialogue via sequenced TTS actions.** X2's "I need you to retrieve the first-aid kit" and Q5's "Understood, retrieving now" are two separate `tts` actions issued sequentially by `impact_agent` — not actual inter-robot communication. From the audience perspective they read as robot-to-robot coordination. Designed demo experience > literal technical accuracy when communicating to non-engineers.
- **Fast Whisper + NovaSonic + Gemma 26B as a live conversational stack.** Pipeline latency: ASR ~500 ms (Fast Whisper, negligible), LLM inference 1–3 s (Gemma 26B on vLLM, bottleneck), TTS ~300 ms. Total ~4–6 s — at the edge of conversational comfort but acceptable for a standing demo where the audience expects the robot to "think." External API calls (LTA, OneMap) add <200 ms on the venue's LAN.
- **Staged confidence (50→75→95) as the C-suite communication tool.** The most common executive question was "how does it know when to escalate?" The dashboard's confidence trace, lit up in real time as each robot reported back, answered the question visually without any explanation. A technical design choice (multi-sensor Bayesian evidence accumulation) became the demo's clearest communication artifact.
- **"Robots stay on" as an architectural insight.** Robots are not laptops — they maintain network state (Wi-Fi association, MQTT session, RTSP stream) as long as they remain powered. Rebooting is a destructive operation in a live-event context: it tears down multiple protocol sessions simultaneously, each with its own reconnect latency. The operational rule ("charge, don't power off") is the event-deployment analogue of the infrastructure principle "prefer graceful restarts over hard reboots."

### Impact
- **NCS Impact 2026 delivered without demo failures.** Four robots, one CCTV camera, two LLM inference pipelines (vLLM Gemma 26B for `impact_agent` + NovaSonic dialogue), one Praxis platform. Public demonstration to Singapore's technology leadership, C-suite, professors, and company representatives.
- **Conversational X2 was the most democratising element.** The incident-response scenario impressed engineers; the talking X2 impressed everyone. Queues of 3–5 people throughout both event days. Multiple executive and professor follow-up questions specifically about the speech-interaction capability. Data point: accessible AI interfaces matter as much as capable ones for broad adoption.
- **The three-part pitch validated empirically.** Agentic orchestration (robots respond to one command), physical reasoning (vision AI confirms the scene), conversational interaction (people talk to the robots) — demonstrated simultaneously on one floor. The combination is the argument; no individual piece makes it.
- **All eight weeks of integration work survived a live public demonstration.** The vendor-agnostic driver architecture (four robots, three locomotion API models, one Praxis schema), the `impact_agent` recipe-style prompt, the TP-Link Omada network, the vLLM local inference, and the NovaSonic speech layer all held under event conditions.

### Academic Connections
- **Networking / RF.** DFS (802.11h) channel management; enterprise AP deployment in high-density RF environments; Wi-Fi association state persistence as an operational reliability mechanism; MAC-reservation-based static IP assignment.
- **AI agents / orchestration.** Recipe-style prompts for Gemma under demo conditions; same-turn TTS sequencing for synthetic multi-robot dialogue; staged-verification confidence as both a correctness mechanism and a communication tool; local LLM as a no-internet-dependency reliability primitive.
- **AI / NLP.** Fast Whisper as an optimised ASR layer; speech-to-speech pipeline latency decomposition (ASR / LLM inference / TTS); knowledge-base injection + external API grounding for conversational robots; vLLM inference throughput as the bottleneck at conversational latency targets.
- **Human-factors / demo design.** Interpretability as a design requirement: invisible reasoning is experientially inert regardless of architectural sophistication; verbal cues + confidence traces + UI as the communication layer over the technical layer; accessible conversational interfaces vs impressive technical demonstrations for different audience segments.
- **Software architecture.** Facade pattern (CommanderAI hides a distributed system behind a command box); hot-reload via volume mount enabling same-night prompt deployment; the compounding value of vendor-agnostic abstractions made visible in a single public demo surface.

## Source dailies

[[NovaSonic speech-to-speech and event prep]] · [[NCS Impact setup day and late night prompt work]] · [[NCS Impact day 1 and X2 speech fixed]] · [[NCS Impact day 2 C-suite demos and pack-out]]

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
