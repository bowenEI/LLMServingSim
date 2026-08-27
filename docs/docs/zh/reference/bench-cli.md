---
sidebar_position: 5
title: Bench CLI
---

# `python -m bench` CLI 参数

vLLM 基准测试框架的完整参考。`bench` 有两个子命令：`run` 通过真实的 vLLM 重放一个工作负载，`validate` 将一次已完成的运行与模拟器输出进行比较。

两者都必须在 **vLLM 容器**（`scripts/docker-vllm.sh`）内运行，而不是模拟器容器。见 **[安装 → vLLM 环境](../getting-started/installation/vllm)**。

由此产生的准确度数字见 **[验证](../validation)**。

## `python -m bench run`

严格重放：运行器读取 LLMServingSim 格式的 JSONL 工作负载——与 `python -m workloads.generators` 输出、`python -m serving --dataset` 消费的格式相同——并通过 `SamplingParams(min_tokens=N, max_tokens=N, ignore_eos=True)` 固定每个请求的 `input_tok_ids` 和 `output_toks`。因此 vLLM 运行处理的正是模拟器看到的那些 prompt，顺序也相同。

### 必填

| Flag | 类型 | 说明 |
| --- | --- | --- |
| `--model` | string | HF 模型 id，原样传给 `vllm.AsyncLLM`。与模拟器不同，这是真实的加载：权重会被下载并放到 GPU 上 |
| `--dataset` | path | LLMServingSim 格式的 JSONL 工作负载。见 **[工作负载 → JSONL 格式](../workloads/jsonl-format)** |
| `--output-dir` | path | 写入 `meta.json` / `requests.jsonl` / `timeseries.csv` 的位置。惯例是 `bench/results/<run_id>/` |

### 并行度

这些是 vLLM 自己的引擎参数，原样转发。它们是集群配置 `tp_size` / `ep_size` / `dp_group` 在 bench 侧的对应物。

| Flag | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--tensor-parallel-size` | int | `1` | vLLM `tensor_parallel_size` |
| `--data-parallel-size` | int | `1` | vLLM `data_parallel_size`（跨引擎 DP） |
| `--enable-expert-parallel` | flag | 关 | vLLM `enable_expert_parallel`，用于 MoE 模型 |

### 调度器与精度

把这些与你打算比较的模拟器运行对齐，否则比较就不是同类比较。

| Flag | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--max-num-seqs` | int | `128` | vLLM `max_num_seqs`，每引擎运行上限 |
| `--max-num-batched-tokens` | int | `2048` | vLLM `max_num_batched_tokens` |
| `--max-model-len` | int | `None` | vLLM `max_model_len`。`None` 使用模型自身的最大值 |
| `--dtype` | string | `bfloat16` | 模型 dtype |
| `--kv-cache-dtype` | string | `auto` | vLLM `kv_cache_dtype` |
| `--seed` | int | `42` | 采样种子 |

:::note[默认值与 `python -m serving` 不同]
`bench run` 把 `--dtype` 直接默认为 `bfloat16`，而模拟器从模型配置的 `torch_dtype` 解析。`bench` 也没有 `--block-size`：vLLM 自己选择 KV 块大小，它最终选定的值记录在 `meta.json` 的 `kv_cache.block_size` 下。读回它并作为 `--block-size` 传给模拟器，如果你想让两者对齐的话。
:::

### 工作负载与输出

| Flag | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--num-reqs` | int | `0` | 从数据集取用的请求数上限。`0` = 重放全部 |
| `--tick-seconds` | float | `1.0` | 统计记录器的降采样间隔，即 `timeseries.csv` 中的行间距。对应模拟器的 `--log-interval` |
| `--log-level` | choice | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

### 输出

```
<output-dir>/
  meta.json          run metadata plus what vLLM *resolved*: kv_cache
                     (num_gpu_blocks, block_size, num_kv_tokens,
                     gpu_memory_utilization), hardware (device name,
                     total memory, CUDA / torch versions), and
                     resolved_config -- the whole VllmConfig, one key
                     per sub-config
  requests.jsonl     per request: request_id, input_toks, output_toks,
                     arrival_time, queued_ts, scheduled_ts,
                     first_token_ts, last_token_ts
  timeseries.csv     per tick: t, prompt_throughput, gen_throughput,
                     running, waiting, kv_cache_pct
```

`meta.json` 的 `kv_cache.num_gpu_blocks` 是最值得先读的数字：它是模拟器必须匹配的 KV 容量，也是 vLLM 激活峰值唯一出现的地方，因为其内存预算的其余部分事先已知。模拟器不建模该峰值，因此在相同 `mem_util` 下它的容量是上界。见 **[KV 缓存与内存](../simulator/scheduling/kv-cache-and-memory)**。

数据集永不被修改——生成发生在 `workloads/generators` 中。

## `python -m bench validate`

加载 bench 产物以及同一工作负载的模拟器每请求 CSV 和日志，在匹配的定义下推导两侧的 TTFT / TPOT / 端到端延迟，并把图与数值摘要写入 bench 运行的一个子目录。

### 必填

| Flag | 类型 | 说明 |
| --- | --- | --- |
| `--bench-dir` | path | 一个已完成的 `bench run` 输出目录 |
| `--sim-csv` | path | 模拟器每请求 CSV，即你传给 `python -m serving --output` 的内容 |
| `--sim-log` | path | 模拟器日志，解析出每个 tick 的 running / waiting 计数。通过重定向模拟器的 stdout 捕获 |

### 可选

| Flag | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--output-subdir` | string | `validation` | `--bench-dir` 下存放图与摘要的子目录 |
| `--prefix` | string | `""` | 生成文件的文件名前缀 |
| `--title` | string | `vLLM vs LLMServingSim` | 图标题后缀 |
| `--log-level` | choice | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

