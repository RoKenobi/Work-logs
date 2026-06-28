---
date: 2026-05-22
---

# Daily

## May 22, 2026

**Graph Nodes:** [[RobotEra Q5]] · #ROS2 #MultithreadedExecutor #V4L2 #DeadReckoning

**Theme:** [[ROS 2 Robotics Middleware]] (4 shared)

### Tasks Completed
- Successfully captured first synchronized dataset from RobotEra Q5 robot after resolving non-standard ROS2 topic discovery
- Implemented multi-threaded data acquisition node using `rclpy` and `MultiThreadedExecutor` to collect MJPEG images from `/dev/video0`, TF2 transforms (nav_odom → nav_base), and timestamped pose data
- Exported first complete trajectory with robot translation, orientation quaternions, and image file paths to CSV format

### Blockers & Challenges
- RobotEra Q5 used completely different ROS2 topic names and message types compared to standard conventions, making initial discovery difficult
- Required coordination with robot developers in China to identify correct topics for camera and SLAM data
- Had to reverse-engineer navigation and calibration topics independently through manual `ros2 topic echo` exploration

### Resolutions & Outcomes
- Collaborated with Chinese developers via remote communication to map camera (`/dev/video0` via v4l2-ctl) and SLAM topics
- Systematically echoed ROS2 topics until finding correct outputs for navigation and localization data
- Successfully logged first complete robot trajectory with synchronized perception and odometry data ready for AWS upload

### Academic Connections
- **Concurrent Programming**: Multi-threaded executor pattern for simultaneous sensor data collection without blocking
- **Coordinate Systems & Transforms**: TF2 buffer queries for frame transformations (nav_odom → nav_base)
- **Time Synchronization**: ROS time stamping for synchronized multi-modal sensor data collection

---

## Rolled up into

[[Unitree Go2 ROS 2 Integration]]
