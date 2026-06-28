---
date: 2026-06-12
---

# Daily

## June 12, 2026

**Graph Nodes:** [[Agibot X2 Ultra]], [[Praxis SDK]], [[Unitree Go2]], [[Agibot A2 Ultra]], [[AIMDK]] · #DDS #MultisourceArbitration #DeadReckoning #colcon

**Theme:** [[ROS 2 Robotics Middleware]] (6 shared) · [[Robotics Integration Infrastructure]] (3 shared)

### Summary
Started the Agibot X2 Ultra integration — a bipedal humanoid whose locomotion API is *neither* continuous odom (Go2) nor discrete RPC (A2), but instead a streaming `McLocomotionVelocity` topic whose publishers are selected by a priority arbiter. Today's headline result was diagnosing why the driver's velocity commands were going out at 10 Hz but the robot wasn't moving: AIMDK's multi-source arbiter was silently ignoring an unregistered publisher. Resolution: explicit `SetMcInputSource` service call at startup with high priority.

### Shipped
- **`praxis_agibot_x2_ultra` package skeleton** — six-node ament_python driver scaffolded via the shared `create_driver.sh`, registered against the X2 device-id in the Praxis backend
- **`SetMcInputSource` startup call** in the executor — one-shot service request with `INPUT_ACTION_REQUEST` and explicit priority high enough to win against teleop, 5-s wait with logged outcome
- **`velocity_publisher.py`** — 10 Hz streaming `McLocomotionVelocity` publisher on `/aima/mc/locomotion/velocity` (commented out of the production tmuxinator profile to avoid contending with the executor)
- **`aimdk_msgs` build integration** — vendor message package added to the `praxis_ws` source tree, `colcon build` topological ordering verified (`aimdk_msgs` first, then `sdk_X2`, then the driver)

### Technical Highlights
- **Multi-source arbitration: publish topic ≠ command channel.** AIMDK's locomotion controller is fed by *multiple* potential publishers (teleop, autonomy, this driver). Selection is by registered priority, not by topic ownership. Publishing to `/aima/mc/locomotion/velocity` without first registering as an `McInputSource` succeeds at the DDS layer — your messages arrive at the arbiter — but the arbiter discards them. The driver now calls `/aimdk_msgs/srv/SetMcInputSource` once at startup with `INPUT_ACTION_REQUEST` and a priority that beats teleop; the velocity stream takes effect within one control cycle thereafter.
- **Three pose-estimation strategies, three reasons.** With X2 added to the fleet there are now three distinct dead-reckoning strategies, each justified by what the vendor exposes:
  - Go2: vendor-fused continuous odometry consumed directly
  - A2: discrete commit on RPC success (no continuous source)
  - X2: IMU-fused absolute yaw + integrated commanded velocity for position (no `/odom` topic, IMU only)
  The Praxis SDK's `set_pose` schema is uniform across all three; the executor implementations are sharply different.
- **Architectural taxonomy: streaming vs RPC vs hybrid locomotion APIs.** The X2 sits between the Go2's continuous-stream model and the A2's plan-and-poll model — it accepts a continuous stream but requires arbitration registration. This is a useful classification axis when onboarding a new robot: which of {topic ownership, RPC task lifecycle, arbiter priority} governs whether your commands win.
- **Topological build ordering in `colcon`.** `aimdk_msgs` provides the message bindings consumed by `sdk_X2` and by the Praxis driver, so it must build first. `colcon build --symlink-install` handles the dependency graph correctly once `package.xml` declares the dependency — but the symptom of forgetting it (an `ImportError` for `aimdk_msgs.msg.McLocomotionVelocity` deep in driver bring-up) is far enough downstream that the diagnosis takes longer than the fix.

### Impact
- X2 driver moves from publishing-into-the-void to actually driving the robot within one bring-up day; the arbiter footgun is documented in the team's runbook as "if it publishes but doesn't move, suspect arbitration before suspecting your physics".
- The fleet now has three concretely-different locomotion API integrations under one Praxis schema, validating the SDK's design: the cloud-side LLM agents drive Go2, A2, and X2 through the same `navigate_to_pose` action without knowing the underlying API model differs.
- Build-order discipline (`aimdk_msgs` → `sdk_X2` → driver) encoded in `package.xml` `<depend>` tags, so the colcon graph is the single source of truth for the dependency chain.

### Academic Connections
- **Distributed systems.** Multi-source publisher arbitration as a control-plane primitive: the topic is the data plane, the arbitration registration is the control plane. Maps onto leader-election / priority-based mutex patterns at robot scale.
- **Control theory.** Streaming velocity command at the bandwidth-appropriate rate (10 Hz) for a tightly-coupled locomotion control loop; comparison with the A2's planning horizon (single discrete RPC per intent) and the Go2's continuous velocity API.
- **Software architecture.** Schema uniformity at the platform layer with sharply-different driver implementations underneath; classification of vendor APIs by control-plane model (topic-ownership / RPC-lifecycle / arbiter-priority).
- **Build systems.** Topological ordering of intermediate artifact builds; `colcon` package dependency graph; the cost of build-order errors manifesting as far-downstream runtime `ImportError`s.

- [ ] Obtain supervisor clearance for confidentiality before submitting

## Rolled up into

[[Agibot X2 and RobotEra Q5 Integration]]

---
