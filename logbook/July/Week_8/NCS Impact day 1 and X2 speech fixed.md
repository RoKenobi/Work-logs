---
date: 2026-07-08
---

# Daily

## July 08, 2026

**Graph Nodes:** [[Praxis Platform]], [[Praxis Agents]], [[Unitree Go2]], [[Agibot X2 Ultra]], [[RobotEra Q5]] · #vLLM #Gemma #MQTT #RTSP #IncidentResponse

**Theme:** [[Robotics Integration Infrastructure]]

### Summary
Day 1 of NCS Impact 2026 — internal NCS staff visiting the demo floor. Ran multiple smooth end-to-end fallen-boxes scenarios throughout the day with no major failures. Discovered and locked in the "keep robots powered on and charging continuously" operational rule — powering off caused Wi-Fi reconnection delays that broke the demo. Also successfully fixed the Fast Whisper speech-recognition pipeline on the spare X2, which had been left 70% done from Sunday. By end of day all robots were speaking, all demos were running, and the X2's conversational mode was attracting a consistent crowd.

### Shipped
- **"Keep robots on all day" operational rule established.** Powering off robots between demos caused them to lose their Wi-Fi association; reconnection took several minutes and in some cases required manual intervention. Solution: keep all robots powered on and connected to chargers throughout the event day. The robots maintain their Wi-Fi association indefinitely when on; the chargers prevent battery drain. This is now a hard rule for all future events.
- **Fast Whisper speech recognition on spare X2 — fixed and working.** Completed the pipeline started on Sunday: Fast Whisper model loads, receives audio from X2's microphone, transcribes speech, routes to the NovaSonic / LLM dialogue system. People can walk up to the X2, ask a question verbally, and receive a spoken response. End-to-end latency acceptable for a standing demo (~4–6 s round trip including inference).
- **Multiple smooth fallen-boxes demos run** throughout day 1 — internal NCS staff seeing the full agentic sequence: CCTV trigger → Go2 scout (verbal + siren) → X2 arrive + announce → Q5 grabaid + navigation → incident resolved. No major failures across all runs.
- **Crowd interaction with X2** — the speech-enabled X2 became a persistent draw throughout the day. Multiple groups queuing to ask it questions, talk about the technology, ask about Singapore. The conversational mode ran independently of the incident-response scenario, allowing the team to demonstrate both capabilities simultaneously.

### Technical Highlights
- **Wi-Fi association persistence is a state that must be actively maintained.** Robots associate with the Omada APs at boot and maintain the association through a keepalive mechanism. When powered off, the association is torn down. On power-on, reconnection requires: DHCP lease renewal, MQTT reconnect to VerneMQ, Praxis client re-registration, RTSP stream re-establishment. Under normal conditions this takes 30–60 s. In a venue with multiple APs and potentially elevated RF traffic, it can take longer or require a manual `praxis_start` cycle. Keeping the robots on eliminates this cold-start path entirely — they stay associated, all connections stay live, the demo can fire in seconds.
- **Fast Whisper as the ASR layer.** Fast Whisper is a reimplementation of OpenAI's Whisper model optimised for inference speed — significantly faster than the original Whisper at the same quality tier. On the X2's compute, it transcribes a typical spoken question (~10 words) in under 500 ms, which is fast enough not to dominate the pipeline latency. The bottleneck remains the LLM inference step (vLLM Gemma 26B, 1–3 s). The full pipeline: microphone → Fast Whisper ASR → NovaSonic/Gemma LLM → TTS → X2 speaker.
- **Two concurrent demo modes on the same floor.** The fallen-boxes scenario runs through `impact_agent` on the Praxis platform. The X2 conversational mode runs through the NovaSonic/Fast Whisper pipeline independently. Both use the same X2 hardware but different software stacks; they don't conflict because they're triggered by different inputs (a Praxis action for the scenario, a microphone input for conversation). This is the demo floor's version of the multi-source arbitration pattern — two input sources, one robot, priority assigned by context.
- **Human interaction dynamics at a tech event.** People engage with robots they can talk to far more than robots that just move. The conversational X2 attracted clusters of 3–5 people who would queue informally to ask it questions, then share what it said with others nearby. The incident-response scenario was impressive to engineers; the talking X2 was impressive to everyone. This is a useful design signal: interactivity beats performance for general audiences.

### Impact
- Day 1 passed with no demo failures. Internal NCS staff engaged positively with both the agentic incident response and the conversational X2.
- Operational rule ("robots stay on all day") documented and applied immediately — zero disconnection issues for the rest of the event.
- Fast Whisper X2 now running: the team's booth has both a scenario demo and a conversational robot, covering two distinct audience engagement modes simultaneously.
- X2's conversational draw was qualitatively the most impactful element for non-technical visitors — a tangible signal for how to design future events.

### Academic Connections
- **Networking / embedded systems.** Wi-Fi association state machine; cold-start latency under DHCP + MQTT + RTSP reconnection; "keep alive" as a reliability strategy over "reconnect on demand" for event deployments.
- **AI / NLP.** Fast Whisper as an optimised Whisper variant; ASR + LLM + TTS pipeline latency decomposition; the bottleneck identification (LLM inference dominates, ASR does not).
- **Human-factors.** Audience engagement as a function of interactivity level; the qualitative difference between observing a demonstration and participating in a conversation; designing demo floors for two distinct engagement modes (technical showcase vs interactive experience).
- **Concurrency / multi-mode systems.** Two concurrent input-driven modes on a single robot platform; conflict avoidance through input-type separation rather than shared state arbitration.

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
