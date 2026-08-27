---
title: 阅读输出
sidebar_position: 8
---

# 阅读输出

模拟器产生三类输出：

1. 通过 `--output` 传入路径的**每请求 CSV**。
2. 每 `--log-interval` 秒打印一次的**吞吐量日志行**。
3. **最终功耗汇总**（仅当集群配置有 `power:` 块时）。

本页介绍每一项的含义以及如何阅读它们。

## 每请求 CSV

当你传入 `--output outputs/foo.csv` 时，模拟器为每个完成的请求写一行：

```csv
instance id,request id,model,input,output,arrival,end_time,latency,queuing_delay,TTFT,TPOT,ITL
0,0,Qwen/Qwen3-30B-A3B-Instruct-2507,1472,133,4059740,1082836204,1078776464,0,51162321,7784955,"[7780422, 7779379, 7779523, ...]"
0,3,meta-llama/Llama-3.1-8B,4,16,570907776,711600111,140692335,3739551,15137413,11414083,"[11043655, 11381158, ...]"
...
```

捆绑的 `outputs/example_*_run.csv` 文件（`serving/run.sh` 中每个场景一个）是很好的速览示例。

### 列参考

| 列 | 类型 | 含义 |
| --- | --- | --- |
| `instance id` | int | 运行此请求的服务实例 |
| `request id` | int | 路由器分配的单调递增 id |
| `model` | string | 模型名称（例如 `meta-llama/Llama-3.1-8B`） |
| `input` | int | 提示词 token（完整输入长度，包括任何前缀缓存命中） |
| `output` | int | 生成的解码 token（即总长度减去 `input`） |
| `arrival` | int (ns) | 请求到达时间（模拟时钟） |
| `end_time` | int (ns) | 最后一个生成的 token 完成时间 |
| `latency` | int (ns) | 端到端延迟：`end_time - arrival` |
| `queuing_delay` | int (ns) | 从到达到首次调度 |
| `TTFT` | int (ns) | 首 token 时间：首 token 完成减去 `arrival` |
| `TPOT` | int (ns) | 平均每输出 token 时间：`(latency - TTFT) // (output - 1)`（当 `output == 1` 时为 `0`） |
| `ITL` | string | 逐 token 延迟，单位 ns。序列化的 Python 列表，例如 `"[7780422, 7779379, ...]"` |

所有时间单位都是**纳秒**。除以 `1e9` 得秒，除以 `1e6` 得毫秒。列名使用空格而非下划线；在 pandas 中需要加引号（`df["instance id"]`）。

> **注意：** `Request` 对象内部还携带 `session_id` / `sub_request_index`（用于 agentic 工作负载）和每层前缀缓存命中计数器（`prefix_cache_hit`、`npu_cache_hit`、`storage_cache_hit`）。这些在内存中跟踪，并在吞吐量日志行中呈现，但**目前**不写入每请求 CSV。使用吞吐量日志（配合 `--log-interval`）查看聚合的前缀命中率；对于每请求的 agentic 记账，直接读取 `Request` 对象或扩展 `Scheduler.save_output`。

### 常用派生指标

```python
import pandas as pd
df = pd.read_csv("outputs/foo.csv")

# Wall-clock TTFT in milliseconds
df["TTFT_ms"] = df["TTFT"] / 1e6

# TPOT in milliseconds (already a per-token mean; divide for ms)
df["TPOT_ms"] = df["TPOT"] / 1e6

# End-to-end latency in seconds
df["latency_s"] = df["latency"] / 1e9

# Throughput across the whole run (tokens / second)
total_tokens = (df["input"] + df["output"]).sum()
sim_duration_s = (df["end_time"].max() - df["arrival"].min()) / 1e9
throughput = total_tokens / sim_duration_s

# Per-instance distribution
per_inst = df.groupby("instance id").agg(
    requests=("request id", "count"),
    p50_TTFT_ms=("TTFT", lambda x: x.quantile(0.5) / 1e6),
    p99_TTFT_ms=("TTFT", lambda x: x.quantile(0.99) / 1e6),
)

# Inter-token latency: parse the ITL string back into a list per row
import ast
df["ITL_list"] = df["ITL"].apply(ast.literal_eval)
df["ITL_p50_ms"] = df["ITL_list"].apply(lambda xs: pd.Series(xs).quantile(0.5) / 1e6)
```

## 标准输出（日志级别）

模拟器的 `--log-level` 标志控制运行期间 stdout 上出现多少细节：