### 输出

```
<bench-dir>/<output-subdir>/
  <prefix>_throughput.png     prompt + generation throughput, both sides
  <prefix>_requests.png       running / waiting counts over time
  <prefix>_latency.png        TTFT / TPOT / latency CDFs
  <prefix>_summary.txt        mean and P50 / P90 / P95 / P99 per metric, with diff%
```

### 匹配的指标定义

两侧从相同的参考点计算相同的三个量，因此 `diff%` 是有意义的：

| 指标 | 定义 |
| --- | --- |
| TTFT | `first_token_ts - arrival_time`（包含排队时间） |
| TPOT | `(last_token_ts - first_token_ts) / max(1, output_toks - 1)` |
| 延迟 | `last_token_ts - arrival_time` |

模拟器的 CSV 直接暴露 `arrival`、`end_time` 和逐 token 的 ITL 列表；bench 从 vLLM 的 `RequestStateStats` 推导同样的字段。

:::caution[`prompt_throughput` 不能逐 tick 比较]
vLLM 在预填充完成时对每个 prompt 计数一次，因此它的 `prompt_throughput` 序列无法显示抢占与重计算。模拟器的每 tick prompt token 可以。比较上面的每请求指标，并把吞吐量图读作形态而不是匹配的值。
:::

## Shell 包装脚本

两个主机侧包装脚本替你设置参数。两者都打算就地编辑或由环境变量驱动。

### `bench/bench.sh`

每个旋钮都是一个带默认值的环境变量：

```bash
MODEL=Qwen/Qwen3-32B \
DATASET=workloads/sharegpt-qwen3-32b-300-sps10.jsonl \
TP=2 DP=1 EXPERT_PARALLEL=0 \
MAX_NUM_SEQS=128 MAX_NUM_BATCHED_TOKENS=2048 \
./bench/bench.sh
```

| 变量 | 它设置的 Flag | 默认值 |
| --- | --- | --- |
| `MODEL` | `--model` | `Qwen/Qwen3-32B` |
| `DATASET` | `--dataset` | `workloads/sharegpt-qwen3-32b-300-sps10.jsonl` |
| `RUN_ID` | （命名输出目录） | `$(date +%Y%m%d-%H%M%S)` |
| `OUTPUT_DIR` | `--output-dir` | `bench/results/$RUN_ID` |
| `TP` | `--tensor-parallel-size` | `2` |
| `DP` | `--data-parallel-size` | `1` |
| `EXPERT_PARALLEL` | 为 `1` 时设置 `--enable-expert-parallel` | `0` |
| `MAX_NUM_SEQS` | `--max-num-seqs` | `128` |
| `MAX_NUM_BATCHED_TOKENS` | `--max-num-batched-tokens` | `2048` |
| `MAX_MODEL_LEN` | `--max-model-len`，为空时省略 | 空 |
| `DTYPE` | `--dtype` | `bfloat16` |
| `KV_CACHE_DTYPE` | `--kv-cache-dtype` | `auto` |
| `SEED` | `--seed` | `42` |
| `TICK_SECONDS` | `--tick-seconds` | `1.0` |
| `NUM_REQS` | `--num-reqs` | `0` |
| `LOG_LEVEL` | `--log-level` | `INFO` |

注意 `TP=2`——包装脚本的默认值不是 vLLM 的 `1`。

### `bench/validate.sh`

位置参数，带三个环境变量覆盖：

```bash
./bench/validate.sh <bench_dir> <sim_csv> <sim_log> [prefix]
```

| 位置 / 变量 | 它设置的 Flag | 默认值 |
| --- | --- | --- |
| `$1` | `--bench-dir` | 必填 |
| `$2` | `--sim-csv` | 必填 |
| `$3` | `--sim-log` | 必填 |
| `$4` | `--prefix`，为空时省略 | 空 |
| `OUTPUT_SUBDIR` | `--output-subdir` | `validation` |
| `TITLE` | `--title` | `vLLM vs LLMServingSim` |
| `LOG_LEVEL` | `--log-level` | `INFO` |

## 已提交的示例

`bench/examples/` 保存了四个端到端运行，按 `<hardware>/<model>` 键控——一个稠密单 GPU 基线、一个 TP=2 稠密运行和一个 RTXPRO6000 上的 DP+EP MoE 运行，外加同一个稠密基线在 RTX 4090 上的版本——每个都捆绑了它的集群 `config.json`、vLLM 产物、模拟器输出以及最终的验证摘要和图。`bench/examples/run.sh <hardware>/<model>` 重新运行模拟器侧，`bench/examples/validate.sh <hardware>/<model>` 重新运行比较；两者在不给参数时都会处理每个示例。头版数字在 **[验证](../validation)** 上。

## 下一步

- **[验证](../validation)**：这些运行实际测量了什么。
- **[贡献者 → 验证你的改动](../contributor/validating-changes)**：使用该框架的回归工作流。
- **[工作负载 → ShareGPT 生成器](../workloads/sharegpt-generators)**：为 `--dataset` 生成数据集。
