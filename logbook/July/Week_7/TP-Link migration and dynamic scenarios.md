---
date: 2026-07-03
---

# Daily

## July 03, 2026

**Graph Nodes:** [[Praxis Platform]], [[Praxis Agents]], [[Unitree Go2]], [[Agibot X2 Ultra]], [[RobotEra Q5]] · #vLLM #RTSP #MQTT #HTTP #Docker #IncidentResponse #VendorAbstraction

**Theme:** [[Robotics Integration Infrastructure]]

### Summary
The TP-Link network team arrived on-site with Omada enterprise hardware. Migrated the entire fleet — all robots, the server, the CCTV camera, and all Praxis services — from the old ad-hoc robot-AP setup to the new dedicated-AP topology. Hiccups encountered and overcome, everything validated before end of day. In parallel, colleague Joe completed two dynamic safety scenarios: bag detection from robot cameras and a perimeter-enforcement loop where X2 actively walks toward and warns any person entering the demo carpet zone during active analysis. Long day, but the fleet is on solid infrastructure going into the event.

### Shipped
- **Full TP-Link Omada enterprise migration completed** — new dedicated EAPs (enterprise access points) deployed with per-robot channel assignment and Omada SDN controller running on the server. Every robot, the CCTV camera, and all Praxis service containers now connect through the new topology. SSH, MQTT, and RTSP validated post-migration on all four robots simultaneously.
- **Joe's dynamic scenario 1 — bag detection** — Go2 and X2 cameras now feed a real-time VA pipeline that can identify abandoned/suspicious bags in the demo zone. Detection triggers an incident via the same Praxis agentic workflow as the fallen-boxes scenario. Validates that the incident-response infrastructure generalises beyond one pre-canned scenario.
- **Joe's dynamic scenario 2 — perimeter enforcement** — if any person enters the carpet/demo zone during an active analysis phase (e.g. while Go2 is at the scene), X2 detects the intrusion via VA, activates TTS ("Please move away from the area"), and walks toward the person. Uses the same `navigate_to_pose` + `tts` Praxis action pair already validated in earlier weeks. The loop runs continuously during the analysis window — X2 will keep repeating the approach-and-warn sequence until the person leaves or the phase ends.
- **Migration hiccups resolved:**
  - Initial IP address conflicts after migrating — robots retained old static IPs not in the new DHCP range; resolved by flushing ARP caches and re-assigning IPs via Omada controller
  - MediaMTX RTSP auth webhook needed the new server IP updated (same `authHTTPAddress` configuration from the RTSP auth fix earlier in the internship)
  - X2's floating DHCP lease (previously `.47` or `.48`) pinned to a single address via Omada MAC reservation — eliminates the dual-host probe in the fleet dashboard for good
  - Q5's GL-MT3000 subnet port-forward verified to work through the new AP topology

### Technical Highlights
- **Omada SDN as the architectural upgrade.** The old setup was ad-hoc: each robot's internal modem was its own independent AP, each on a random channel, no coordination. The new setup puts every device on APs managed by a single controller that coordinates channel assignment, transmit power, and roaming. Critically, each robot zone has its own dedicated EAP on a clean channel — the control, telemetry, and video planes for each robot are isolated from crowd-device RF noise by channel plan, not just power.
- **MAC reservation kills the X2 floating-IP problem for good.** The fleet dashboard's `_pick_reachable_host()` multi-host probe was the software workaround for X2's DHCP lease ambiguity. With the Omada controller reserving a static IP for X2's MAC address, the probe is unnecessary. The dashboard's X2 host config is now a single IP. One operational footgun permanently eliminated.
- **RTSP auth webhook IP update — the same class of bug as week 3.** MediaMTX's `authHTTPAddress` needs to point at the Praxis API backend's reachable IP. The old entry had the pre-migration server IP. After migration the server got a new IP from the Omada DHCP pool. Updating `authHTTPAddress` in `mediamtx.yml` and restarting the `praxis_video` Docker stack — same root cause as the June 2 RTSP auth fix, same fix, second time around.
- **Perimeter enforcement as an emergent capability from existing primitives.** Joe's scenario doesn't use any new Praxis actions — just `navigate_to_pose` + `tts` in a polling loop gated by a VA intrusion-detection trigger. The value is that it demonstrates the platform can compose existing primitives into safety behaviors beyond the pre-planned scenario. It's the same vendor-abstraction validation as the fallen-boxes demo, applied to a reactive safety use case.
- **Bag detection generalises the incident-response template.** The fallen-boxes scenario was hand-crafted for one incident type. Bag detection uses the same `create_incident` → `navigate_to_pose` → `video_reasoning` → `update_incident_confidence` pipeline but with a different trigger condition and a different VA prompt. The template is incident-agnostic; the scenario is parameterised by the VA's detection output. That's the architectural payoff of building a generic incident-management toolset rather than a one-off fallen-boxes system.

### Impact
- **Fleet is on enterprise Wi-Fi going into the NCS Impact event.** RF congestion from a crowd will no longer drop robot connectivity. All four robots + CCTV camera validated simultaneously on the new topology. The hard prerequisite from Monday is met.
- **X2's floating-IP problem permanently fixed** via MAC reservation — one less operational footgun in the fleet dashboard, one less thing that can silently fail during the demo.
- **Two new dynamic scenarios ready** — bag detection and perimeter enforcement both functional. These weren't in the original demo plan but give the event team additional scenarios to demonstrate if time allows, and validate that the incident-response architecture generalises.
- **Demo is rehearsal-ready** — the full fallen-boxes sequence (CCTV-triggered → Go2 → X2 → Q5 grabaid) runs end-to-end on the new network with local Gemma. The day ended late but the fleet is in the best shape it's been for a live event.

### Academic Connections
- **Networking / RF engineering.** SDN controller-managed channel coordination as the correct solution for high-density Wi-Fi; MAC-based DHCP reservation as a network-layer solution to dynamic-IP operational footguns; ARP cache flushing and IP re-assignment during live infrastructure migration.
- **Distributed systems.** Correlated failure mode (one RF failure kills all three planes simultaneously) eliminated by topology redesign; RTSP auth webhook IP as a hard-coded endpoint that becomes stale on infrastructure changes — same class of bug as the original RTSP auth fix, reinforcing the lesson that any hardcoded IP in a config file is a migration footgun.
- **AI agents / orchestration.** Emergent safety behavior from primitive composition (navigate + TTS + polling loop = perimeter enforcement); incident-type parameterisation of the generic `create_incident → navigate → vision → update` pipeline; the architectural payoff of generic toolsets over scenario-specific code.
- **Software architecture.** VA trigger → Praxis incident → robot dispatch as a clean event-driven pipeline where the sensor (CCTV VA) and the actuators (robots) are decoupled through the Praxis platform. Neither the VA nor the robots know about each other; the agent is the coordinator.
- **Operational engineering.** Live infrastructure migration under time pressure: ARP conflicts, RTSP auth IP, DHCP lease pinning — each resolved in sequence. The same debugging playbook (identify the changed variable, find what hardcodes it, update and restart) applied three times in one evening.

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
