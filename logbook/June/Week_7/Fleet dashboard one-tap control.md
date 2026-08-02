---
date: 2026-06-29
---

# Daily

## June 29, 2026

**Graph Nodes:** [[Praxis Platform]], [[Unitree Go2]], [[Agibot X2 Ultra]], [[RobotEra Q5]] · #Python #Docker #systemd #HTTP #tmuxinator #VendorAbstraction

**Theme:** [[Robotics Integration Infrastructure]]

### Summary
Shipped `fleet-dashboard` — a phone-friendly FastAPI web app hosted on the always-on server (`robotics-3gyc:9191`) that fans out one-tap **Start / Kill / Set-Pose** actions to all three Praxis robots in parallel over SSH + HTTP. Replaces the previous workflow of SSH-ing into three robots and manually running `praxis_start` aliases, plus a separate sequential bash script for the pose-set step. The operator can now walk around the demo room and trigger fleet actions from a phone.

### Shipped
- **`fleet-dashboard` FastAPI app** (`~/fleet-dashboard/app.py`, ~150 lines) — async-native, uvicorn-served on `0.0.0.0:9191`, bound to AP_MLO Wi-Fi (`192.168.123.181`). Three endpoints (`/start`, `/kill`, `/set-pose`) each fan out via `asyncio.gather()`; per-request wall-clock is `max(per_robot_latency)` not `sum`. Start completes ~3.4 s for three responsive robots.
- **Phone-friendly UI** — single Jinja2 template + vanilla JS, ~140 lines + ~5 KB CSS. Zero build step, no React/SPA scaffolding. Per-robot card shows `idle` / `running…` (pulsing dot) / `online · praxis started` / failure-mode strings.
- **SSH layer** — `sshpass + ssh -tt -o ConnectTimeout=5 -o LogLevel=ERROR <user>@<host> bash -ic 'cd ~/praxis_ws && tmuxinator start run --no-attach'`. `bash -ic` forces interactive shell so alias expansion works; `-tt` forces TTY allocation for tmuxinator; `--no-attach` so the SSH command returns instead of hanging on the new tmux session.
- **Multi-host probe for AgiBot X2** — `_pick_reachable_host()` accepts either string or list for a robot's `host` field; TCP-probes both candidates (`192.168.123.47` and `.48`) in parallel with 1.5 s timeout; dispatches SSH to whichever responds first. Sidesteps X2's floating DHCP lease without needing router admin.
- **Praxis API fan-out** — three `POST /orgs/{org_id}/actions/Set Pose/execute` calls via stdlib `urllib`, wrapped in `loop.run_in_executor()` with 10 s socket timeout. Each robot's recorded floor-plan pose is hard-coded in `ROBOTS[*]["pose"]`. 503 from praxis (when a robot's `tmuxinator` stack hasn't yet started publishing `robot_status`) surfaces verbatim on the card so the operator knows to wait ~10 s after Start.
- **`systemd` unit** at `/etc/systemd/system/fleet-dashboard.service` — `Type=simple`, `Restart=on-failure, RestartSec=3`, `After=network-online.target`. Auto-starts on boot, auto-restarts within 3 s on failure, survives terminal close.
- **Cross-subnet Q5 reachability** — Q5 physically at `192.168.8.100:2222` behind GL-MT3000 router; reached from server via port-forward `TCP 2222 → 192.168.8.100:2222` on the router's WAN IP `192.168.123.166`. Chose port-forward over server-side static route (`ip route add 192.168.8.0/24 via ...`) for faster verification in the router UI.

