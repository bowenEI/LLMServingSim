# Source Evidence Ledger

## Analysis Baseline

- Repository: `/home/foo/repos/LLMServingSim`
- Branch: `main`
- Revision: `725ef79d6961`
- ASTRA-Sim submodule: `d3469945c50410cac2e727c9ab627670c965db2a`
- Chakra submodule: `30221ab8bfd9212aa9c063cd0b14a7d0a2ea6dd7`
- Analysis includes the visible checkout. Existing untracked `.agents/` and `skills-lock.json` were not modified.

## Control Flow

| Claim | Primary source | Supporting source | Confidence |
|---|---|---|---|
| The Python frontend reads an ASTRA-Sim completion, updates `current`, routes arrivals, completes the prior batch, schedules, generates a graph, and returns a workload path. | `serving/__main__.py#L661-L983` (`main`) | `serving/core/controller.py#L22-L71` | high |
| Scheduler phase A serves running requests and may preempt from the tail; phase B admits waiting requests only if phase A did not preempt. | `serving/core/scheduler.py#L90-L236` (`Scheduler.schedule`) | `serving/core/scheduler.py#L252-L270` | high |
| Scheduled tokens are advanced at schedule time and captured in `Batch.scheduled_tokens`. | `serving/core/scheduler.py#L272-L338` (`_build_batch`) | `serving/core/request.py` | high |
| Trace rows are converted in process to Chakra ET graphs. | `serving/core/graph_generator.py#L138-L187` (`generate_graph`) | `astra-sim/extern/graph_frontend/chakra/src/converter/llm_converter.py#L145-L190` | high |
| ASTRA-Sim dispatches ready ET nodes to compute, memory, or communication backends. | `astra-sim/astra-sim/workload/Workload.cc#L115-L190` (`Workload::issue`) | `Workload.cc#L202-L390` | high |

## Compute Latency

| Formula / behavior | Source evidence | Notes |
|---|---|---|
| `latency_ns = round(time_us * 1000)` | `serving/core/trace_generator.py#L255-L266` (`_read_category_csv`) | CSV stores microseconds; ET runtime is treated as nanoseconds in this fork. |
| `t(x)=t0+(x-x0)(t1-t0)/(x1-x0)` | `serving/core/trace_generator.py#L439-L468` | Used for dense and per-sequence lookup; upper-bound queries extrapolate. |
| Attention uses four axes `(prefill_chunk, kv_prefill, n_decode, kv_decode)` and linear interpolation on each axis. | `serving/core/trace_generator.py#L571-L639`, `#L827-L861` | Despite a stale docstring at `#L827`, `_axis_bracket` and implementation use linear-axis interpolation. |
| `t_skew=t_mean+alpha(t_max-t_mean)` | `serving/core/trace_generator.py#L780-L824` | `alpha` is selected from profile metadata. |
| `alpha_hat=sum(dtm*dts)/sum(dtm^2)` | `profiler/core/fit_alpha.py#L268-L350` | Per-bucket weighted least squares. |
| MoE compute duration is the maximum profiled duration across emitted local EP ranks. | `serving/core/trace_generator.py#L1155-L1188` | Each rank lookup uses `(local_tokens, activated_experts)`. |
| PIM latency is `(scaled_slope*L+scaled_intercept)/channel_split`. | `serving/core/pim_model.py#L120-L185` | Device-specific baseline coefficients for four PIM specs. |

## Capacity And Memory Latency

