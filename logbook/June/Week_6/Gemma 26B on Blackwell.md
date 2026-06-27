---
aliases:
  - 23-06-26
  - 2026-06-23
---

# Daily

## June 23, 2026

**Graph Nodes:** [[Praxis Platform]], [[Jetson Orin]] · #vLLM #Gemma #Docker #HuggingFace #OpenAIcompatibleAPI #ToolCalling #PagedAttention

**Theme:** [[Robotics Integration Infrastructure]] (7 shared)

### Summary
Switched off Gemma-E4B onto the Gemma-4-26B-A4B-it variant — the bigger SKU we actually needed for the upcoming `impact_agent`. Found the headroom on the workstation Blackwell GPU, hit and resolved the **CUDA Error 803** Blackwell driver footgun at startup, wired up the tool-call parser, and got the 26B model serving with healthy `/health` 200 responses on `:9090`. The OpenAI-compatible endpoint is now the canonical local-LLM target the Praxis agents service will point at.

### Shipped
- **`gemma-e4b` preset replaced by 26B** — same Compose template, new env values: `MODEL_ID=google/gemma-4-26B-A4B-it`, sized `MAX_MODEL_LEN` and `GPU_MEMORY_UTILIZATION` to fit on a single Blackwell card without OOM on KV
- **Blackwell `LD_LIBRARY_PATH` override** baked into compose — putting `/lib/x86_64-linux-gnu:/usr/local/nvidia/lib64:/usr/local/cuda/lib64` *first* so the loader picks up the host `libcuda.so.1` ahead of vLLM's stale `cuda-compat` shim. Harmless on older drivers, required on this box
- **Tool-call parser flags** — `--enable-auto-tool-choice --tool-call-parser gemma4` passed through `VLLM_EXTRA_ARGS`. Without these, the model still chats but returns tool calls as plain text instead of structured `tool_calls` JSON
- **API-key gate** — `make gen-api-key` script that prints a strong key to stdout (never writes to disk); copied into `.env` as `VLLM_API_KEY`. Every request now requires `Authorization: Bearer <key>`
- **Health-check pattern** documented — `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:9090/health` polls until 200. `docker ps` shows "running" the instant Python imports; the container isn't actually serving until CUDA graphs compile (~30–90 s). Critical for automation
- **`README.md` runbook** with first-time setup, day-to-day commands, the common failure-modes table, and the explicit non-goals (no reverse proxy / TLS, no LB, no metrics export, no model swapping, no multi-node TP)

### Technical Highlights
- **CUDA Error 803 at startup, root cause.** The `vllm/vllm-openai` image ships a `cuda-compat` layer with a `libcuda.so.1` built for drivers `< 571`. Our host runs driver **580** (CUDA 13.0). The compat lib was intended to let *newer* CUDA code run on *older* drivers — but here the host driver is **newer** than the compat lib expects, so the stale lib *shadows* the real one and the loader resolves to it first. Fix is the `LD_LIBRARY_PATH` env in compose that pins host library paths in front of the image's compat path. Whole class of failure mode I'd never have predicted from the symptom — Error 803 sounds like a GPU problem, was actually a linker path problem.
- **The two Blackwell failure modes look similar but aren't.** Error 803 is a *startup* failure caused by the cuda-compat shadow. "no kernel image is available for execution on the device" is a *runtime* failure caused by the vLLM/PyTorch build not having `sm_120` kernels compiled in. Same Blackwell card, two distinct diagnoses, two distinct fixes. Documented both in the failure-modes table so the next person reaches for the right lever.
- **GPU sizing for 26B at bf16.** Weights at bf16 cost roughly 2 GB per billion parameters → 52 GB for the 26B model. The Blackwell card has enough headroom for that plus KV cache as long as `MAX_MODEL_LEN` is reasonable (32K context default). If we ever stack a second model on this GPU, the rule is `Σ GPU_MEMORY_UTILIZATION ≤ 1.0` across all containers and we drop `MAX_MODEL_LEN` to free KV. vLLM autodetects quantization from the HF repo — no flag needed — so if 26B ever stops fitting we just pick the upstream FP8 variant.
- **Continuous batching pays off most on bursty agent workloads.** The `impact_agent` flow issues 26+ tool calls per incident in tight bursts; static batching would serialise them behind the slowest in-flight forward pass. With vLLM, each tool-call completion frees its KV slot at `<eos>` and the next request slides in mid-batch. That's why a 26B local model can compete with hosted APIs on wall-clock for this workload — the throughput floor is high.
- **Tool calling needs an explicit parser, model by model.** vLLM doesn't auto-parse tool calls; you have to pick the right parser plugin per model family. `--tool-call-parser gemma4` for Gemma 4; Qwen, Llama, Mistral each need their own. Without it, the model still happily emits tool calls but they're wrapped in prose and the client never sees a structured `tool_calls` field. Easy to miss until you wire the agent up and wonder why it's "talking about" using tools instead of using them.
- **Image pinning > restart policy.** `restart: unless-stopped` brings every running model back on reboot, but the value of pinning the image to `v0.21.0` is bigger — `latest` silently changes on rebuild and can break model support or kernel ABI. The pin is the byte-stability guarantee; the restart policy is just availability.

### Impact
- Local Gemma-26B endpoint is live and the `impact_agent` build can start immediately tomorrow with `OPENAI_API_BASE=http://localhost:9090/v1`. No further blockers on the inference side.
- One-line fix (the `LD_LIBRARY_PATH` override) saves the next engineer onboarding a Blackwell host hours of misdiagnosis. The failure-modes table in the runbook is the institutional memory of every gotcha we hit today.
- Cost trajectory now real: every token served against the local 26B is a token not billed to Bedrock. The break-even calculation is straightforward — hosted Claude Sonnet vs amortized workstation GPU power — and the *predictability* is the bigger win than the raw cost, since a runaway loop calling `/v1/chat/completions` no longer generates a bill.
- 26B handling the recipe-style prompts cleanly (verified during initial smoke tests) — we can actually drive the multi-step incident-response playbook on a local model. The size jump from 4B was the right call.

### Academic Connections
- **Systems / linker semantics.** The `LD_LIBRARY_PATH` resolution order is `LD_LIBRARY_PATH` paths in order, then `/etc/ld.so.cache`, then standard system paths. Putting host paths first defeats library shadowing by the cuda-compat layer. Classic Unix dynamic-linker priority semantics.
- **Operating systems.** Continuous batching as preemptive scheduling at sub-request granularity — same principle as a kernel preempting on a tick boundary rather than waiting for the task to yield.
- **Computer architecture.** GPU memory hierarchy and the KV-cache-vs-weights trade-off — bf16 weights pin a fixed cost, KV cache scales with `MAX_MODEL_LEN × batch_size × num_layers`, and `GPU_MEMORY_UTILIZATION` is a soft VRAM cap that the scheduler respects by limiting batch concurrency.
- **Distributed systems.** Tool-call parsing as a vendor-specific deserialisation layer over a vendor-neutral wire format (OpenAI's `tool_calls` field) — same shape as parsing JSON-RPC over HTTP with a vendor-specific envelope, which is exactly what the A2 driver does for AIMDK.
- **Software engineering.** Failure-mode taxonomy in the runbook (Error 803 vs "no kernel image" vs OOM vs auth 401 vs port collision) as a forcing function for the next engineer to *read* before debugging. Documented symptoms → causes → fixes beats raw stack traces.

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
