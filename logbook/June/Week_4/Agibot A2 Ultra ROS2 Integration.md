---
---

# Weekly

## June 14, 2026

**Graph Nodes:** [[Agibot A2 Ultra]], [[Praxis Platform]], [[AIMDK]], [[GMSL Camera]], [[Jetson Orin]] · #ROS2 #systemd #Python #DDS #MQTT #JSONRPC #tmuxinator #colcon #QoS #SE2Composition #DeadReckoning #MultithreadedExecutor #VendorAbstraction

**Theme:** [[ROS 2 Robotics Middleware]] (14 shared) · [[Robotics Integration Infrastructure]] (4 shared)

### Summary
Shipped the Agibot A2 Ultra end-to-end into Praxis: a six-node ROS 2 driver atop a four-unit `systemd`-managed on-board service substrate, the second-ever discrete-dead-reckoning executor pattern in the fleet, and a deployment workflow that reaches `READY` status against the `@assess-integration` agent. Closed the week with a conversational demo — `concierge_agent` decomposed "wave hello and walk 2 m forward" into a `motion_replay` action followed by a `navigate_to_pose` with feedback streamed back over MQTT.

### Shipped
- **On-board service substrate** (`/agibot/onboard_orin/`) — four `systemd`-managed Python servers wrapping AIMDK JSON-RPC endpoints as ROS 2 services and actions: `a2_get_bms_state`, `a2_mc_get_action`, `a2_mc_set_action`, `a2_motion_action_server`. Heartbeat-gated preflight launchers with two-stage probe (topic-presence then 5-message-in-10s flow, then HAL-endpoint `curl`). Unit hardening: `Restart=always, RestartSec=2, User=agi`.
- **Custom message packages** — `a2_actions_pkg/A2MotionRequest.action`, `a2_services_pkg/A2Request.srv`.
- **`praxis_agibot_a2_ultra` driver package** — six runtime nodes: `translate_and_rotate_executor` (discrete dead-reckoning + RPC poll loop), `pose_publisher`, `joint_states_publisher` (7-DoF arm, `BEST_EFFORT` QoS), `robot_status_publisher` (async BMS service client with SI normalisation), `video_streamer` (GMSL `/dev/gmslcam6` at 1920×1536/15 fps), `camera_info_publisher`.
- **Production tmuxinator profile** — canonical six-line `pre_window` sourcing chain (ROS core → domain+locality → FastDDS profile → vendor proto-msg bridge → AIMDK workspace → Praxis driver) plus a five-pane main window.
- **`deploy_ros` reuse** unchanged from the Go2 work — Humble auto-detect, `rosdep`, `.bashrc` idempotent mutation with timestamped backups, `colcon build --symlink-install`.

### Technical Highlights
- **Discrete dead-reckoning as a first-class fleet pattern.** A2's locomotion is RPC-planned via `SpinTurnAndMoveForward`, not velocity-streamed. The integrator commits planned `(rotation, distance)` to the odom frame *only* after `PncServiceState_SUCCESS`, with the same SE(2) composition as the Go2 driver — only the time base is different. Three frames held thread-safely (odom, world-anchor at last `set_pose`, on-demand world-now); rotation-before-translation order in `_integrate_movement` because AIMDK's PNC executes the maneuver in that order (flipping the order produces ~5 cm drift over a 1.5 m / 90° move).
- **BEST_EFFORT vs RELIABLE QoS as a silent dropper.** Arm joint-state subscriber connected, callback never fired, `ros2 topic echo` from a separate shell worked. Vendor publishes with `BEST_EFFORT`; default `rclpy` subscriber is `RELIABLE`; DDS silently drops incompatible profiles. When porting from a vendor sample, port the QoS profile too — not just topic name and message type.
- **Two map-id namespaces, two failures.** PNC `SpinTurnAndMoveForward` rejected every request with `CommonState_FAIL` because the payload's `map_id` was being filled with the Praxis UUID (`96835da7-…`). PNC expects the AIMDK 64-bit integer map-id from the on-board SLAM pipeline. Both IDs now pinned in the driver; runbook documents the manual re-alignment when SLAM rebuilds.
- **FastDDS profile + `ROS_DOMAIN_ID` + `ROS_LOCALHOST_ONLY` is a three-variable footgun.** The driver could see AIMDK topics from a directly-spawned `ros2 topic list` but in-process publishers never discovered them. Vendor's `ros_dds_configuration.xml` opens loopback and sets a multicast TTL appropriate for the on-board network; the default profile restricts to localhost. All three variables now pinned in `pre_window`.
- **Heartbeat-gated systemd startup.** AIMDK's heartbeat topic appears seconds before the runtime is actually publishing on it. Preflight script waits for the topic, then counts 5 messages in a 10-s window, then `curl`s the HAL endpoint with a 5-s timeout. Combined with `Restart=always, RestartSec=2`, transient AIMDK crashes self-recover without manual intervention.

### Impact
- Agibot A2 Ultra reaches full Praxis fleet parity within four working days. BMS, arm joint state, pose (discrete-dead-reckoned), and 4 MP camera video flow into the platform; `set_pose`, `navigate_to_pose`, and `motion_replay` actions flow back; the `systemd` substrate handles AIMDK restart cycles transparently. Operator bring-up reduced to one alias on top of the substrate.
- **End-to-end demo (June 10)**: `concierge_agent` natural-language instruction routed through the Praxis action vocabulary, no humanoid-specific code on the agent side — the motion library (`.mcap` catalogue of ~150 entries) is picked by semantic name through the motion-action server, then the navigation executor handles the locomotion.
- **Pattern reuse**: the discrete-dead-reckoning executor + three-frame state model + cancellation-aware RPC poll loop becomes the template for the Agibot D1 Max bring-up and influences the Q5 FSM-orchestration design later in the week.
- **Diagnostic playbook entries**: QoS-mismatch as a silent dropper, asymmetric discovery as a FastDDS-profile hint, two-namespace map-id alignment, heartbeat-gated startup as a substrate pattern.

### Academic Connections
- **Robotics theory.** SE(2) Lie group composition under discrete updates (vs continuous integration); preserving vendor operation order when integrating a planned trajectory; the equivalence of discrete-step and continuous formulations under the same algebra.
- **Distributed systems.** Service mesh pattern via local proxy nodes; cross-protocol bridging (DDS ↔ HTTP-RPC); long-running operation pattern (submit + task-id poll + terminal-state classification) as a mirror of cloud operator-reconcile loops at robot scale; namespace separation across federated identity systems.
- **Concurrency.** `MultiThreadedExecutor` with `ReentrantCallbackGroup` separation; `threading.Lock`-guarded three-frame state; cancellation propagation through nested poll loops; async service client with future callbacks.
- **Operating systems.** `systemd` unit dependency expression (`After=`, `Wants=`, `multi-user.target`); supervisor-tree pattern via `Restart` semantics; two-stage readiness probe (heartbeat-presence → heartbeat-flow → endpoint-reachability).
- **Networking.** DDS QoS policy compatibility model (reliability/durability/history); multicast TTL and locality scope; environment-driven discovery as a hidden configuration surface.
- **Software architecture.** Schema uniformity at the platform layer with sharply-different driver implementations underneath; vendor-protocol-abstraction adapter pattern at the substrate boundary; mock-mode as a testability affordance; idempotent fault-code mapping at the system boundary.

## Source dailies

[[A2 systemd substrate]] [[A2 discrete dead-reckoning]] [[A2 BMS service and QoS]] [[A2 map-id and FastDDS profile]]

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
