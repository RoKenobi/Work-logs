---
aliases:
  - 17-06-26
  - 2026-06-17
---

# Daily

## June 17, 2026

**Graph Nodes:** [[RobotEra Q5]], [[Praxis Platform]] · #CycloneDDS #DDS #ROS2 #FSMOrchestration #ROSService #VendorAbstraction

**Theme:** [[Robot Middleware Integration]] (4 shared)

### Summary
Started the RobotEra Q5 humanoid driver and tracked down two distinct "publishes but doesn't move" classes of bug back-to-back — the Q5's strict `INIT → IDLE → READY → ACTIVE` FSM must be advanced via service calls before any `cmd_vel` takes effect, and the host had `RMW_IMPLEMENTATION` defaulting to FastDDS while the Q5 publishes via CycloneDDS, leaving the topic discovery completely empty. Both fixed; the driver now talks to the robot end-to-end.

### Shipped
- **`praxis_robotera_q5` package scaffold** — seven-node ament_python driver against the Q5 device-id, registered in the Praxis backend
- **FSM-orchestration sequence at executor startup** — waits up to 5 s for `/ready_service`, calls it to drive `IDLE → READY`, waits up to 5 s for `/activate_service`, calls it to drive `READY → ACTIVE`. Graceful degradation if either service is unavailable: warns rather than fails, continues in passive mode publishing pose telemetry from `/wr1_base_drive_controller/odom`, `navigate_to_pose` returns "Q5 not in ACTIVE state"
- **`profiles/praxis_robotera_q5.yml`** — `pre_window` exports `ROS_DOMAIN_ID=211` and `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, plus the four standard `PRAXIS_*` environment variables and the two ROS sources
- **Operator runbook entry** — pre-flight steps document the SSH session (`developer@192.168.8.100:2222`), manual `/ready_service` call (or rely on the driver), the manual XOS-web `initpose_handsdown` trigger to set the arms into a driving posture, the `/activate_service` call, and the `sudo chmod 777 /dev/video*` one-shot per boot

### Technical Highlights
- **CycloneDDS vs FastDDS interop, the topic-list-is-empty bug.** Fresh shell on the host: `ros2 topic list` returned nothing despite the Q5 clearly being online and pingable. Root cause: `RMW_IMPLEMENTATION` was unset, defaulting to FastDDS; the Q5 publishes via CycloneDDS; the two implementations don't interoperate at the DDS discovery layer. Fix: `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` in the tmux `pre_window`. Documented as the *very first* environment requirement in the Q5 `CONTEXT.md` — gets you 0 % to 100 % of the topic visibility in one line.
- **FSM orchestration in the driver, not the operator's head.** Vendor exposes the `INIT → IDLE → READY → ACTIVE` state machine via `std_srvs/srv/Trigger` calls on `/ready_service` and `/activate_service`. Initial implementation assumed the operator had already advanced the FSM before bringing the driver up; in practice this caused "publishes `TwistStamped`, robot doesn't move" because the FSM was stuck in `READY (2)` rather than `ACTIVE (4)`. Solution: the executor advances the FSM itself on startup. Graceful degradation if either service is missing — driver still publishes pose telemetry, only command-side actions fail — so the driver remains useful even in a partially-broken hardware state.
- **Two distinct "publishes but doesn't move" failure modes in one robot.** The X2 had it (multi-source arbiter); the Q5 has both: (i) FSM not advanced past `READY`, (ii) DDS implementation mismatch silently hiding the topics. Same surface symptom, three distinct root causes across the fleet. Useful diagnostic check-list now reads: "if the publisher succeeds but the robot doesn't move, suspect in this order — DDS implementation, FSM state, arbiter registration, QoS profile."
- **Discovery diagnostic asymmetry, replayed.** Same diagnostic technique as A2 (June 11): when topic visibility differs between two processes on the same host, suspect environment-driven discovery layer first. On A2 that pointed at FastDDS profile + `ROS_LOCALHOST_ONLY`; here it points at `RMW_IMPLEMENTATION`. The pattern is the same: discovery is environment-controlled, asymmetric visibility implies environment divergence.

### Impact
- Q5 driver reaches the "talking to the robot" milestone in one day rather than the multi-day diagnosis the FSM-or-DDS class of bug usually takes for a new robot integration. Both root causes are now permanent entries in the team's debugging playbook.
- The graceful-degradation pattern (driver continues in passive mode when FSM transition fails) means operators can debug sensor-side issues without a fully-active robot — particularly valuable for Q5 because the FSM transitions sometimes fail on hardware faults that don't otherwise prevent telemetry.
- FSM-orchestration design becomes a reusable template — any future robot exposing a vendor state machine via services will use the same wait + call + verify + graceful-degrade sequence rather than relying on operator preflight.

### Academic Connections
- **Distributed systems.** DDS implementation interoperability: two compliant implementations of the same spec that nonetheless don't talk to each other in practice (vendor-specific multicast TTL, locator configuration, transport plugins); the cost of an under-specified interoperability contract. Environment-controlled discovery as a hidden configuration surface.
- **Control theory / state machines.** Vendor-exposed finite state machine over a service interface; mandatory state transitions before command authority; mealy-state semantics where the same input means different things in different states.
- **Software architecture.** Driver-owned FSM orchestration vs operator-owned preflight (pushing responsibility into the software for reproducibility); graceful degradation when downstream dependencies fail (passive telemetry mode); fail-loud-but-keep-running as a partial-failure policy.
- **Networking.** ROS 2 RMW layer abstraction: standardised at the API, polymorphic at the runtime; the cost of an abstraction that's transparent on success but opaque on cross-implementation failure.

- [ ] Obtain supervisor clearance for confidentiality before submitting

## Rolled up into

[[2026-W25]]

---
