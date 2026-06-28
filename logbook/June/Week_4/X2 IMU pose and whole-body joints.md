---
date: 2026-06-13
---

# Daily

## June 13, 2026

**Graph Nodes:** [[Agibot X2 Ultra]], [[Unitree Go2]], [[Agibot A2 Ultra]], [[Praxis Platform]], [[AIMDK]] · #ROS2 #MultithreadedExecutor #DeadReckoning #SE2Composition #QuaterniontoEuler #EMAFilter #DeadbandThreshold

**Theme:** [[ROS 2 Robotics Middleware]] (9 shared) · [[Robotics Integration Infrastructure]] (3 shared)

### Summary
Built the X2's IMU-fused dead-reckoning executor and the whole-body joint aggregator that merges four separate joint topics into a single Praxis publish stream. Key insight: read **absolute yaw** from the chest IMU's orientation quaternion rather than integrating angular velocity — the same stationary-drift class of bug the Go2 hit, but solved with a different fix because the X2 exposes a fused quaternion the Go2 doesn't.

### Shipped
- **IMU-fused executor in `translate_and_rotate_executor.py`** — subscribes `/aima/hal/imu/chest/state`, two `ReentrantCallbackGroup`s for sensor+timer parallelism on a `MultiThreadedExecutor`, world-frame integration of *commanded* `(vx, vy)` rotated into the IMU yaw
- **`joint_states_publisher.py`** — subscribes four topics (`/aima/hal/joint/{leg,arm,waist,head}/state`, each `aimdk_msgs/JointStateArray`) via a single shared lambda parameterised by `area`, maintains a unified `latest_joint_states` dict, republishes a 10 Hz snapshot to Praxis
- **`robot_status_publisher.py`** — `/aima/hal/pmu/state` (`aimdk_msgs/PmuState`) → Praxis `StatusManager` with empirically-recomputed warning bands for the X2's lower-nominal-voltage battery chemistry
- **`pose_publisher.py` fallback** — IMU-only telemetry mode for when the executor isn't loaded

### Technical Highlights
- **Absolute yaw from quaternion, never integrate angular velocity.** Initial implementation integrated `imu.angular_velocity.z` — same code shape as the Go2 fix. Under stationary conditions the pose marker rotated on the dashboard at ~0.01 rad/s, visibly twitching, because the chest IMU has a slow yaw bias drift when the magnetometer is disabled and the gyro bias isn't compensated. The X2 publishes a *fused* orientation quaternion (AIMDK on-board sensor fusion), so the executor now extracts yaw directly via `atan2(2(w·z + x·y), 1 − 2(y² + z²))` and assigns it; no integration. Stationary drift dropped to <0.001 rad/min — below visual perception. Same class of bug as the Go2, different fix; pick by what the vendor exposes.
- **Commanded velocity for translation, not IMU acceleration.** The chest IMU's linear-acceleration channels are noisy enough that double-integration drifts unusably within seconds. The executor instead uses the *commanded* velocity as a reference signal — clean by construction — and rotates it into the IMU yaw. The arbiter guarantees the robot tracks the command well enough that the position estimate stays accurate at the scale of a 5–10 m sequence (~5–10 cm error empirically).
- **Whole-body joint aggregation across four topics.** The X2 splits joints by body part (leg, arm, waist, head) across four `JointStateArray` topics. The Praxis `joint_states` schema is a flat dict. Solution: one `Subscription` per topic, all four callbacks pointing at the same `latest_joint_states` dict keyed by joint name, with a 10 Hz timer publishing the unified snapshot. Hands (`HandStateArray` with finger-array structure) are deliberately excluded for now — different message type, different finger-encoding semantics, out of scope for the initial integration.
- **Concurrency separation for the multi-threaded executor.** Sensor callbacks (IMU, four joint topics, PMU) go on one `ReentrantCallbackGroup`; the timer-driven Praxis publishers go on another. Without this separation, a busy joint-state callback queue can starve the publisher timer. The pattern reappears in §3.6 of the report — image streaming was dropping frames under joint-state load until the same separation was applied.

### Impact
- X2 telemetry surface fully wired: pose (IMU-fused), whole-body joints, PMU health into Praxis. The executor handles `set_pose` (resets the world-frame anchor) and `navigate_to_pose` (decomposes into a streaming velocity command sequence) under the same SE(2)-correct composition as the Go2 and A2.
- The fleet now has a complete library of stationary-drift mitigation strategies: deadband + EMA when only angular velocity is exposed (Go2), absolute yaw from quaternion when fusion is on-vendor (X2). Future drivers pick by what the vendor publishes.
- Whole-body aggregation pattern reusable for any robot whose vendor splits joint state across multiple topics. Joining at the driver-republish layer keeps the platform schema flat while letting the vendor structure its publishers however makes sense for its internal control architecture.

### Academic Connections
- **Robotics theory.** Sensor fusion at the platform-API boundary: vendor-fused quaternion vs raw gyro+accel integration; the cost of double-integrating accelerometer noise; commanded-velocity-as-reference vs measured-velocity-as-feedback in dead-reckoning. SE(2) composition reused identically across three drivers.
- **Signal processing.** Comparison of stationary-drift mitigation strategies: deadband + EMA on angular velocity (Go2 pattern) vs direct absolute-orientation read (X2 pattern). The Go2 fix trades phase lag for jitter reduction; the X2 fix is lossless because the noise was removed upstream.
- **Concurrency.** `MultiThreadedExecutor` with `ReentrantCallbackGroup` separation of sensor inflow from timer-driven outflow as a precondition for low-jitter publish rates under variable load; producer/consumer isolation pattern at the `rclpy` callback layer.
- **Software architecture.** Schema flattening at the driver-republish layer; vendor-internal structure stays out of the platform API; the `(name, position, velocity, effort)` quadruple as a stable joint-state lingua franca across heterogeneous robots.

- [ ] Obtain supervisor clearance for confidentiality before submitting

## Rolled up into

[[Agibot X2 and RobotEra Q5 Integration]]

---
