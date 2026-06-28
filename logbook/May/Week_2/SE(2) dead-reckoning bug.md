---
date: 2026-05-30
---

# Daily

## May 30, 2026

**Graph Nodes:** [[Unitree Go2]] · #SE2Composition #DeadReckoning

### Tasks Completed
- Diagnosed critical 90° pose rotation bug in dead-reckoning implementation for Unitree Go2
- Identified root cause: initial pose_manager.py treated map-frame offset as scalar addition, ignoring relative rotation between robot's odom frame and operator-set map frame
- Worked with teammate Joe to understand correct SE(2) composition mathematics

### Blockers & Challenges
- Operator set robot pose to (3.7, 1.17) in dashboard, drove robot 3.7m forward (physically south), but dashboard updated to (7.21, 1.17) — a 90° rotation of expected (3.7, -2.53)
- Initial assumption that pose addition was simple arithmetic proved incorrect
- Debugging required understanding Lie group theory and rigid body transformations beyond typical robotics coursework

### Resolutions & Outcomes
- Joe guided through correct SE(2) frame composition: snapshot (initial_odom_x, initial_odom_y, frame_rotation) on set_pose, then compute delta_odom = current - initial, rotate by frame_rotation, then apply offset
- Implemented corrected logic in utils/pose_manager.py and utils/dead_reckoning.py with dedicated unit tests
- Documented lesson learned: "addition of poses" is SE(2) composition, not scalar arithmetic — forgetting rotation is a category error

### Academic Connections
- **Robotics Mathematics**: SE(2) special Euclidean group for 2D rigid transformations; understanding pose composition as matrix multiplication rather than vector addition
- **Linear Algebra**: Rotation matrix application R(θ) · v for transforming velocity vectors between reference frames
- **Debugging Methodology**: Root cause analysis through systematic hypothesis testing; unit test development for mathematical primitives

---

## Rolled up into

[[Unitree Go2 ROS 2 Integration]]