### Technical Highlights
- **`praxis_start` was an alias, not a script — and that fact cascaded into five distinct fixes.** Diagnosis chain: (1) `ls ~/praxis_ws/praxis_start*` → not found; (2) `grep "praxis_start" ~/.bashrc` → `alias praxis_start="tmuxinator start run"`; (3) calling `tmuxinator start run` directly failed because the alias-target relied on `TMUXINATOR_CONFIG` set in `.bashrc`; (4) `bash -ic '...'` forced `.bashrc` to load past its `[ -z "$PS1" ] && return` guard (login shells via `-lc` wouldn't have worked — `bash -lc` doesn't set `$PS1` either); (5) tmuxinator then complained `open terminal failed: not a terminal`, fixed by adding `-tt` to `ssh`; (6) tmuxinator attached to the new session by default, blocking the SSH call indefinitely — appended `--no-attach`. Five hidden environment dependencies, each broken differently, discovered in sequence. The lesson: convenience aliases hide cascading invariants, and you peel them one symptom at a time.
- **`asyncio.gather()` as the throughput lever for I/O-bound fan-out.** Three independent SSH calls + three independent HTTP calls, all I/O-bound. Sequential dispatch is ~3 × wall-clock; `gather` makes it `max(per_robot)`. The synchronous `urllib` POST is wrapped in `loop.run_in_executor(None, ...)` so it doesn't block the event loop — the cheapest way to bridge sync stdlib HTTP into the async handler without pulling in `httpx`.
- **`StrictHostKeyChecking=no` + `UserKnownHostsFile=/dev/null`** on every SSH call. Deliberate for a demo-context LAN-only dashboard; documented in §7 of the report as a security trade-off. If the dashboard ever leaves AP_MLO, three changes are mandatory: secrets to `.env` with `chmod 600`, HTTP basic auth (or Tailscale ACLs), SSH key auth instead of `sshpass`.
- **Stale uvicorn vs systemd race.** When the systemd unit was installed (`sudo systemctl enable --now fleet-dashboard`), the manually-launched uvicorn from earlier in the session was still holding port 9191. systemd's uvicorn went into `activating` (retrying) instead of `active`, with no error in `journalctl -u fleet-dashboard`. Fix: `pkill -f "uvicorn app:app"` then `systemctl restart`. Documented because the symptom isn't self-explanatory.
- **Status-line semantics over raw output.** Initial design showed `tail = out.splitlines()[-1]` as the user-visible status, which sometimes surfaced locale warnings (`bash: warning: setlocale: LC_ALL: cannot change locale`) instead of useful state. Replaced with a verb-mapped semantic string (`online · praxis started` / `online · praxis stopped` / `online · pose set`). Server response stays a uniform `{key, name, ok, rc, output}` per robot; the JS does the verb mapping.
- **The 503 caveat as a feature, not a bug.** Praxis's `Set Pose` returns `503 "Robot 'X' is not available (no robot_status published in last 2 seconds)"` if the robot's stack isn't running. The dashboard surfaces this verbatim on the card, encoding the operator workflow: **Start → wait ~10 s → Set Pose**. The 503 is the contract; we propagate it instead of masking it.

### Impact
- **Operator UX inverted.** Demo runs no longer require an open laptop with three SSH sessions. The operator walks around the room and triggers Start / Kill / Set-Pose from a phone bookmark — `http://192.168.123.181:9191`. Three taps replace three terminal commands × three robots.
- **Three robots × three actions = nine operations now collapsed into three buttons.** Each button does the right thing per-robot via the heterogeneous SSH + HTTP fan-out underneath. Same Praxis device IDs, same floor-plan poses, same `tmuxinator` profile names per-robot — uniform interface on top, vendor-specific plumbing underneath. Validates the same vendor-abstraction pattern that drives the Praxis SDK design.
- **Crash + reboot survival baked in.** `systemd Restart=on-failure, RestartSec=3` plus `restart: unless-stopped` semantics across the stack means the dashboard self-heals from process crashes and host reboots without operator intervention. Day-N operations are limited to `docker compose logs -f` / `systemctl restart fleet-dashboard` when iterating on code.
- **The five-step `praxis_start` saga is documented.** Anyone onboarding a new robot to the dashboard gets the bash-ic + `-tt` + `--no-attach` invocation as a contract from the report's §4.2. Saves an hour of cascade-debugging per new robot.

### Academic Connections
- **Distributed systems / concurrency.** `asyncio.gather()` as fan-out concurrency for I/O-bound work; `loop.run_in_executor()` as the bridge between sync and async at process boundaries; multi-host probing with bounded parallelism as a graceful-degradation pattern under DHCP uncertainty.
- **Networking.** Cross-subnet reachability via TCP port-forward vs server-side static route; the trade-off between "no server-side config" and "preserve original addressing." Host-mode Docker networking vs NAT for LAN services.
- **Operating systems.** Bash startup semantics — interactive (`-i`) vs login (`-l`), `$PS1` guard in `.bashrc`, the cascade from "alias not expanded" through "no `TMUXINATOR_CONFIG`" through "no TTY" through "blocking attach"; `systemd` lifecycle (`activating` vs `active`, `Restart=on-failure`); `network-online.target` ordering for late-starting services.
- **Software architecture.** Uniform response shape (`{key, name, ok, rc, output}`) over heterogeneous backends (SSH return code vs HTTP status); semantic-status mapping at the UI layer to decouple operator-visible state from raw subprocess output; vendor-abstraction at the dashboard layer mirroring the same abstraction at the Praxis SDK layer.
- **Security engineering.** Threat-model-justified shortcuts — `StrictHostKeyChecking=no`, in-source secrets, no auth — appropriate for a trusted LAN demo, with an explicit "mandatory changes if reach expands" checklist that documents the migration path off each shortcut.

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