| 级别 | 你会看到什么 |
| --- | --- |
| `WARNING`（默认） | 每 `--log-interval` 秒一次的心跳块，外加警告（variant 回退、运行时超出剖析器扫描范围、MoE 配置不匹配等） |
| `INFO` | 增加每次迭代的调度器细节和请求生命周期事件（恢复通知、每节点功耗日志） |
| `DEBUG` | 增加逐层内存加载 / 存储活动和完整的 `Batch` / `Request` 转储。产生大量输出；请重定向到文件 |

与级别无关，运行总会打印启动横幅、KV 缓存容量块、周期性心跳和最终结果。`bench/examples/<hardware>/<model>/outputs/sim.log` 保存了所有这些内容的完整真实示例；本页每个样例都来自那里。

### 启动横幅

```text
──────────────────────────── LLMServingSim2.0 ────────────────────────────
                              Input configuration

  • Cluster config             : bench/examples/RTXPRO6000/Llama-3.1-8B/config.json
  • Run ID                     : run_1787203264816023_112338
  • ASTRA-Sim inputs root      : /app/LLMServingSim/astra-sim/inputs/runs/run_1787203264816023_112338
  • Dataset                    : workloads/sharegpt-llama-3.1-8b-300-sps10.jsonl
  • Max num seqs               : 128
  • Max batched tokens         : 2048
  • Block size (tokens)        : 16
  • Request routing            : LOAD
  • Expert routing             : BALANCED
  • Prefix caching             : ENABLED
  • Chunked prefill            : ENABLED
  • Prefix caching scheme      : xPU-Only
  • Centralized prefix caching : DISABLED
  • Offload attention to PIM   : DISABLED
  • Sub-batch interleaving     : DISABLED
  • Network backend            : analytical
  • Log interval (s)           : 1.0
  • Log level                  : WARNING
──────────────────────────────────────────────────────────────────────────
                          KV Cache Initialization

  • Instance [0] : 585248 tokens / 36578 blocks (71.44 GiB/rank at util 0.90)
```

**Run ID** 和 inputs root 是你查找一次运行的中间 ASTRA-Sim 文件所需的信息，并且只有在你传入 `--keep-inputs`（或隐含它的 `--save-trace-text`）时才会保留。

**KV Cache Initialization** 行是与真实 vLLM 对比时首先要读的：它报告模拟器根据 `npu_mem.mem_size * mem_util - weight` 推导出的容量。vLLM 还会减去其激活峰值和 CUDA 上下文，模拟器不对此建模，因此这是在相同利用率下对 vLLM 容量的上界。`bench run` 的 `meta.json::kv_cache.num_gpu_blocks` 是与它对比的数字。

