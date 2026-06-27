---
aliases:
  - Weekly_W5
  - 2026-W25
---

# Weekly

## June 21, 2026

**Graph Nodes:** [[Agibot X2 Ultra]], [[RobotEra Q5]], [[Unitree Go2]], [[Agibot A2 Ultra]], [[Praxis Platform]], [[AIMDK]] · #ROS2 #CycloneDDS #DDS #FFmpeg #OpenCV #colcon #tmuxinator #HTTP #V4L2 #SE2Composition #DeadReckoning #MultisourceArbitration #FSMOrchestration #MultithreadedExecutor #SettleDetection #TwophaseTranslateRotate #QoS

**Theme:** [[ROS 2 Robotics Middleware]] (17 shared) · [[Robotics Integration Infrastructure]] (4 shared)

### Summary
Shipped two complete humanoid integrations end-to-end: Agibot X2 Ultra (bipedal, IMU-fused dead-reckoning, multi-source arbitration, TTS) Mon-Wed, and RobotEra Q5 (60 V 70 kg wheeled humanoid, FSM-orchestrated, settle-detected motion replay) Wed-Fri. The fleet now has three architecturally-distinct pose-estimation strategies — vendor odom (Go2), discrete RPC (A2), IMU+commanded velocity (X2), and Q5 odom delta integration — all under one Praxis `set_pose` / `navigate_to_pose` schema. Cloud-side `concierge_agent` drove a guided-tour sequence on the Q5 by week's end without any Q5-specific code on the agent side.

### Shipped
- **`praxis_agibot_x2_ultra` driver** — six runtime nodes: `translate_and_rotate_executor` (IMU-fused absolute-yaw + commanded-velocity integration, two `ReentrantCallbackGroup`s), `joint_states_publisher` (four-topic whole-body aggregation), `robot_status_publisher` (PMU with X2-specific thresholds), `video_streamer` (`sensor_msgs/Image` topic + `cv_bridge` + FFmpeg), `velocity_publisher`, `tts_executor` (SetVolume → PlayTts with priority propagation).
- **`SetMcInputSource` arbitration registration** at executor startup — `INPUT_ACTION_REQUEST` with explicit priority to win against teleop, 5-s wait with logged outcome.
- **`aimdk_msgs` package build integration** with correct `colcon` topological ordering (`aimdk_msgs` → `sdk_X2` → driver).
- **`praxis_robotera_q5` driver** — seven runtime nodes: `translate_and_rotate_executor` (FSM-orchestrated SE(2) dead-reckoning, ramped differential-drive `TwistStamped` publisher), `pose_publisher`, `joint_states_publisher` (34-DoF unfiltered), `robot_status_publisher` (LED-matched SoC thresholds, `power_supply_status` propagation), `video_streamer` (3840×1080 wide-aspect V4L2), `camera_info_publisher`, `velocity_publisher`, `motion_replay_executor` (XOS HTTP trigger + joint-velocity settle detection).
- **FSM-orchestration startup** — driver advances Q5 from `INIT → IDLE → READY → ACTIVE` via `/ready_service` and `/activate_service` calls with graceful degradation to passive-telemetry mode if either service is unavailable.
- **Production tmuxinator profiles** for both robots; runbook entries documenting Q5's pre-flight (SSH session, manual `initpose_handsdown`, `/dev/video*` chmod).

### Technical Highlights
- **Multi-source arbitration on X2.** Publish topic ≠ command channel. AIMDK's locomotion controller arbitrates between registered input sources by priority; an unregistered publisher's messages reach the arbiter and get discarded. `SetMcInputSource` at startup with explicit high priority resolves it within one control cycle. Diagnostic playbook now reads: "if it publishes but doesn't move, suspect DDS implementation, FSM state, arbiter registration, or QoS — in that order."
- **Three pose-estimation strategies, three justifications.** Go2: vendor-fused continuous odom (consume directly). A2: discrete commit on RPC success (no continuous source). X2: IMU absolute yaw + integrated commanded velocity (no `/odom` topic, IMU only). Same SE(2) algebra across all three; the differentiator is what the vendor exposes. Future drivers pick by available signals, not by re-inventing.
- **Absolute yaw from fused quaternion vs integrated angular velocity.** X2 chest IMU has slow yaw bias drift (~0.01 rad/s stationary). Integrating angular velocity reproduces the Go2's stationary-drift bug. But the X2 publishes a fused orientation quaternion (AIMDK on-board fusion), so the executor reads `atan2(2(w·z + x·y), 1 − 2(y² + z²))` directly — no integration. Stationary drift dropped to <0.001 rad/min. Lossless because the noise was removed upstream; pick by what the vendor publishes.
- **CycloneDDS vs FastDDS implementation mismatch (Q5).** Fresh shell, `ros2 topic list` returned empty despite the Q5 being online. Q5 publishes via CycloneDDS, host defaulted to FastDDS, no interop at the DDS discovery layer. `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` in `pre_window` — 0% to 100% topic visibility in one line.
- **FSM orchestration in driver, not operator's head.** Q5's `INIT → IDLE → READY → ACTIVE` machine had been assumed pre-advanced; "publishes `TwistStamped`, robot doesn't move" because FSM was stuck in `READY`. Executor now advances the FSM itself on startup with `std_srvs/srv/Trigger` calls and graceful degradation if either service is unavailable.
- **`TwistStamped` vs `Twist`, silent-ignore class.** Q5 uses the stamped variant (uncommon ecosystem-wide). Publisher with `Twist` succeeded silently; subscriber-side type mismatch dropped every message. Type swap + `header.stamp` from node clock (CycloneDDS drops stale timestamps under some QoS) + `header.frame_id = "odom"`.
- **Settle-by-sensor-feedback, not RPC-return.** Q5's XOS motion-replay HTTP endpoint returns ~immediately on accept, not on motion completion. Naïve sequencing made the chassis walk while arms were mid-gesture. The settle detector watches `/joint_states` for two transitions (start: any body joint velocity > 0.1 rad/s; end: max(|velocity|) < 0.05 rad/s continuously for 1.0 s) with an empirically-derived exclusion list (`wheel`, `left_wrist`, `left_hand` — residual encoder noise). Pattern reusable for any robot with HTTP-triggered fire-and-forget motion libraries.
- **`MultiThreadedExecutor` + `ReentrantCallbackGroup` is mandatory for sensor-heavy driver nodes.** Single-threaded executors serialise image callbacks behind joint-state deserialisation under load; frame drops to 5–8 fps. Sensor subscriptions on one callback group, timer-driven publishers on another → throughput returns to source rate with zero drops. Now the default pattern.
- **URL-encoded service namespace gotcha (X2 TTS).** AIMDK registers `aimdk_msgs/srv/SetVolume` under percent-encoded `aimdk_5Fmsgs/srv/SetVolume`. Strict lookups by unencoded name fail silently. Trust `ros2 service list`, not your own typing.

