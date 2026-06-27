---
aliases:
  - 18-06-26
  - 2026-06-18
---

# Daily

## June 18, 2026

**Graph Nodes:** [[RobotEra Q5]] · #SE2Composition #DeadReckoning #FSMOrchestration #CycloneDDS #ROS2 #QoS

**Theme:** [[Robotics Middleware Infrastructure]] (4 shared) · [[Robot Middleware Integration]] (3 shared)

### Summary
Shipped the Q5 navigation stack: SE(2) dead-reckoning executor (same algebra as Go2, ported in an afternoon thanks to the shared utility module), velocity ramping for the 70 kg differential-drive chassis, and the discovery that the Q5 uses `geometry_msgs/TwistStamped` rather than the more common `Twist`. Also wired up the 34-DoF joint-state aggregator — highest-DoF robot in the fleet by a wide margin — and battery telemetry with calibrated SoC thresholds matching the physical LED warnings.

### Shipped
- **Dead-reckoning executor (`translate_and_rotate_executor.py`)** for the Q5 — same SE(2)-correct world-pose composition as the Go2 driver, ported via the shared `utils/pose_manager.py` module; wrapped in the FSM-orchestration sequence from yesterday
- **Differential-drive path decomposition** — replaced the Go2's holonomic strafe with a rotate-then-translate-then-rotate trajectory because Q5's wheeled base mechanically ignores `linear_y` and `linear_z`
- **`TwistStamped` publisher** to `/wr1_base_drive_controller/cmd_vel`, populated `header.stamp` from node clock, `header.frame_id = "odom"`
- **Velocity envelope and ramping** — max linear 1.5 m/s, max angular 2.0 rad/s, 0.05 m/s ramp step per control iteration, auto-decelerate when `dist_left < 0.2 m`. Tolerances: `dist_tol = 0.03 m`, `yaw_tol = 0.06 rad`
- **34-DoF `joint_states_publisher.py`** — flat `sensor_msgs/JointState` subscription, all 34 (20 body + 14 hand) joints forwarded unfiltered at 10 Hz on the Praxis schema
- **`robot_status_publisher.py`** — `/battery_state` (`sensor_msgs/BatteryState`) → `StatusManager` with empirically-calibrated thresholds (`<33%` autonomy ceiling, `<21%` warning matching yellow LED, `<9%` critical matching red flashing LED) and `power_supply_status` propagation (discharging=2, charging=3)

### Technical Highlights
- **`TwistStamped` vs `Twist`, the silent-ignore class of bug.** Initial implementation published `geometry_msgs/Twist` to `/wr1_base_drive_controller/cmd_vel` — the more common type, what every quadruped driver in the fleet uses. Publisher created without complaint; subscriber-side type mismatch caused ROS 2 to silently ignore the messages. Vendor's `cmd_vel` is `TwistStamped` (uncommon in the wider ROS ecosystem). Fix: type swap, populate `header.stamp` from node clock (CycloneDDS drops stale-timestamped messages under some QoS profiles), set `header.frame_id = "odom"`. Lesson now lives at the top of the team's "things to check first" list: confirm the message type via `ros2 topic info -v` before assuming the common form.
- **Differential-drive path decomposition.** Q5's base is differential-drive, not holonomic. The Go2 executor commands `vx`/`vy` simultaneously to strafe diagonally toward the target — that's mechanically impossible on the Q5. The path planner therefore decomposes a `(target_x, target_y)` into three phases: rotate to face the target, translate forward, rotate to final heading. Same `navigate_to_pose` Praxis action; the driver internally decides whether to use holonomic or differential-drive decomposition based on chassis class.
- **Velocity ramping as a chassis-mass concession.** Q5 is 70 kg on a differential-drive chassis. Initial step inputs at 1.5 m/s caused one wheel to spin out (encoder noise climbs, the other wheel takes over, the chassis veers). Ramping at 0.05 m/s per control iteration eliminates this — equivalent to a software-side acceleration limit. Auto-decelerate at `dist_left < 0.2 m` prevents overshoot at the target.
- **Empirical battery threshold calibration to match physical LEDs.** The vendor manual gives nominal voltage and SoC range but no warning-threshold guidance. The Q5 has *physical LED warnings*: yellow at some SoC, red flashing at lower. The driver's threshold bands (33% / 21% / 9%) were reverse-engineered to match the LED transitions, so the dashboard warning, the LLM agent's status read, and the operator's eyeball view of the robot all flag the same conditions at the same time.
- **High-DoF aggregation without filtering.** 20 body + 14 hand joints in one flat `JointState` array is a lot for a dashboard, but filtering upstream forces every downstream consumer (perception, policy learning, dashboard) to agree on what to keep. The driver forwards all 34 unfiltered with explicit name tagging (`wheel_*`, `left_hand_*`, etc.); consumers filter according to their own needs.

### Impact
- Q5 navigation works end-to-end: `set_pose` resets the world-frame anchor identically to the Go2 implementation, `navigate_to_pose` decomposes correctly for differential-drive, 3 cm / 3.4° tolerance achieved on bring-up tests matching the vendor's spec.
- Battery telemetry now agrees with the robot's physical LED state at every threshold; operators don't have to mentally translate between SoC percentage and the colour of the chest light.
- 34-DoF joint stream gives the perception team a rich enough feature vector to start training imitation policies on the Q5's bi-manual XHAND gestures — they previously only had the Agibot data, which is lower-DoF on the hands.
- `TwistStamped` lesson plus FSM orchestration from yesterday means the Q5 went from "scaffolded" to "drives end-to-end" in two days — same elapsed time as the X2, despite a more elaborate startup contract.

### Academic Connections
- **Robotics theory.** Differential-drive kinematics vs holonomic strafe; rotate-translate-rotate path decomposition for non-holonomic chassis; SE(2) composition as a chassis-class-agnostic abstraction; tolerance-driven control-loop termination.
- **Control theory.** Velocity ramping as a discrete-time acceleration limit; auto-deceleration as an open-loop deceleration profile; the trade-off between control aggressiveness and disturbance rejection on heavy chassis.
- **Distributed systems / ROS 2.** Stamped-vs-unstamped message types and the implicit timestamp QoS contract under CycloneDDS; `header.frame_id` semantics; the silent-drop failure mode of type-mismatched publishers.
- **Software architecture.** Chassis-class-parameterised path decomposition behind a uniform action schema (`navigate_to_pose`); empirical threshold calibration as a system-integration responsibility; unfiltered telemetry forwarding to keep downstream consumers free to choose what to consume.

- [ ] Obtain supervisor clearance for confidentiality before submitting

## Rolled up into

[[2026-W25]]

---
