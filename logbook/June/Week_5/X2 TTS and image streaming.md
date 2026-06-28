---
date: 2026-06-15
---

# Daily

## June 15, 2026

**Graph Nodes:** [[Agibot X2 Ultra]], [[Praxis Platform]], [[AIMDK]] · #ROS2 #FFmpeg #OpenCV #MediaMTX #Docker #tmuxinator #MQTT #H264 #MultithreadedExecutor #VendorAbstraction

**Theme:** [[Robotics Integration Infrastructure]] (5 shared) · [[ROS 2 Robotics Middleware]] (4 shared) · [[Video Streaming Infrastructure]] (4 shared)

### Summary
Closed out X2 integration with a Praxis `tts` action executor (volume-set + play-with-priority chain) and a `sensor_msgs/Image` topic-based video streamer that's the cleanest of the three driver implementations — no V4L2, no GStreamer, just `cv_bridge` and FFmpeg. Cherry on top: tracked down why image frames were dropping under joint-state load to the single-threaded executor pinch point, fixed it the same way as yesterday's pose executor.

### Shipped
- **`tts_executor.py`** — standalone Praxis `tts` action handler, chains `aimdk_msgs/srv/SetVolume` then `aimdk_msgs/srv/PlayTts` with priority levels mapped from Praxis input to AIMDK `TtsPriorityLevel` (1=BACKGROUND … 10=SAFETY, default 6=INTERACTION), reports success/failure through the action context
- **`video_streamer.py`** — subscribes `/aima/hal/sensor/stereo_head_front_left/rgb_image` (`sensor_msgs/Image`), converts each frame to OpenCV BGR via `cv_bridge`, FFmpeg `libx264 fast` → MediaMTX, co-publishes `camera_info` at 0.2 Hz
- **`MultiThreadedExecutor` rollout to all sensor-heavy nodes** — sensor subscriptions on a `ReentrantCallbackGroup`, timer-driven publishers on a separate group, eliminated frame-drop pinch points across the driver
- **Five-pane production tmuxinator profile** — `robot_status_publisher`, `joint_states_publisher`, `translate_and_rotate_executor`, `video_streamer`, `tts_executor`; `velocity_publisher` commented out to avoid contending with the executor for `/aima/mc/locomotion/velocity` ownership

### Technical Highlights
- **URL-encoded service namespace gotcha.** `client.wait_for_service('/aimdk_msgs/srv/SetVolume')` timed out, yet `ros2 service list` showed the service was up. AIMDK registers services under the percent-encoded form: `/aimdk_5Fmsgs/srv/SetVolume` (the `_5F` is URL-encoded underscore). The encoded form is what's discoverable on the bus; strict lookups by the unencoded name fail silently. The TTS executor uses the encoded path; documented in `CONTEXT.md` so the next engineer doesn't lose an afternoon to it.
- **Image-topic streaming as the cleanest video path.** The X2 publishes its head camera as a ROS 2 `sensor_msgs/Image` topic rather than a V4L2 device. Pipeline: `Subscription → cv_bridge → OpenCV BGR → FFmpeg → MediaMTX`. No V4L2 contention, no GStreamer multicast group management, no first-N-frames warm-up dance. The vendor has already done the device decode upstream; the driver only needs to re-encode and forward.
- **Single-threaded executor as a hidden frame-drop pinch point.** Under joint-state load (four `JointStateArray` topics at 50 Hz source rate), `rclpy`'s default single-threaded executor was serialising the image callback behind the joint deserialisations. The image queue would grow, the SDK would drop older frames, and the RTSP stream would stutter at 5–8 fps. `MultiThreadedExecutor` + `ReentrantCallbackGroup` for sensor callbacks → image throughput returned to source rate with zero drops. Same pattern as yesterday's pose executor — confirms the rule for sensor-heavy driver nodes.
- **Priority-as-first-class-parameter for shared interaction surfaces.** TTS contention is inevitable in a fleet where multiple agents (`robot_agent`, `concierge_agent`, `audio_agent`) might speak through the same physical speaker. The AIMDK `TtsPriorityLevel` (10 levels, `SAFETY` at the top) is propagated end-to-end: Praxis `tts` action payload carries a priority, the executor passes it through to `PlayTts`, AIMDK arbitrates if multiple plays are queued. The platform's job is to expose the parameter; the runtime's job is to arbitrate.

### Impact
- X2 is now a fully integrated Praxis robot — PMU, whole-body joint state, pose, head-camera video stream live; `set_pose`, `navigate_to_pose`, `tts` actions accepted; the entire driver stack starts with a two-line `pre_window` plus `praxis_start`.
- The third distinct video pipeline implementation in the fleet (Go2: H.264 multicast, A2: V4L2 GMSL, X2: ROS image topic) all land in MediaMTX through the same FFmpeg envelope. The codec path is the constant; the source half varies entirely.
- TTS as a Praxis action makes the X2 + A2 stack independently usable by the `concierge_agent` for end-to-end guided-tour demos — the agent issues `tts("welcome")` → `motion_replay("wave")` → `navigate_to_pose(target)` → `tts("this way please")` without any humanoid-specific code on its side.
- The `MultiThreadedExecutor` + `ReentrantCallbackGroup` pattern is now the default for any future driver node with sensor subscriptions. Single-threaded execution is reserved for trivially-low-throughput nodes only.

### Academic Connections
- **Distributed systems.** Priority-based arbitration of a shared physical resource (the speaker); URL-encoding as a discovery namespace transformation (a footgun-class undocumented behavior); request-response chaining as a service composition pattern (SetVolume → PlayTts).
- **Computer vision / media.** ROS image topic vs V4L2 device vs H.264 multicast as three points on the "where does decode happen" spectrum; `cv_bridge` as the BGR/RGB/CHW format conversion layer; FFmpeg as the unifying re-encode-and-publish substrate.
- **Concurrency.** Multi-threaded executor as a precondition for sensor-heavy node throughput; `ReentrantCallbackGroup` separation of inflow from outflow; head-of-line blocking in single-threaded callback queues.
- **Software architecture.** End-to-end propagation of priority through the API stack (Praxis schema → driver → AIMDK runtime); the vendor-decode-upstream pattern as the simplest possible video source.

- [ ] Obtain supervisor clearance for confidentiality before submitting

## Rolled up into

[[Agibot X2 and RobotEra Q5 Integration]]

---
