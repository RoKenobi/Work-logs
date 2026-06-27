---
aliases:
  - 19-06-26
  - 2026-06-19
---

# Daily

## June 19, 2026

**Graph Nodes:** [[RobotEra Q5]], [[XOS Runtime]], [[Praxis Agents]] · #ROSTopic #HTTP #SettleDetection #VendorAbstraction #FSMOrchestration

**Theme:** [[Robot Middleware Integration]] (5 shared) · [[Praxis Integration Toolchain]] (3 shared)

### Summary
Shipped the most architecturally interesting node of the Q5 driver: `motion_replay_executor`, which fires the XOS HTTP runtime's recorded-motion endpoint and **blocks until the motion settles by watching `/joint_states`**, not by trusting the HTTP `200 OK`. The pattern — "settle by sensor feedback, never by RPC return" — is reusable for any robot whose motion library is HTTP-triggered fire-and-forget. Empirical exclusion list (wheel + left wrist + left hand) discovered after the naïve implementation never declared completion.

### Shipped
- **`motion_replay_executor.py`** — Praxis `motion_replay` action handler that POSTs `{"rosbag_name": "<name>"}` to `http://192.168.8.100:1888/robot/replay/do_replay_action` and then implements the multi-phase settle detector:
  1. POST the replay request
  2. Wait up to `motion_start_timeout_sec` (default 3 s) for any body joint velocity to exceed `motion_start_threshold` (0.1 rad/s); failure here returns "replay did not start"
  3. Poll `/joint_states` at 20 Hz (50 ms period)
  4. Compute `max(|velocity|)` across all body joints **excluding** wheels, left wrist, and left hand
  5. Once that max stays below `velocity_threshold` (0.05 rad/s) continuously for `settle_duration_sec` (1.0 s), declare motion complete
  6. Hard timeout at `max_wait_sec` (60 s)
- **Empirically-derived `EXCLUDED_JOINT_SUBSTRINGS = ("wheel", "left_wrist", "left_hand")`** — documented with the failure mode so future engineers don't add joints back blindly
- **`video_streamer.py`** for the wide-aspect 3840×1080 head camera — V4L2 `/dev/video0` via OpenCV, FFmpeg → MediaMTX, native resolution unscaled (sensor is designed for stereoscopic split-screen)
- **Operator runbook entry** for `sudo chmod 777 /dev/video*` one-shot per boot until a udev rule lands
- **End-of-week integration test**: `concierge_agent` driving a guided-tour sequence — `motion_replay("point_left")` → `navigate_to_pose(3.0, 0.0)` → `motion_replay("present_object")` — with the chassis correctly waiting for each arm gesture to settle before walking

### Technical Highlights
- **Sensor-feedback settle detection beats RPC-return trust.** Naïve implementation: POST and return success on HTTP 200. The XOS endpoint returns ~immediately on accept, *not* on motion completion. Sequencing `motion_replay` then `navigate_to_pose` then made the chassis start walking while the arms were still mid-gesture — bad-looking, potentially destabilising. The settle detector watches `/joint_states` for two transitions (motion start, then motion end) and only signals success after both. Same architectural pattern as the A2's task-id polling, but with sensor feedback as the success signal rather than a vendor task-state enum — applicable to any robot whose motion-library RPC is fire-and-forget.
- **Empirical exclusion list, derived from failure.** Initial implementation watched all 34 joints. Settle never triggered, because the wheel-drive joints have non-zero `velocity` even when the chassis is stationary (floor compliance, motor encoder noise), and the left wrist / left hand XHAND finger encoders have similar residual noise. The exclusion list `("wheel", "left_wrist", "left_hand")` was reached by inspecting the joint-velocity vector during a "robot stationary, motion finished" state and finding which channels were preventing the settle predicate from being satisfied. Documenting *why* each entry is on the list is critical — without that, a future engineer adding `left_hand` back to support a hand-only motion would silently break every existing replay.
- **Two-phase motion-tracking state machine.** The executor explicitly models motion-start and motion-end as separate detection events. The motion-start phase guards against "replay didn't actually start" (HTTP accepted, but the underlying motion controller failed to schedule the rosbag); the motion-end phase guards against "motion finished too quickly to detect" by requiring a continuous settle window rather than a single below-threshold sample.
- **The 3840×1080 wide-aspect sensor**, designed for stereoscopic split-screen, is forwarded unscaled to MediaMTX. Praxis dashboard already handles wide-aspect renders correctly; downsampling would lose the future stereo-decomposition option.

### Impact
- Q5 is now a fully integrated Praxis robot: battery, 34-DoF joint state, pose (from real odometry), head-camera video flow into the platform; `set_pose`, `navigate_to_pose`, and `motion_replay` actions flow back; the FSM is orchestrated automatically; motion replays compose cleanly with navigation in agent-driven sequences.
- The settle-detection pattern becomes a reusable building block for the fleet: any future robot exposing a motion library through an HTTP fire-and-forget endpoint can adopt the same `start → poll → settle` shape. The A2's task-id polling and the Q5's joint-velocity settle are two implementations of the same abstract pattern.
- `concierge_agent` end-to-end demo successful: guided-tour sequence drove the Q5 through three Praxis actions with no Q5-specific code on the agent side. The fleet-wide action vocabulary (`navigate_to_pose`, `motion_replay`, future `tts`) is now rich enough for non-trivial demonstrations on any robot that implements them.
- The exclusion-list-with-rationale documentation pattern (`# wheels: residual encoder noise even when stationary`) is a small but durable inoculation against the class of bug where a maintainer reverts a defensive measure without understanding why it was there.

### Academic Connections
- **Robotics / control theory.** Sensor-feedback termination as a robust alternative to open-loop trust in RPC return; settle-detection as a stability-criterion check across the joint-velocity vector; rationale-documented exclusion as a maintainability discipline.
- **Distributed systems.** HTTP fire-and-forget vs synchronous-completion semantics; two-phase tracking (start, end) as a state-machine over an asynchronous remote operation; the parallel between HTTP+sensor-settle and gRPC+task-id-poll as two implementations of the same long-operation pattern.
- **Software architecture.** Multi-phase state machines as explicit code structure; configurable thresholds (`motion_start_threshold`, `velocity_threshold`, `settle_duration_sec`, `max_wait_sec`) as a runtime tuning surface; empirical-with-rationale design as a forward-compatibility discipline.
- **Signal processing.** Continuous-below-threshold over a settle window as a debouncing filter against single-sample dips below the noise floor; multi-channel `max` aggregation as an OR-style coalesce of stop-condition predicates.

- [ ] Obtain supervisor clearance for confidentiality before submitting

## Rolled up into

[[2026-W25]]

---
