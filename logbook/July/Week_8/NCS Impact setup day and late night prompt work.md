---
date: 2026-07-07
---

# Daily

## July 07, 2026

**Graph Nodes:** [[Praxis Platform]], [[Praxis Agents]], [[Unitree Go2]], [[Agibot X2 Ultra]], [[RobotEra Q5]], [[TP-Link Omada]] · #vLLM #Gemma #MQTT #RTSP #IncidentResponse #RecipestylePrompt

**Theme:** [[Robotics Integration Infrastructure]]

### Summary
Setup day at NCS Impact 2026, MBS Level 5 indoor auditoriums. Unloaded and deployed the full fleet. Hit a major network wall that consumed most of the afternoon — venue Wi-Fi was completely silent for the robots for hours before a single config flag (`DFS channels: disabled`) on the TP-Link controller fixed it instantly. Once the network was live the demo came up clean. Then a late-night session with Joe and the boss's boss running until 10pm: added robot speech throughout the incident-response scenario — Go2 with a siren and verbal confirmation, X2 and Q5 speaking to each other and to the crowd — to make the agentic loop intelligible and human-feeling for a non-technical C-suite audience.

### Shipped
- **Full fleet deployed at MBS Level 5** — four robots, server, TP-Link Omada hardware, CCTV camera, all wiring run and connected. The demo floor is live.
- **DFS channel disable — the network fix.** TP-Link Omada enterprise APs have Dynamic Frequency Selection (DFS) channels enabled by default in some configurations. DFS channels require radar-detection scans before transmitting; in a venue environment these scans blocked channels for extended periods (minutes to hours). Once DFS was disabled on the Omada controller, the APs immediately came up on clean non-DFS channels and all robots connected within minutes.
- **Robot speech added to the incident-response scenario overnight:**
  - Go2: verbal confirmation on scene arrival ("Incident confirmed, fallen boxes detected") + emergency siren sound played from its back speaker during investigation
  - X2: TTS announcement to crowd ("Emergency. Please give way to emergency response.") + verbal exchange with Q5 ("I need you to retrieve the first aid kit from the first aid station")
  - Q5: verbal response to X2 ("Understood. Retrieving first aid kit now.") + confirmation on arrival ("First aid kit retrieved. Proceeding to incident location.")
- **Prompt v4 committed** — updated `impact_agent` prompt to include the robot-speech choreography; Q5 `motion_replay` sequencing fixed to always trigger `grabaid9` before navigating; narration discipline tightened for the new speech turns.

### Technical Highlights
- **DFS channels as a venue deployment footgun.** DFS (802.11h) is a regulatory requirement in many countries — APs must listen for radar signals before transmitting on certain 5 GHz channels, and must vacate immediately if radar is detected. In a convention centre with complex RF environments (radar from nearby systems? other APs?) DFS detection can fire repeatedly, keeping APs silent for 60-second scan windows. The symptom — APs visible in the Omada controller as "connected" but no traffic flowing to robots — is exactly what we saw. Disabling DFS forces the APs onto non-DFS channels permanently; the trade-off is fewer available channels, but in a venue where you control all the APs this is the right call.
- **Robot speech as a narrative UX layer over the agentic workflow.** Without speech, the demo looks like this to a CEO: robots move around a room for 2 minutes and then stop. With speech it looks like: a robot arrives at the scene and announces what it found; a second robot coordinates verbally with a third to retrieve first aid. The underlying agentic loop is identical — same Praxis actions, same `impact_agent` prompt, same MQTT/RTSP plumbing. The speech is a thin narrative layer on top. The insight is that intelligibility for a non-technical audience is not a feature of the technology — it's a feature of the communication design.
- **X2–Q5 verbal coordination as synthetic multi-robot dialogue.** The exchange ("I need you to retrieve the first aid kit" / "Understood, retrieving now") isn't actual robot-to-robot communication. Both speech events are triggered by the `impact_agent` in sequence as separate `tts` actions — the agent issues X2's TTS, then issues Q5's TTS. From the audience's perspective it sounds like the robots are talking to each other. This is deliberate demo design: the illusion of coordination is as valuable as actual coordination for a demonstration setting.
- **The value of a late-night creative session.** The speech additions transformed the demo. But this kind of work — writing robot dialogue, choreographing timing, testing how it reads to a non-technical observer — only happens when the people in the room have both the technical ability (to modify the prompt and deploy instantly) and the creative instinct (to know when something feels human vs mechanical). Staying until 10pm was the right call.

### Impact
- Network is live, demo is live, speech is live. The setup day ended with a full end-to-end rehearsal run of the fallen-boxes scenario with all speech elements in place.
- The demo is now intelligible to any audience — technical or not. The added speech turns the 6-minute incident response from a confusing robot dance into a recognisable emergency-response narrative.
- Go2's siren + verbal confirmation, X2's crowd announcement, Q5's kit retrieval confirmation — each robot now has a voice that matches its role in the scenario. Small detail, enormous impact on audience comprehension.

### Academic Connections
- **Networking.** DFS (802.11h) regulatory mechanism and its operational cost in venue deployments; channel plan management in enterprise SDN deployments; the asymmetry between "controller shows connected" and "traffic actually flows."
- **Human-factors / UX.** Intelligibility as a design property of demonstrations: the same underlying system reads completely differently with vs without narration. Designed for the audience, not the engineers. Parallels to the "narration discipline" principle in the `impact_agent` prompt — same concept, different scale.
- **AI agents / multi-robot.** TTS actions as a narrative-layer primitive on top of a task-execution loop; synthetic multi-robot dialogue via sequenced `tts` calls from a single orchestrating agent; prompt additions for speech choreography as an extension of the recipe-style prompt pattern.
- **Software engineering.** Same-night prompt iteration and deployment at a live event: the volume-mount hot-reload pattern (`docker compose restart praxis-agents`) enabling sub-2-minute turnaround on prompt changes. The deployment architecture paid off precisely when we needed it most.

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
