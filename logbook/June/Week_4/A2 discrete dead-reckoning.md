---
aliases:
  - 09-06-26
  - 2026-06-09
---

# Daily

## June 09, 2026

**Graph Nodes:** [[Agibot A2 Ultra]], [[Agibot D1 Max]], [[RobotEra Q5]], [[Unitree Go2]], [[AIMDK]], [[Praxis Platform]] · #ROS2 #Python #HTTP #JSONRPC #SE2Composition #DeadReckoning #MultithreadedExecutor #TwophaseTranslateRotate

**Theme:** [[ROS 2 Robotics Middleware]] (11 shared) · [[Robotics Integration Infrastructure]] (3 shared)

### Summary
Authored the flagship node of the A2 driver — `translate_and_rotate_executor` — implementing a discrete-step dead-reckoning model for a humanoid whose locomotion is RPC-planned (`SpinTurnAndMoveForward`) rather than velocity-streamed. The discrete integrator commits planned `(rotation, distance)` to the odom frame only after the RPC reports success, with the same SE(2) composition as the Go2 driver but on a per-move time base. This pattern has since been ported to D1 Max and Q5.

### Shipped
- **`translate_and_rotate_executor.py`** — `MultiThreadedExecutor` node unifying:
  - Praxis `set_pose` and `navigate_to_pose` action handlers
  - Three-frame state model: odom frame, world-frame anchor (snapshot at last `set_pose`), and on-demand world-pose getter that composes the two via SE(2)
  - RPC-driven `SpinTurnAndMoveForward` client with 1.5-s polling on `ActionGetState`, 60-second hard timeout per phase, `ctx.is_cancel_requested()` propagation
  - Discrete movement integration: rotation-first-then-translation, applied to odom only on `PncServiceState_SUCCESS`
- **Pose publisher fallback** — `pose_publisher.py` for telemetry-only mode when the executor isn't loaded (used during sensor-only bring-up)

### Technical Highlights
- **Discrete dead-reckoning as a first-class pattern.** Unlike the Go2 (continuous odom + Sport-mode RPC) or any quadruped with `/odom` streaming, the A2 plans the trajectory server-side and reports completion via task-id polling. The integrator therefore advances state only on success, not on a velocity callback. The algebra is the same SE(2) composition the Go2 uses; the integrator's time base is what differs. Same `world_pose = world_at_set + R(yaw_offset) · (odom − odom_at_set)` formula, just with discrete updates.
- **Rotation-before-translation order in `_integrate_movement`.** AIMDK's PNC executes the move in that order; the integrator must match. Initial implementation translated first into the old heading, then rotated. After 1.5 m / 90° moves, the endpoint differed from ground truth by ~5 cm — a systematic drift, not noise. Swapped the order; verified against tape-measured L-shaped trajectories.
- **Three-frame state held thread-safely.** Two callback groups (executor) plus `threading.Lock`-guarded mutation of `(world_x_anchor, world_y_anchor, world_yaw_anchor, odom_x_at_set, odom_y_at_set, odom_yaw_at_set)` so the on-demand world-pose getter can run from the publisher timer while the RPC poller is mid-flight.
- **AIMDK envelope and addressing.** `_send_spin_turn_and_move_forward` POSTs to `http://192.168.88.88:53176/rpc/aimdk.protocol.PncService/SpinTurnAndMoveForward` with the AIMDK header envelope (`timestamp`, `control_source`), a hard-coded internal map-id (distinct from the Praxis map UUID — that's tomorrow's debugging headline), the requested `angle` (rad) and `distance` (m). Response carries a `task_id` for the polling loop.
- **Cancellation discipline.** `ctx.is_cancel_requested()` is checked on every 1.5-s poll cycle. On cancel, the executor immediately stops polling and surfaces a clean action result rather than letting the RPC run to completion silently.

### Impact
- A2 navigation API is now wired into the same Praxis schema (`set_pose`, `navigate_to_pose`) every other robot uses; cloud-side LLM agents can route to the A2 via capability with no humanoid-specific code.
- Validated a reusable pattern for *any* robot whose locomotion API is RPC-planned rather than velocity-streamed. The discrete integrator + three-frame state + cancellation-aware poll loop later anchored the Agibot D1 Max integration and influenced the Q5's FSM-orchestration design.
- The rotation-first ordering decision turned a several-centimeter systematic drift per move into <1 cm composition error — the difference between a pose marker that visibly desynchronizes after three commands and one that stays glued to the physical robot.

### Academic Connections
- **Robotics theory.** SE(2) Lie group composition under discrete updates; equivalence of continuous-integration and discrete-step formulations under the same algebra; the importance of preserving the vendor's operation order when integrating a planned trajectory.
- **Distributed systems.** Long-running operation pattern: synchronous RPC submit → async `task_id` polling → terminal-state classification. Mirror of standard Kubernetes/cloud operator-reconcile loops at robot scale.
- **Concurrency.** `MultiThreadedExecutor` with `ReentrantCallbackGroup` separation of timer-driven publisher from RPC-driven state mutation; thread-safe state via `threading.Lock`; cancellation propagation through nested poll loops.
- **Software architecture.** State-machine encoding via three explicit frames (odom, world-anchor, world-now); composition rather than inheritance for pose representations; idempotent state updates committed only on success terminal states.

- [ ] Obtain supervisor clearance for confidentiality before submitting

## Rolled up into

[[2026-W24]]

---
