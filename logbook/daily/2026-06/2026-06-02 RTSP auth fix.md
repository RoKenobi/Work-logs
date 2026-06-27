---
aliases:
  - 2026-06-02
---

# Daily

## June 02, 2026

### Tasks Completed
- Debugged and resolved RTSP video streaming authentication failures preventing live camera feed from reaching Praxis dashboard
- Investigated MediaMTX configuration and Docker networking to identify container-localhost mismatch
- Reconfigured authHTTPAddress to use host LAN IP and validated RTSP webhook authentication flow

### Blockers & Challenges
- Video streamer connected to MediaMTX successfully, first second of H.264 stream rendered, then connection abruptly closed with HTTP 401 Unauthorized
- Initial mediamtx.yml shipped with `authHTTPAddress: http://praxis-api:8000/rtsp-auth/webhook` which resolved inside Docker network but pointed to wrong localhost context
- Required learning Docker networking fundamentals, container DNS resolution, and host-to-container communication patterns — networking concepts not previously mastered

### Resolutions & Outcomes
- Changed authHTTPAddress to host's LAN IP address instead of container hostname
- Ensured Praxis backend bound to 0.0.0.0:8000 (all interfaces) rather than 127.0.0.1
- Successfully established authenticated RTSP stream with 250-400ms latency, enabling live robot camera feed in dashboard

### Academic Connections
- **Computer Networks**: Container networking vs host networking; Docker bridge networks and DNS resolution; localhost semantics in containerized environments
- **Distributed Systems**: Webhook-based authentication patterns; HTTP callback flows for access control; out-of-band data planes (RTSP video separate from MQTT control)
- **Security**: Authentication token validation; JWT-based API authorization; per-stream credential gating

---

## Rolled up into

[[2026-W26]]
