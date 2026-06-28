---
date: 2026-06-08
---

# Daily

## June 08, 2026

**Graph Nodes:** [[Agibot A2 Ultra]], [[AIMDK]], [[Jetson Orin]] · #ROS2 #Python #systemd #HTTP #JSONRPC #DDS

**Theme:** [[ROS 2 Robotics Middleware]] (8 shared)

### Summary
Stood up the on-board service substrate for the Agibot A2 Ultra integration — four `systemd`-managed Python servers that wrap AIMDK's JSON-RPC endpoints as ROS 2 services and actions, with heartbeat-gated preflight launchers that hard-guarantee the AIMDK runtime is alive before any Praxis publisher tries to talk to it. This is the foundation the rest of the A2 driver builds on.

### Shipped
- **`/agibot/onboard_orin/` service tree** — four `systemd` units installed under `multi-user.target`:
  - `a2_get_bms_state.service` — wraps `HalBmsService.GetBmsState` HTTP-RPC as a ROS 2 service so the driver doesn't need to speak HTTP for battery telemetry
  - `a2_mc_get_action.service` — wraps `aimdk.protocol.McGetAction` (motion-control state read-back)
  - `a2_mc_set_action.service` — wraps `aimdk.protocol.McSetAction` (motion-control intent submission)
  - `a2_motion_action_server.service` — exposes the ~150-entry `.mcap` motion library as an `A2MotionRequest.action` long-running ROS 2 action
- **Custom message packages** — `a2_actions_pkg` (`A2MotionRequest.action`: `string goal → string result → string feedback`) and `a2_services_pkg` (`A2Request.srv`) built into `/agibot/a2_ws/`
- **Preflight launchers** — `start_*.sh` for each unit, sources `/opt/ros/humble/setup.bash` + `ros2_plugin_proto_aarch64` overlay + `/agibot/a2_ws/install/setup.bash`, exports `ROS_DOMAIN_ID=232`, pins `FASTRTPS_DEFAULT_PROFILES_FILE` to vendor `ros_dds_configuration.xml`
- **Unit hardening** — `Restart=always, RestartSec=2, User=agi, Type=simple` across all four; transient AIMDK crashes self-recover without operator intervention

### Technical Highlights
- **Two-stage heartbeat probe before service launch.** Naïve "wait for heartbeat topic to appear" fails because the topic is registered seconds before the runtime is actually publishing on it. The preflight script first waits up to 30 s for the topic to appear, *then* counts at least 5 heartbeat messages in a 10-s window before exec'ing the Python server. This catches the gap between AIMDK starting its DDS publishers and actually feeding them.
- **HTTP-endpoint reachability gate.** After the heartbeat passes, the launcher `curl`s each required HAL endpoint with a 5-s timeout, treating *any* HTTP response (including 4xx) as "reachable" — we only care that the socket is up, not the semantic status. This catches the additional gap between DDS heartbeat going healthy and the HTTP-RPC port actually accepting connections.
- **`systemd` as the recovery loop.** With `Restart=always, RestartSec=2`, the rare race where AIMDK comes up *after* the wrapper has already exited self-resolves within a couple seconds. The preflight contract means a restarted wrapper always re-validates the runtime, so no half-initialised state escapes.
- **Service wrapping as architectural choice.** AIMDK's vendor interface is JSON-RPC over HTTP, not ROS 2. Wrapping it in ROS 2 services on-board means every consumer downstream — the Praxis driver, any future LLM agent, even a teleop client — speaks the same `rclpy` client API and inherits the same discovery semantics. The HTTP plumbing is now the substrate's responsibility, not the driver's.

### Impact
- Provides a deterministic startup contract for the A2 driver: BMS and motion-control service surfaces are guaranteed reachable before any Praxis publisher attempts a connection, eliminating the "first dozen requests return service-unavailable" failure mode that would otherwise hit every robot boot.
- Decouples the Praxis driver from AIMDK's RPC layer entirely. The driver subclasses standard `rclpy` clients; if AIMDK's RPC shape changes, only the four wrappers need to track it.
- Reusable substrate pattern: the motion-action server design (long-running ROS 2 action over an HTTP trigger) becomes the template later in the week for the X2's TTS and the Q5's motion-replay executors.

### Academic Connections
- **Distributed systems.** Service mesh pattern via local proxy nodes; cross-protocol bridging (DDS ↔ HTTP-RPC) with reachability gating; supervisor-tree pattern via `systemd` Restart semantics.
- **Operating systems.** Linux `systemd` unit dependency expression (`After=`, `Wants=`, `multi-user.target`); process supervision; user-isolated service execution (`User=agi`).
- **Concurrency.** Race condition between DDS discovery and HTTP-RPC port availability; two-phase commit-style readiness probe (heartbeat-presence → heartbeat-flow → endpoint-reachability) before exposing a higher-level service.
- **Software architecture.** Adapter/wrapper pattern for vendor protocol abstraction; "fail fast at the substrate boundary so downstream consumers can assume health".

- [ ] Obtain supervisor clearance for confidentiality before submitting

## Rolled up into

[[Agibot A2 Ultra ROS2 Integration]]

---
