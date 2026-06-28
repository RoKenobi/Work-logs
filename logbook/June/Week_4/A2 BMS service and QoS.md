---
date: 2026-06-10
---

# Daily

## June 10, 2026

**Graph Nodes:** [[Agibot A2 Ultra]], [[GMSL Camera]], [[Praxis Platform]], [[Praxis Agents]], [[AIMDK]] · #ROS2 #Python #FFmpeg #OpenCV #MediaMTX #MQTT #DDS #V4L2 #H264 #QoS #MockMode #VendorAbstraction

**Theme:** [[ROS 2 Robotics Middleware]] (8 shared) · [[Video Streaming Infrastructure]] (5 shared) · [[Robotics Integration Infrastructure]] (4 shared)

### Summary
Closed out the A2 sensor-side bring-up: BMS health publisher with unit-normalisation and fault-code mapping, 7-DoF arm joint-state republisher with explicit `BEST_EFFORT` QoS to match the vendor publisher, and 1920×1536 V4L2 video streamer from the GMSL interaction camera. End-to-end demo with the cloud-side `concierge_agent` driving "wave hello and walk 2 m forward" as a single natural-language instruction routed through Praxis.

### Shipped
- **`robot_status_publisher.py`** — async `a2_services_pkg/srv/A2Request` client polling `/a2_get_bms_state_service` at 0.5 Hz, caching last-good response under `threading.Lock`, routing through Praxis `StatusManager`. JSON-encoded vendor struct normalised to SI:
  - `charge` (1=1%) → direct
  - `voltage` (1=1mV) → ×1e-3
  - `current` (1=1mA) → ×1e-3
  - `temperature` (1=0.1°C) → ×0.1
  - `abnormal_state`/`bms_state`/`charger_state` enums → Praxis fault codes
- **`joint_states_publisher.py`** — 7-DoF arm telemetry from `/motion/control/arm_joint_state`, explicit `QoSProfile(reliability=BEST_EFFORT, history=KEEP_LAST, depth=10)`, republished at 10 Hz on the Praxis schema
- **`video_streamer.py`** — V4L2 capture from `/dev/gmslcam6` at 1920×1536/15 fps, FFmpeg `libx264 fast` at 4 Mbit/s into MediaMTX, with `camera_info` co-publication on the Praxis bus
- **`use_mock` ROS parameter** on the BMS publisher — same node binary runs in dev (off-robot, mock data with warning) and production (real service)

### Technical Highlights
- **BEST_EFFORT vs RELIABLE QoS, the silent dropper.** The arm joint-state subscriber connected (`ros2 topic info` showed both endpoints, `ros2 topic echo` from a separate shell worked), but the in-process callback never fired. Vendor publishes with `BEST_EFFORT` reliability; `rclpy.Node.create_subscription` defaults to `RELIABLE`; DDS silently drops the subscription when profiles are incompatible. Fix is an explicit `QoSProfile` matching the vendor — but the more important lesson is that *when porting from a vendor sample, port the QoS too, not just the topic name and message type.*
- **Async service client over polling subscriber.** AIMDK exposes battery telemetry as a service rather than a topic, so `robot_status_publisher` is structurally different from the joint/pose publishers. Pattern: `create_client` + `wait_for_service` + `call_async` with future callbacks; `Lock`-guarded last-good cache so the 0.5 Hz timer can publish even if the service call is in flight or briefly unavailable.
- **Unit normalisation at the boundary.** Vendor reports voltage in mV, current in mA, temperature in tenths of °C. Normalisation happens once in `robot_status_publisher` at the system boundary — downstream consumers (dashboard, LLM agents, alarm rules) see SI units uniformly. Enum-to-fault-code mapping similarly lives at the boundary.
- **Mock-mode as a first-class development affordance.** `use_mock` ROS parameter lets the same Python binary run on a developer laptop with no robot attached, returning plausible BMS values with an explicit warning log line. Avoids `if DEVELOPMENT: ...` branches inside business logic.

### Impact
- A2 telemetry surface now complete: pose, joints, status, video. All four Praxis publishers running concurrently at their designed rates with no contention.
- End-to-end conversational demo successful: `concierge_agent` decomposed "have the humanoid wave hello and walk 2 m forward" into a `motion_replay` action (the systemd-managed motion server picks the right `.mcap` from the ~150-entry library) followed by `navigate_to_pose(2.0, 0.0)` (the discrete-dead-reckoning executor issues `SpinTurnAndMoveForward(0, 2.0)`), with feedback streamed back over MQTT to the dashboard.
- QoS-mismatch class of bug now has a permanent place in the team's onboarding doc — costs an afternoon every time someone hits it for the first time.
- The same `use_mock` parameter affordance was adopted by every subsequent driver in the fleet, including the Q5 and X2 work later this week.

### Academic Connections
- **Distributed systems.** DDS QoS policy compatibility model; publish-subscribe with reliability/durability/history dimensions; service-vs-topic API design trade-offs (one-shot request-response vs continuous broadcast).
- **Operating systems / device I/O.** V4L2 device interface; OpenCV `VideoCapture` backend selection; FFmpeg subprocess pipe lifecycle.
- **Software architecture.** Adapter pattern at protocol boundaries; SI-unit normalisation as a single-responsibility transformation; mock-mode as testability affordance; idempotent fault-code mapping from vendor enums to platform schema.
- **Concurrency.** Async service client with future callbacks; thread-safe last-good cache via `threading.Lock`; QoS-profile matching as a precondition for callback delivery.

- [ ] Obtain supervisor clearance for confidentiality before submitting

## Rolled up into

[[Agibot A2 Ultra ROS2 Integration]]

---