### Impact
- Both robots reach full Praxis fleet parity in three working days each. X2: PMU, whole-body joint state, IMU-fused pose, head-camera ROS-image stream, `set_pose`/`navigate_to_pose`/`tts` actions. Q5: battery, 34-DoF (highest in the fleet) joint state, odom-derived pose, 3840×1080 wide-aspect camera, `set_pose`/`navigate_to_pose`/`motion_replay` actions.
- **Guided-tour demo (June 19)**: `concierge_agent` drove the Q5 through `motion_replay("point_left")` → `navigate_to_pose(3.0, 0.0)` → `motion_replay("present_object")` with the chassis correctly waiting for each arm gesture to settle before walking. Zero Q5-specific code on the agent side.
- **Fleet now has four robots integrated** (Go2, A2, X2, Q5) with three architecturally-distinct locomotion API models (continuous topic, discrete RPC, streaming-with-arbitration) and three pose-estimation strategies (vendor odom, discrete commit, IMU-fused). The Praxis SDK's schema-uniformity-with-implementation-flexibility design validates at scale.
- **Action vocabulary grows**: `tts` (X2, shared with A2/Q5 audio backends), `motion_replay` (Q5, shared with A2's motion catalogue). Both flow back into the fleet — every robot that has a recorded-motion library can implement `motion_replay` and inherit the settle-detection contract.
- **Diagnostic playbook gains a multi-cause framework** for "publishes but doesn't move": DDS implementation → FSM state → arbiter registration → QoS profile. Four distinct root causes seen across A2/X2/Q5 this fortnight.
- **`MultiThreadedExecutor` + `ReentrantCallbackGroup`** becomes the default for any sensor-heavy driver node fleet-wide.

### Academic Connections
- **Robotics theory.** Three SE(2) dead-reckoning strategies under one schema; differential-drive vs holonomic path decomposition (rotate-translate-rotate vs strafe); chassis-class-parameterised navigation behind a uniform action surface; tolerance-driven control-loop termination; velocity ramping as discrete-time acceleration limit.
- **Distributed systems.** Multi-source publisher arbitration as a control-plane primitive distinct from the topic data plane; DDS implementation interoperability gap (CycloneDDS vs FastDDS); environment-controlled discovery as a hidden configuration surface; HTTP fire-and-forget vs RPC task-id polling vs sensor-feedback settle as three implementations of the same long-running-operation pattern.
- **Control theory / state machines.** Driver-orchestrated vendor FSM (Mealy-state semantics over services); graceful degradation as a partial-failure policy; two-phase motion tracking (start, end) as explicit state-machine code structure; continuous-below-threshold over a settle window as a debounce filter.
- **Sensor fusion / signal processing.** Vendor-fused quaternion vs raw gyro+accel integration trade-off; commanded-velocity-as-reference vs IMU-acceleration-as-feedback for position; multi-channel `max(|velocity|)` aggregation with rationale-documented exclusion list; absolute-orientation read as the lossless mitigation for stationary drift.
- **Concurrency.** `MultiThreadedExecutor` + `ReentrantCallbackGroup` separation as a precondition for low-jitter sensor-heavy nodes; producer/consumer isolation at the `rclpy` callback layer; head-of-line blocking in single-threaded callback queues.
- **Software architecture.** Schema-uniformity-with-implementation-flexibility at the platform/driver boundary; chassis-class-parameterised behaviour under a uniform action API; URL-encoded namespace as an undocumented vendor-runtime transformation; end-to-end priority propagation through the API stack; rationale-documented empirical configuration as a forward-compatibility discipline.
- **Networking.** RMW abstraction across DDS implementations as a transparent-on-success / opaque-on-failure design; stamped-vs-unstamped message types with implicit timestamp QoS contracts; `header.frame_id` semantics; the silent-drop failure mode of type-mismatched publishers.

## Source dailies

[[2026-06-12]] [[2026-06-13]] [[2026-06-15]] [[2026-06-17]] [[2026-06-18]] [[2026-06-19]]

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
