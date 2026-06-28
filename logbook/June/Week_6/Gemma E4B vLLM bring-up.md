---
date: 2026-06-22
---

# Daily

## June 22, 2026

**Graph Nodes:** [[Praxis Platform]], [[Jetson Orin]] · #vLLM #Gemma #Docker #HuggingFace #OpenAIcompatibleAPI #PagedAttention #ContinuousBatching

**Theme:** [[Robotics Integration Infrastructure]] (7 shared)

### Summary
Stood up the `local_llm` project — a self-hosted vLLM deployment on the workstation GPU serving Gemma 4 over an OpenAI-compatible HTTP API, driven by Docker Compose + a `Makefile` of per-model presets. First attempt was Gemma-E4B (the 4-billion-parameter "small" SKU); model loaded and served correctly but output quality on the agent workloads was visibly weaker than we needed for the upcoming Praxis incident-response agent. Set up the foundation today; tomorrow's job is to size and load the bigger variant.

### Shipped
- **`local_llm` repo** — `gemma_4_26B.yml` Compose template parameterised by env vars (`MODEL_ID`, `PORT`, `CONTAINER_NAME`, `MAX_MODEL_LEN`, `GPU_MEMORY_UTILIZATION`, `TENSOR_PARALLEL_SIZE`, `VLLM_API_KEY`, `VLLM_EXTRA_ARGS`, `HF_TOKEN`, `HF_CACHE`, `VLLM_IMAGE`) so every preset reuses the same compose file
- **`Makefile` of presets** — one target per model SKU; each `make <preset>` launches as a distinct Compose project (`-p <name>`) so multiple models can coexist on different host ports sharing the GPU
- **Shared HuggingFace cache** — `~/.cache/huggingface` bind-mounted into every container at `/root/.cache/huggingface`. Weights download once on first run, every subsequent launch (or container recreate, or reboot) is a cache hit
- **`gemma-e4b` preset** running on `:9090 → 8000`, image `vllm/vllm-openai:v0.21.0` pinned (not `latest` — silent ABI drift bait), `restart: unless-stopped` so it survives reboots
- **OpenAI-compatible HTTP API live** — `/v1/chat/completions`, `/v1/completions`, `/v1/models` all responding. Any client speaking the OpenAI SDK works against `http://localhost:9090/v1` with a `base_url` swap
- **`make check`** preflight script verifying Docker Compose, NVIDIA driver, NVIDIA Container Toolkit, free disk, and HF token presence before any preset spins up

### Technical Highlights
- **vLLM as the runtime, not the model.** Naive `transformers.generate()` allocates a contiguous KV slab per request sized to the worst-case `MAX_MODEL_LEN`. vLLM borrows OS-style **PagedAttention** — KV cache split into fixed-size 16-token blocks, allocated lazily, with a per-sequence block table. Sequences only use the VRAM they actually need; fragmentation collapses; the GPU holds many more concurrent requests for the same memory budget. This is the headline reason to host vLLM over rolling your own server.
- **Continuous batching closes the throughput gap.** Static batching forces every request to wait on the slowest in its batch. vLLM schedules at the *token* level — once any sequence emits `<eos>`, its slot frees mid-forward-pass and a queued request takes its place. Throughput scales near-linearly with concurrency until VRAM saturates.
- **OpenAI-compatible API is the integration lever.** vLLM ships a FastAPI server (`vllm.entrypoints.openai.api_server`) that implements Chat Completions, Completions, Embeddings, and Models. LangChain, LlamaIndex, the `openai` SDK, ADK via LiteLLM — all of them work against a local vLLM with a single base-URL swap. We can host LLMs in-house without rewriting any client code.
- **Pin the image, mount the cache, gate the port.** Three engineering decisions every self-hosted LLM deployment needs: (i) pin `vllm-openai:v0.21.0` not `latest` so rebuilds are byte-stable; (ii) mount the HF cache on the *host* so weights survive container recreates; (iii) set `VLLM_API_KEY` so requests require `Authorization: Bearer <key>` — vLLM ships with **no auth by default** and that's unsafe anywhere reachable from the network.
- **Why self-host when hosted APIs exist.** Five reasons live in the README: data residency (prompts never leave the host), cost stability (fixed power + amortization vs variable per-token billing), latency floor (no ~50–150 ms public-internet round-trip), model choice (Gemma / Llama / Qwen / Mistral / quantized variants of all of them), and no silent model drift (a pinned model + pinned image is reproducible for evaluation harnesses). The honest trade-off is operational complexity — drivers, container toolkit, VRAM sizing, license acceptance, scaling beyond one GPU — which this repo exists to make tractable.
- **E4B quality ceiling on agent workloads.** The 4B-active-parameter Gemma SKU loads and serves cleanly, but on the Praxis incident-response prompt structure it consistently failed to do parallel tool calls, missed mandatory post-`video_reasoning` updates, and swapped robot roles. The smaller model can't carry a 200-line recipe-style prompt without regressing on basic discovery. That diagnosis is what justifies moving to a larger variant tomorrow.

### Impact
- Project unblocks the upcoming `impact_agent` build — the agent needs an OpenAI-compatible endpoint to point LiteLLM at, and we now have one. ADK + LiteLLM will configure with `OPENAI_API_BASE=http://localhost:9090/v1`.
- One-command bring-up (`make gemma-e4b`) for any teammate to stand up the same model on their box. The Makefile + Compose template means adding a new model is a ~5-line block in the Makefile's Favorites section, not a fresh deploy.
- Cost trajectory diverges from Bedrock from day one — every token served locally is a token not billed by AWS, and the workstation GPU has fixed amortized cost.
- E4B's failure on the agent workload is itself a useful result: it pins down the *minimum* model size that handles recipe-style multi-step prompts, justifying the bigger spend on the 26B variant tomorrow.

### Academic Connections
- **Operating systems / virtual memory.** PagedAttention is OS paging applied to KV cache — page tables, per-sequence block lists, lazy allocation, copy-on-write for prompt prefix reuse. Direct analogue.
- **Systems / scheduling.** Continuous batching as token-level preemption: a sequence's `<eos>` is a yield point, the scheduler immediately admits a queued request into the freed slot. Token-granularity scheduling vs request-granularity is the same kind of optimisation as page-fault-driven context switches.
- **Distributed systems.** OpenAI-compatible REST as a vendor-neutral interface contract — the value is in the schema everyone agrees on, not the original provider. Once the interface is the protocol, swapping the implementation behind it (Bedrock → vLLM) is a config change.
- **Containers / packaging.** Image pinning + bind-mount for ephemeral container layers + persistent state on host. Pattern reusable for any "stateful workload in stateless container" deployment.
- **Operational engineering.** Pre-flight verification (`make check`) as a fail-fast at the substrate boundary — the same pattern as the A2 systemd-wrapper preflight from week 4.

- [ ] Obtain supervisor clearance for confidentiality before submitting

---