| Formula / behavior | Source evidence | Notes |
|---|---|---|
| `KV_bytes/rank = 2*kv_dim*seq*num_layers*kv_bytes_per_element/num_npus` | `serving/core/memory_model.py#L209-L215` (`get_kv`) | `kv_dim=num_kv_heads*head_dim`; FP8 uses one byte. |
| `num_blocks=floor((utilization*NPU_memory-weight_bytes)/bytes_per_block)` | `serving/core/memory_model.py#L73-L100` | Capacity omits activation peak and CUDA context. |
| Lower-tier recall bytes equal coarse hits times lower-tier bytes per block. | `serving/core/kv_cache_manager.py#L297-L308` | Recall is critical-path traffic. |
| Lower-tier write-through is tracked but intentionally not charged to generation latency. | `serving/core/kv_cache_manager.py#L339-L355` | It is retained for energy accounting. |
| `t_mem(S)=mem_latency+floor(S/mem_bw)` | `astra-sim/extern/memory_backend/analytical/AnalyticalMemory.cc#L271-L275` | The backend directly divides bytes by the configured numeric `mem-bw`. |
| Per-node and pooled memory requests serialize through a FIFO per device. | `AnalyticalMemory.cc#L126-L200`, `#L202-L263` | Per-NPU expansion registers independent events. |
| PIM memory duration adds PIM compute runtime and load/store runtime. | `AnalyticalMemory.cc#L126-L155` | PIM channels have independent queues. |

## Communication Latency

| Formula / behavior | Source evidence | Notes |
|---|---|---|
| Network bandwidth conversion is `GB/s * 2^30 / 10^9` B/ns. | `astra-sim/extern/network_backend/analytical/common/NetworkFunction.cpp#L8-L15` | This is explicit in the network backend. |
| Congestion-unaware point-to-point delay is `hops*latency + bytes/bandwidth_Bpns`. | `.../congestion_unaware/basic-topology/BasicTopology.cpp#L37-L60` | Ring hop count is shortest bidirectional distance. |
| Congestion-aware arrival delay is `latency+bytes/bandwidth`; a link frees after serialization only. | `.../congestion_aware/network/Link.cpp#L91-L135` | Busy links queue chunks FIFO. |
| TP AllReduce size is the full output tensor of `o_proj` / `down_proj`, `T*hidden_size*bytes`. | `serving/core/trace_generator.py#L1062-L1067`, `#L1262-L1265` | ASTRA-Sim expects total collective data size. |
| P/D KV transfer per layer and rank is `2*kv_dim*tokens*kv_bytes/TP`. | `serving/core/trace_generator.py#L1047-L1059` | K+V only; Q is not sent. |
| MoE dispatch uses `max(1,T//EP)*(hidden+num_experts)*bytes`; combine uses `T*hidden*bytes`. | `serving/core/trace_generator.py#L1122-L1148` | Current implementation uses floor division with a minimum of one token. |
| Collective nodes preserve optional `involved_dim`. | `llm_converter.py#L215-L234`; `Workload.cc#L276-L340` | This scopes TP/EP to the intended topology dimensions. |
| ASTRA-Sim chunks data, selects active dimensions, and creates collective phases per implementation. | `astra-sim/astra-sim/system/Sys.cc#L800-L1100` (`generate_collective`) | Final latency is event scheduled, not a frontend scalar formula. |

## End-To-End Time

For ET node `v`:

```text
start(v)  = max finish(u), u in pred(v)
finish(v) = start(v) + duration(v)
```

The duration comes from the compute replay, analytical memory event, or communication collective. Shared memory/link/collective queues may delay `start(v)`. The frontend's `current` is updated from ASTRA-Sim's absolute completion cycle, so total simulated time is the latest completed sink event, not a serial sum of independent NPU iteration durations.

> Source: `astra-sim/astra-sim/workload/Workload.cc#L115-L190`, `#L202-L390`; `serving/__main__.py#L664-L670`, `#L1189-L1199`.

## Verification Status

| Check | State | Result |
|---|---|---|
| Source control/data-flow trace | passed | Static caller and state transition analysis completed. |
| Compute/memory/network formula trace | passed | Formula inputs, units, and backend dispatch verified against source. |
| Draw.io preflight and strict structure validation | passed | Zero FAILs; both files parse with one page and no embedded raster/external images. |
| XeLaTeX two-pass build | passed | 31 pages, zero LaTeX errors, undefined references, or overfull boxes. |
| PDF page-boundary audit | passed | Every extractable text block lies within the 16:9 page rectangle. |
| Full simulator baseline run | not run | No serving code was changed; compiling/running ASTRA-Sim was outside this documentation deliverable. |
| GPU profiler execution | blocked | Requires a supported NVIDIA GPU and the vLLM container. |
