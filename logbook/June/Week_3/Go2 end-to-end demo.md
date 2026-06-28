---
date: 2026-06-04
---

# Daily

## June 04, 2026

**Graph Nodes:** [[Unitree Go2]], [[Praxis Platform]], [[Praxis SDK]] · #GoogleADK #MQTT #RTSP #Pydantic #AWSBedrock #Docker #tmuxinator #VendorAbstraction #ROSTopic

**Theme:** [[Robotics Integration Infrastructure]] (10 shared)

### Tasks Completed
- Achieved successful end-to-end integration demonstration of Unitree Go2 with Praxis multi-robot platform
- Demonstrated natural language control via Google ADK conversational agents: commanded robot to navigate specific distances, capture photos, stream live video, set poses, and report battery status
- Validated complete data flow: MQTT telemetry (pose at 1Hz, joint states at 10Hz, status at 0.5Hz), RTSP video (15fps), and bidirectional action execution (set_pose, navigate_to_pose)

### Blockers & Challenges
- Integration required coordinating six runtime nodes (translate_and_rotate_executor, pose_publisher, joint_states_publisher, robot_status_publisher, video_streamer, camera_info_publisher) with correct environment sourcing and tmuxinator orchestration
- Needed to validate 3cm linear and 4.6° angular navigation tolerances met platform requirements
- First attempt at LLM-driven robot control required ensuring Praxis SDK schemas correctly exposed actions as tool-callable functions

### Resolutions & Outcomes
- Joe provided step-by-step guidance through integration process, helping resolve every problem along the way
- Successfully demonstrated vendor-agnostic control: Google ADK agent selected Go2 by capability, invoked navigate_to_pose, streamed progress feedback — all without knowing robot was quadruped
- Deployment workflow reduced to single `praxis_start` alias launching all six nodes in organized tmux session
- Validated driver architecture as reusable template for future robot onboarding (Agibot, additional RobotEra units)

### Academic Connections
- **Software Architecture**: Vendor abstraction layers; platform-agnostic interface design; publisher-executor separation of concerns; dependency injection patterns
- **AI/LLM Integration**: Schema-typed actions (Pydantic models) as LLM tool functions; understanding how structured APIs enable conversational robot control; ADK/Bedrock agent orchestration
- **Systems Integration**: Multi-service Docker Compose orchestration; MQTT pub/sub + RTSP streaming hybrid architecture; environment-driven configuration management; idempotent deployment scripts

---

## Rolled up into

[[Unitree Go2 ROS 2 Integration]]
