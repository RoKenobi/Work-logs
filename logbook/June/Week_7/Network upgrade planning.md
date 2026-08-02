---
date: 2026-06-30
---

# Daily

## June 30, 2026

**Graph Nodes:** [[Praxis Platform]], [[Unitree Go2]], [[Agibot X2 Ultra]], [[RobotEra Q5]] · #systemd #HTTP #VendorAbstraction

**Theme:** [[Robotics Integration Infrastructure]]

### Summary
Diagnosed a critical connectivity failure mode that had been lurking under normal conditions but would be catastrophic at the NCS Impact event: when too many people gather in range of the robots' internal Wi-Fi modems, connectivity to all robots drops entirely — our AP mode and the robots' own hotspot modes both collapse under interference. With a week until the event, came up with two infrastructure upgrade plans, evaluated them, got sign-off from the boss and a network specialist, and locked the path forward.

### Shipped
- **Root cause diagnosed** — robot connectivity loss under crowd conditions traced to the robots' built-in Wi-Fi modems (internal hotspot / AP mode) competing with each other and with crowd devices on the 2.4/5 GHz bands. When enough people are nearby, the signal-to-noise floor degrades to the point where SSH, MQTT, and RTSP all drop simultaneously. Not a software problem — a physics problem.
- **Two infrastructure plans drafted and evaluated:**
  - **Plan A (adopted):** Replace the ad-hoc robot AP setup with proper industry-scale networking — dedicated access points locked to specific robots, providing isolated RF channels per device. Multiple APs across the demo floor prevent any single AP from being overwhelmed. No shared congestion regardless of crowd size.
  - **Plan B (rejected):** Stick with current setup but use channel-bonding and power adjustments on the existing modems. Assessed as insufficient for an event-scale crowd and fragile to interference from attendee devices.
- **Vendor shortlist:** TP-Link (Omada enterprise Wi-Fi series) and Cisco (Meraki) identified as the two candidates to consult. Meeting with both booked for tomorrow.
- **Boss + network specialist approval** — plan presented, risk of event failure without it made clear, Plan A approved for immediate procurement and deployment this week.

### Technical Highlights
- **The failure mode is a crowd-induced RF collision problem, not a driver or SDK bug.** Each robot's internal modem (typically a 2.4 GHz hotspot) competes for airtime on the most congested part of the spectrum. Under normal lab conditions (2–3 people, clear spectrum) connectivity is fine. Under demo conditions (50+ people with phones) every device in the room retransmits, the collision domain fills, and 802.11 CSMA/CA back-off timers compound until effective throughput collapses. The robots' control links (SSH), telemetry plane (MQTT), and video plane (RTSP) all share the same congested medium.
- **Dedicated per-robot AP isolation is the correct architectural fix.** By assigning each robot to its own access point on a clean channel, we remove inter-robot RF contention entirely. The AP–robot link is a private collision domain; crowd devices on different APs or different channels can't interfere with it. This is the same pattern enterprise venues use to support high-density Wi-Fi — Cisco and TP-Link Omada both support the required channel plan and roaming coordination.
- **Impact event context tightens the tolerance to zero.** A connectivity failure during a lab demo is recoverable — restart and retry. A connectivity failure during a live CEO/leadership demo is not. The upgrade isn't an improvement, it's a prerequisite.

### Impact
- Infrastructure upgrade plan approved and vendor consultations booked for tomorrow, with three days of runway before the event to receive hardware, deploy, and validate.
- Both RF planes affected by the upgrade: control/telemetry (MQTT over TCP, SSH) and video (RTSP multicast/unicast). All three robots plus the CCTV camera and the server will migrate to the new AP topology.
- The root-cause analysis gives the team a clean mental model going forward: robot connectivity is an RF engineering problem, not just a network configuration problem. Future demos and events need to pre-plan AP coverage as part of the deployment checklist.

### Academic Connections
- **Networking / RF engineering.** 802.11 CSMA/CA collision avoidance under high-density conditions; the effect of crowd-induced interference on effective Wi-Fi throughput; channel planning and AP isolation as the standard enterprise mitigation.
- **Systems engineering.** Failure mode analysis under real-world (vs lab) operating conditions; risk assessment framework for live events (cost of failure × probability → justify the upgrade cost); vendor evaluation process (requirements → two candidates → parallel consultation).
- **Distributed systems.** Multi-plane reliability: MQTT/SSH/RTSP all sharing the same physical medium means a medium failure is a correlated failure across all planes simultaneously. Plane separation (control vs telemetry vs video) only helps if the physical layers are also separated or isolated.

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
