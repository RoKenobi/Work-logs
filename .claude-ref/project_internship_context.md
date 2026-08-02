---
name: project-internship-context
description: "Rohan's internship at NCS Singapore — projects, robots, key dates, and work context for the work-logs vault"
metadata: 
  node_type: memory
  type: project
  originSessionId: 77d4051c-fc0a-4dcb-afea-67b08f77ffde
  modified: 2026-08-02T05:42:43.958Z
---

Rohan is a software/robotics engineering intern at NCS Singapore, working on the Praxis multi-robot orchestration platform. Internship started 2026-05-18.

**Why:** Physical AI Factory initiative at NCS — integrating heterogeneous robots onto a vendor-agnostic platform for agentic orchestration.

**How to apply:** Every log entry, rollup, and feature request happens in this context. The robots, the platform, and the events are the through-line.

## Robot fleet
- Unitree Go2 (quadruped) — integrated May/June
- Agibot A2 Ultra (humanoid) — integrated June Week 4
- Agibot X2 Ultra (bipedal humanoid, x4 units) — integrated June Week 4/5
- RobotEra Q5 (60V wheeled humanoid) — integrated June Week 5
- Hikvision IP camera (CCTV) — integrated June Week 7

## Key milestones
- May 18: internship starts, Q5 data collection begins
- Jun 4-5: Go2 end-to-end demo with ADK agents
- Jun 8-14: A2 + X2 Ultra drivers built
- Jun 15-19: Q5 driver + X2 TTS
- Jun 22-26: vLLM (Gemma 26B on Blackwell), impact_agent, Boss demo (fallen-boxes scenario, 2m 9.4s)
- Jun 29: Fleet dashboard (one-tap phone control), HK Vision CCTV driver
- Jun 30 – Jul 3: Network upgrade (TP-Link Omada migration), CEO sign-off on scenario, DFS channel fix
- Jul 6: NovaSonic speech-to-speech on Q5, event prep
- Jul 7-9: NCS Impact 2026 at MBS Level 5 — public demo, C-suite audience, conversational X2, all robots live

## Key projects
- `praxis_unitree_go2`, `praxis_agibot_a2_ultra`, `praxis_agibot_x2_ultra`, `praxis_robotera_q5`, `praxis_hk_vision` — robot drivers
- `local_llm` — vLLM Docker Compose stack, Gemma 26B on Blackwell GPU
- `impact_agent` — Google ADK + LiteLLM incident-response agent (21 tools, recipe-style prompt)
- `fleet-dashboard` — FastAPI phone-friendly web UI for one-tap Start/Kill/Set-Pose
- `CommanderAI` — public demo webpage with live robot status + natural-language command

## Colleagues
- Joe — teammate, worked on dynamic scenarios (bag detection, perimeter enforcement X2)

## Important dates (absolute)
- NCS Impact 2026 event: Jul 7-9, 2026 at MBS Level 5
- Internship anchor date: 2026-05-18 (Week 1 Day 1)
- Week naming: Mon-Sun calendar weeks off May 18 anchor