注意横幅报告的是 `Max num seqs` 和 `Max batched tokens` 的 **CLI** 值。每实例的覆盖值不会在此回显，因此在异构配置下，此块不会告诉你每个实例实际得到什么。参见 **[集群配置 → 运行时覆盖](../reference/cluster-config#runtime-overrides-optional)**。

## 心跳块

每经过 `--log-interval` 模拟秒，模拟器打印一行吞吐量，随后是一个缩进树，每个实例一个分支，然后每个节点一个：

```text
[1.0s] Avg prompt throughput: 9069.0 tokens/s, Avg generation throughput: 224.0 tokens/s
        ├─Running Instance[0]: 9 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 16486.51 MB (16.771 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 9069)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
```

开头的 `[1.0s]` 是**模拟**时钟，不是墙钟。

| 字段 | 含义 |
| --- | --- |
| `Avg prompt throughput` | 区间内的输入 token/s，**包括**前缀缓存命中 |
| `Avg generation throughput` | 区间内生成的 token/s |
| `Running Instance[i]` | `len(scheduler.running)` —— 持久运行集合，不是本步批次的大小。这是 vLLM `num_running_reqs` 的对应物，`bench validate` 与之比较的正是它 |
| `Waiting` | 已经**到达**的等待请求（未来的到达被排除） |
| `Total # N NPUs` | 实例的 `num_npus` |
| `Each NPU Memory Usage` | 每个 rank 的权重加 KV，以及占 `npu_mem.mem_size` 的百分比——因此上限是 `mem_util * 100`，而不是 100 |
| `Prefix Cache Hit ratio` | 自运行开始以来的累计值，不是每区间值，后面跟着 `(命中 token / 请求 token)`。仅当实例开启前缀缓存时出现 |
| `Node[i]` | 该节点较低层 KV 层使用的主机内存 |

### 多实例

每个实例一个 `├─Running Instance[i]` 分支，`Node` 行增加主机总量的每实例拆分：

```text
[4.0s] Avg prompt throughput: 9063.0 tokens/s, Avg generation throughput: 1074.0 tokens/s
        ├─Running Instance[0]: 23 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 32634.88 MB (33.198 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 20285)
        ├─Running Instance[1]: 22 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 32981.38 MB (33.550 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 24147)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used (Instance[0]: 0.00 %, Instance[1]: 0.00 %)
```

末尾的每实例百分比是每个实例占节点 CPU 使用量的份额，不是占节点容量的份额——有东西驻留时它们加起来是 100%。当节点只有一个实例时省略，当 `--enable-prefix-sharing --prefix-storage CPU` 使池变为节点级而非每实例时也省略；那种情况下 `Node` 行携带共享的 `Prefix Cache Hit ratio`。

此块中没有信息能标识哪个实例是预填充、哪个是解码。请从集群配置中读取实例顺序。

### 以 CXL 作为较低层

`--prefix-storage CXL` 在节点行之后增加一个 `CXL` 分支。使用 `--enable-prefix-sharing` 时每个设备一个分支：

```text
        ├─CXL[0]: Total CXL Device Memory Usage 3276.80MB, 3.200 % Used
```

不共享时，每个前缀缓存实例一个：

```text
        ├─CXL[0]/Instance[0]: Total CXL Device Memory Usage 3276.80 MB, 3.200 % Used
```

### 使用功耗模型

节点上的 `power:` 块追加一个最终分支：

```text
        └─Avg power consumption: 712.4 W
```

这个标签既对又误导。它*是*一个平均值——在日志区间内，计算为自上次心跳以来累计的能量除以经过的模拟时间——但它同时也是跨每个节点求和的单个**集群级**数字，因此在多节点运行中这一行无法按节点归属。按节点拆分只出现在最终汇总中。

## 最终结果

关闭时模拟器打印几个带横线的区块。取自一次真实的 300 请求运行（已裁剪）：

```text
▶ Simulation results...

Total simulation time: 0h 2m 40.611s
─────────────────────────── Throughput Results ───────────────────────────
Total requests:                                                     300
Total clocks (ns):                                                  65049871040
Total latency (s):                                                  65.050
Total input tokens:                                                 257239
Total generated tokens:                                             195753
Request throughput (req/s):                                         4.61
Average prompt throughput (tok/s):                                  3954.49
Average generation throughput (tok/s):                              3009.28
Total token throughput (tok/s):                                     6963.76
Throughput per 1.0 sec ([prompt_throughput], [gen_throughput]): [(9069.0, 224.0), (13535.0, 493.0), ...]
──────────────────────── Prefix Caching Results ──────────────────────────
Total requested prompt tokens:                                      257239
NPU prefix hit prompt tokens:                                       19520
NPU prefix hit ratio (%):                                           7.59
Total prefix hit ratio (%):                                         7.59
───────────────────────────── Instance [0] ───────────────────────────────
─────────────────────────── Time to First Token ──────────────────────────
Mean TTFT (ms):                                                     6915.26
Median TTFT (ms):                                                   8783.06
P99 TTFT (ms):                                                      19627.55
───────────────── Time per Output Token (excl. 1st token) ────────────────
Mean TPOT (ms):                                                     32.33
Median TPOT (ms):                                                   33.59
P99 TPOT (ms):                                                      37.80
─────────────────────────── Inter-token Latency ──────────────────────────
Mean ITL (ms) :                                                     32.24
Median ITL (ms) :                                                   27.68
P99 ITL (ms) :                                                      111.39
──────────────────────────────────────────────────────────────────────────
```

关于个别字段的说明：

- **`Total simulation time`** 是墙钟时间：模拟运行了多久，而不是工作负载的模拟时长。后者是 `Total latency (s)`。
- **`Total clocks (ns)`** 是以 ASTRA-Sim 周期计的模拟 makespan。由于模拟器是确定性的，这是一个精确的回归信号——相同的配置和工作负载可以逐位复现它。
- **`Total input tokens`** 从每个请求的 `original_input` 求和，刻意*不*通过减去重算计数器来推导。一个在重算中途再次被抢占的请求，每次重新接纳时都会被收取其全部剩余工作量，因此两者不是互补的。
- **`Preemptions`** 和 **`Recomputed prompt tokens (preemption)`** 行仅在非零时出现。它们缺席意味着运行从未抢占。
- **`Throughput per N sec`** 是完整的每区间序列，与心跳行的数字相同，形式为 `(prompt, generation)` 对列表。
- **Prefix Caching Results** 块仅当某个实例开启前缀缓存时出现。使用 `--prefix-storage CPU` 或 `CXL` 时，会增加 `<tier> prefix hit prompt tokens` / `<tier> prefix hit ratio` 对，`Total prefix hit ratio` 覆盖两层。
- 每 **Instance** 块报告**毫秒**，与全程纳秒的 CSV 不同。

:::note[TTFT 的测量方式与 vLLM 不同]
模拟器在第一个 token 的*计算*完成时停表。vLLM 在客户端*收到* token 时停表，因此真实 vLLM 的 TTFT 更高。`bench validate` 让两边使用匹配的定义；参见 **[Bench CLI](../reference/bench-cli)**。
:::

### 功耗建模结果

配置了 `power:` 块时，会在吞吐量与每实例块之间增加一个区块：

```text
──────────────────────── Power Modeling Results ──────────────────────────
Total energy consumption (kJ):                                      15.95
──────────────────────────────────────────────────────────────────────────
Node 0 total energy consumption (kJ):                               15.95
├─ NPU energy consumption (J):        12453.00
├─ CPU energy consumption (J):         1233.00
├─ DRAM energy consumption (J):         442.00
├─ Link energy consumption (J):         388.00
└─ ...
──────────────────────────────────────────────────────────────────────────
Power per 1.0 sec (W): [712.4, 698.1, ...]
```

每个节点一个节点块，每个列出其按设备的能量，随后是完整的每区间功耗序列。按设备数字包含该设备常开基础功耗乘以运行时长，因此它们加起来等于节点总量。

## 值得留意的常见模式

### 等待数高，NPU 内存低

心跳显示大量 `Waiting` 计数，而 `Each NPU Memory Usage` 远低于 `mem_util * 100 %`。可能的原因：token 预算（`--max-num-batched-tokens`）或 `--max-num-seqs` 是瓶颈，而不是内存。哪个受限就提高哪个。

如果 `Running` 恰好钉在 `--max-num-seqs`，那就是绑定约束。如果 `Running` 在变化但吞吐量不变，则是 token 预算。

### 预填充突发期间解码 TPOT 尖峰

预填充密集的时刻与进行中的解码落在同一个批次，预算被预填充吃光，解码延迟被拉长。

缓解措施：
- `--enable-chunked-prefill`（默认）拆分长预填充。
- `--long-prefill-token-threshold N` 限制每步的预填充 token。
- `--npu-memory-utilization` 设置权重加 KV 可以使用的 NPU 内存量。**提高**它会扩大 KV 缓存并接纳更多并发请求；降低它会缩小容量，从而增加抢占。

### 前缀命中率接近 0%

要么工作负载确实没有共享前缀，要么它没有预先 token 化。没有 `input_tok_ids` 的请求得到空哈希链，这会直接禁用它此前缀缓存——因此未 token 化的工作负载在启用该特性时正好报告 0.00%。先检查 JSONL（参见 [工作负载 → JSONL 格式](../workloads/jsonl-format#why-token-ids-matter)）。

注意心跳的比例是**自运行开始累计**的，因此即使是在共享严重的工作负载上，前几个区间它也接近零，爬升缓慢。

### MoE 每 rank 延迟剧烈波动

设置 `--expert-routing-policy BALANCED`（默认）。RR 或 RAND 在小型批次上可能产生不均匀负载。使用 BALANCED，每 rank 延迟应在大约 1% 以内保持一致。

### CXL 延迟主导 TPOT

放在 CXL 上的权重在每次解码步骤都要付出往返代价。如果 TPOT 看起来比预期差得多，检查 `placement` 块——将冷层（embedding、lm_head）移到 CXL 有帮助；移动每个 decoder 块会伤害性能。

## 对照已知参考验证

LLMServingSim 与真实 vLLM 进行端到端验证。在四个捆绑配置上，TPOT 均值落在 1.7% 以内，端到端延迟均值在 2.2% 以内；TTFT 均值在 +1.3% 到 -13.6% 之间，对于一个绝对值小的指标来说这是很小的绝对差。RTX 4090 运行——那张卡饱和、其 `mem_util` 已按实测 KV 块数校准——每个指标都在 1% 以内。数字和图表在 **[验证](../validation)**；产生它们的测试平台是 **[Bench CLI](../reference/bench-cli)**。这些运行的完整真实日志提交在 **[bench/examples/](https://github.com/casys-kaist/LLMServingSim/tree/main/bench/examples)** 下，这是查看健康运行端到端样子的最佳位置。

## 接下来

- **[参考 → CLI 标志](../reference/cli-flags)**：影响输出的每个标志。
- **[示例](../examples)**：用于对比输出的可运行配置。
