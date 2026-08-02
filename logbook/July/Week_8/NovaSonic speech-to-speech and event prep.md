---
date: 2026-07-06
---

# Daily

## July 06, 2026

**Graph Nodes:** [[RobotEra Q5]], [[Agibot X2 Ultra]], [[Praxis Platform]] · #Python #vLLM #HTTP #VendorAbstraction #IncidentResponse

**Theme:** [[Robotics Integration Infrastructure]]

### Summary
Morning brief from the boss: the Q5 and X2 need speech-to-speech interaction working before the event. NovaSonic — an existing speech-to-speech pipeline on the Q5 — was operational within hours by extending the existing code with an event-specific knowledge base (NCS context, Singapore LTA, OneMap APIs, basic SG info). People can now walk up and have a full spoken conversation with the Q5. Simultaneously tried to get Fast Whisper running on one of the spare X2 units but ran out of time before packing. The rest of the day was logistics: packing four robots, servers, chargers, cables, laptops, and all demo equipment for the NCS Impact 2026 event at MBS Level 5.

### Shipped
- **NovaSonic speech-to-speech on Q5 — production-ready for the event.** Extended the existing NovaSonic codebase already on the Q5 with: (1) an event-specific knowledge base (NCS Impact 2026 context, what the robots do, what Praxis is); (2) Singapore-specific APIs — LTA real-time data, OneMap geocoding, basic SG info — so the Q5 can answer questions about Singapore, the event, and the tech when people ask; (3) improved prompt context so responses feel appropriate for a public tech event rather than a dev terminal. Successfully tested: full spoken conversation with the Q5 with sub-3s round trips.
- **Fast Whisper on spare X2 — attempted, incomplete due to time.** Started getting the Fast Whisper speech-recognition model running on one of the four X2 units (specifically a spare, not the demo unit). Integration path confirmed, model loads, but the full pipeline wasn't validated before packing cut off the work. Will revisit at the event venue if time allows.
- **Full event pack completed** — all four robots (Go2, X2 ×4, Q5), server (`robotics-3gyc`), TP-Link Omada hardware, power adapters, charging cables, ethernet runs, two laptops, monitor, and all demo peripherals packed and staged for transport to MBS.

### Technical Highlights
- **NovaSonic as the speech surface on top of a complex agentic stack.** The Q5 is already connected to Praxis, already runs `impact_agent` for the incident scenario. NovaSonic adds a *conversational* layer on top: people can ask it questions about itself, the event, Singapore, and the integration — getting spoken answers. This is different from the agentic incident-response loop; it's a general-purpose dialogue interface, not a task executor.
- **Knowledge base + external APIs as the personalisation layer.** Vanilla NovaSonic would give generic answers. The extension injects: (a) structured event context (who is here, what the robots do, what the demo shows), (b) live SG data via LTA and OneMap APIs so the robot can give real-time answers to "where's the nearest MRT?" or "what's the traffic like on the AYE?". These are trivial API calls but they make the conversation feel grounded and locally relevant — the robot knows it's at MBS, not in a lab.
- **Latency is the real UX problem with speech-to-speech.** The pipeline is: microphone → ASR → LLM inference → TTS → speaker. Each stage adds latency; on the local vLLM Gemma 26B, the LLM inference step alone is 1–3 s for a conversational response. Total end-to-end is noticeable to a human conversation partner (~3–5 s). Acceptable for a standing demo where people expect the robot to "think"; would not be acceptable for a voice assistant. The bottleneck is vLLM inference throughput on Gemma 26B — a smaller model or a streaming-decode path would close the gap.
- **Four X2 units creates a testing surface question.** The team has four Agibot X2 Ultras; the demo uses one. The spare units exist as fallback hardware and as a development sandbox. Keeping the dev work on a spare unit (not the demo unit) is the right practice — a bad speech integration on the demo unit the night before the event would be a disaster.

### Impact
- Q5 is conversational for the event — visitors can talk to it about the demo, the technology, Singapore, and the event. This is the non-technical hook: robots that answer your questions are approachable; robots that just move are intimidating.
- Event logistics complete. The entire fleet is packed and ready for the 7:00 AM transport to MBS.
- Fast Whisper on X2 is 70% done — will attempt to close it out at the venue during setup day.

### Academic Connections
- **AI / NLP.** Speech-to-speech pipeline: ASR → LLM → TTS as three independently-replaceable components; knowledge injection as RAG-lite (structured context in the system prompt); latency decomposition per pipeline stage; the trade-off between model size and inference latency for real-time dialogue.
- **Distributed systems.** External API integration (LTA, OneMap) in an LLM system prompt as a live-data grounding mechanism; the resilience question of API dependencies during a public event (rate limits, auth failures in a crowded venue).
- **Software engineering.** Dev-vs-demo unit separation as a safety discipline; iterative knowledge base extension as a low-risk way to improve response quality without touching the core pipeline.
- **Human-factors.** Latency tolerance in human-robot conversation: 3–5 s is the edge of acceptable for a standing demo; beyond that the conversation feels broken. Designing the robot's physical behaviour (LED animation, subtle movement) during inference to signal "thinking" rather than "broken."

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
