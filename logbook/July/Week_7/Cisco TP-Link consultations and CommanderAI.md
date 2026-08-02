---
date: 2026-07-01
---

# Daily

## July 01, 2026

**Graph Nodes:** [[Praxis Platform]], [[Praxis Agents]], [[Unitree Go2]], [[Agibot X2 Ultra]], [[RobotEra Q5]] · #vLLM #Docker #HTTP #IncidentResponse #VendorAbstraction

**Theme:** [[Robotics Integration Infrastructure]]

### Summary
Two parallel tracks ran simultaneously: back-to-back vendor consultations with Cisco and TP-Link to brief their engineers on the network upgrade requirements, and active development work on CommanderAI — the demo showcase webpage — plus prompt iteration on the fallen-boxes incident-response scenario. Described our topology, robot fleet, bandwidth requirements, and event constraints to both vendors; got technical proposals back. CommanderAI took shape as the public-facing demonstration surface for everything the fleet can do.

### Shipped
- **Cisco consultation** — briefed Cisco engineers and directors on the demo floor topology, robot count (4 robots + CCTV + server), per-robot bandwidth requirements (RTSP ~4 Mbit/s, MQTT ~50 kB/s per robot, SSH control), expected crowd size, and event duration. Cisco's proposal centered on Meraki APs with cloud-managed channel coordination.
- **TP-Link Omada consultation** — parallel session with TP-Link technicians covering identical requirements. TP-Link proposal centered on Omada SDN hardware — dedicated EAPs (enterprise access points) per robot zone, managed via an on-premises Omada controller on the server. Hardware is available for same-day procurement.
- **CommanderAI demo page** — started building the showcase webpage that lets leadership and event attendees see all robotic integrations in one place: live robot status (via Praxis API), a video feed panel, a natural-language command interface routing through `impact_agent`, and a scenario trigger panel (fallen-boxes, bag detection, etc.). The page is the *narrative wrapper* around the Praxis platform for the non-technical audience.
- **Fallen-boxes scenario tightened** — improved prompt clarity on `impact_agent` for the demo flow: Go2 → image capture + VA → confidence boost → X2 arrive + TTS announcement → Q5 grabaid + first-aid navigation. Addressed an edge case where X2 was reaching the scene before Go2 had reported back.

### Technical Highlights
- **TP-Link Omada vs Cisco Meraki — the key tradeoff.** Meraki is cloud-managed (requires internet for controller), which is a dependency we can't guarantee during a busy event venue. Omada runs the controller on-premises (our server at `192.168.123.181`) — no cloud dependency, full control, and the hardware is available immediately. That clinched the recommendation for TP-Link. Cisco's solution is architecturally cleaner at scale but wrong for our zero-cloud-dependency constraint.
- **Per-robot bandwidth budget.** Dominant consumer is RTSP video: 4 Mbit/s per robot at 720p/15 fps. Four robots × 4 Mbit/s = 16 Mbit/s video alone. MQTT telemetry and SSH control are negligible by comparison. The AP plan needs to guarantee 20+ Mbit/s aggregate per zone. Omada EAPs rated at 1.2 Gbps comfortably cover this; the bottleneck is the RF, not the wired backhaul.
- **CommanderAI as the demo interface.** The technical stack (Praxis SDK, MQTT, RTSP, vLLM, impact_agent) is invisible to a non-technical CEO. CommanderAI wraps it: one page, one command box, live feeds, robot status cards. The design goal is "type a sentence, watch the robots do it." The page pulls robot status from the Praxis API and streams video from MediaMTX; the command box posts to `impact_agent` which runs the full agentic loop. It's the product surface; Praxis is the infrastructure.
- **Local LLM as a demo constraint, not a preference.** The decision to use vLLM-hosted Gemma for the CommanderAI / impact_agent path rather than Bedrock Claude was driven by a real constraint: in a dense crowd with degraded Wi-Fi, internet-dependent Bedrock calls would fail or timeout unpredictably. The local vLLM endpoint on the server (`192.168.123.181:9090`) is LAN-only — immune to internet congestion. Lower performance than Claude, but zero dependency on external infrastructure.
- **Prompt robustness under crowd-demo conditions.** The demo isn't a dev environment — you can't retry. So the prompt needs to handle partial failures (one robot slow to respond) and edge cases (X2 arriving before Go2 has reported) without the whole sequence falling over. The explicit ordering in the prompt (`SCOUT FIRST, ANNOUNCER SECOND`) plus the mandatory same-turn post-`video_reasoning` update routine exist specifically so the agent can't accidentally shortcut the sequence.

### Impact
- TP-Link Omada selected as the network upgrade solution: on-premises controller, same-day hardware procurement possible, no cloud dependency, covers the bandwidth budget with significant headroom.
- CommanderAI takes shape as the demo's public face — by end of day it can show live robot status and accept a natural-language command that routes through `impact_agent`.
- Both parallel tracks (infrastructure + software) are in flight simultaneously, tracking toward the Fri Jul 3 migration and demo rehearsal window.

### Academic Connections
- **Networking / enterprise Wi-Fi.** SDN-managed vs cloud-managed AP topologies; on-premises controller as a reliability guarantee for air-gapped / congested environments; per-zone bandwidth planning for mixed media (video + telemetry + control).
- **AI agents / orchestration.** Local LLM as a reliability primitive for offline/degraded-internet demos; prompt robustness under ordering constraints as a correctness requirement; same-turn sequencing enforcement as the key mechanism preventing agent shortcuts.
- **Software architecture.** CommanderAI as a facade pattern over a complex distributed system — the public interface is intentionally simple (one command box, one video feed, one status card per robot); the Praxis platform is the engine underneath. Separating the demo interface from the integration platform keeps both simpler.
- **Systems engineering.** Parallel vendor evaluation with explicit elimination criteria (cloud dependency) rather than scoring-matrix-based selection; bandwidth budget as a concrete hardware requirement that eliminates candidates rather than informs preference.

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
