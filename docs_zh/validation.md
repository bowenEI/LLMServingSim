---
title: 验证
sidebar_position: 3
description: LLMServingSim 的输出与真实 vLLM 的对比情况
---

# 验证

LLMServingSim 在随附的 **(hardware, model) 组合**上与真实 vLLM 端到端对比验证。下面的数字来自在 RTXPRO6000 上把 300 请求的 ShareGPT 回放分别跑过 vLLM v0.19.0 和模拟器，再用 `python -m bench validate` 比较逐请求与逐 tick 指标。

> **想验证你自己的改动？** 回归工作流见 **[给贡献者 → 验证你的改动](contributor/validating-changes)**。

## 设置

| 参数 | 值 |
| --- | --- |
| **工作负载** | 300 个 ShareGPT 派生请求，约 10 sps 泊松到达 |
| **硬件** | RTXPRO6000 与 RTX 4090，单节点（`profiler/perf/<hardware>/` 中的剖析包） |
| **vLLM 版本** | `v0.19.0`（bench 容器使用的固定版本） |
| **块大小** | 16 |
| **引擎 flags** | 默认值，除非集群配置另有规定 |
| **集群配置** | `bench/examples/<hardware>/<model>/config.json` |
| **KV 容量** | `mem_util` 为 `0.9`，RTX 4090 示例除外（该校准到实测块数，见下文） |

输入和输出（vLLM token ID、采样参数、逐请求耗时）通过 `bench` 的严格回放路径固定，因此两边以相同顺序处理完全相同的提示。

:::caution[每当 KV 缓存饱和时，把 `mem_util` 对齐到真实运行]
`npu_mem.mem_util` 决定 KV 缓存大小，而 KV 缓存大小只在运行真正**填满**它时才会体现在结果中——低于该上限时没有任何抢占，容量不可见。这里的四个配置中只有 RTX 4090 处于该状态：24 GB，在大部分运行时间里钉在天花板上。因此它把 `mem_util` 设置为让模拟器的块数等于 vLLM 解析出的块数（从该运行自己的 `meta.json` 读出）：

```json
"kv_cache": { "num_gpu_blocks": 2588, "block_size": 16, "num_kv_tokens": 41408 }
```

这很重要，因为模拟器不建模 vLLM 的激活峰值或 CUDA 上下文，所以默认的 `mem_util: 0.9` 会得到比 vLLM 在相同比例下*更多*的 KV 缓存——更少的抢占、更早结束，所有延迟指标也随之移动：

| | KV tokens | 块数 | TTFT 均值 | TPOT 均值 | 延迟均值 |
| --- | --- | --- | --- | --- | --- |
| `mem_util: 0.9`（默认） | 54,400 | 3,400 | -20.7% | +12.9% | -12.5% |
| `mem_util: 0.833919`（匹配） | 41,408 | 2,588 | **+0.6%** | **+0.2%** | **+0.5%** |

三个 RTXPRO6000 配置在 96 GB 卡上峰值只到预算的 58-97%，因此它们保持 `0.9`——校准它们不会有任何变化。如果你针对自己的 vLLM 运行做验证，先检查心跳中的 `Each NPU Memory Usage` 峰值：如果它接近 `mem_util * 100`，就从 `meta.json` 读取 `num_gpu_blocks` 并匹配它，然后再比较任何延迟。
:::

## 头条数字

与真实 vLLM 相比，四个当前随附配置的每个指标的均值误差：

| 硬件 | 模型 | 并行度 | TTFT 均值 | TPOT 均值 | 延迟均值 |
| --- | --- | --- | --- | --- | --- |
| RTX 4090   | Llama-3.1-8B                | TP=1 dense      | +0.6% | +0.2% | +0.5% |
| RTXPRO6000 | Llama-3.1-8B                | TP=1 dense      | -4.0% | -1.0% | -1.8% |
| RTXPRO6000 | Qwen3-32B                   | TP=2 dense      | +1.3% | +0.8% | +1.0% |
| RTXPRO6000 | Qwen3-30B-A3B-Instruct-2507 | DP=2 x EP=2 MoE | -13.6% | -1.7% | -2.2% |

本页每个数字都从已提交的 `bench/examples/<hardware>/<model>/validation/summary.txt` 文件读出，因此可复现而非转述。

**四个配置的 TPOT 均值都落在 1.7% 以内、端到端延迟均值落在 2.2% 以内**，DP+EP MoE 路径与 dense TP 路径一样紧密地跟踪 vLLM。TTFT 均值更松：RTXPRO6000 Llama 运行为 -4.0%，MoE 运行为 -13.6%。

RTX 4090 一行是四个中最紧的，包括所有分位数在内每个指标都在 1% 以内。它也是唯一把 `mem_util` 校准到实测 KV 块数的运行——见上文提示——且是唯一显卡饱和的运行，因此它是现有最干净的同类对比。

这个 TTFT 差距在意料之中而非令人担忧，在读表之前值得知道原因。两侧对测量的定义并不相同——模拟器在第一个 token 的*计算*完成时停表，vLLM 在客户端*收到*它时停表——而 TTFT 由排队主导，所以运行早期一个小的调度差异就会大幅移动均值。MoE 运行的中位 TTFT 是 138.8 ms 对比 108.6 ms，因此 30 ms 的绝对差读作 -21.8%。请用绝对误差和尾部来评判 TTFT，而不是用很小的数字的百分比：每个配置的 TTFT P90 到 P99 都落在 10.9% 以内，RTX 4090 运行在 1.0% 以内。

逐分位数数字（中位数 / P90 / P95 / P99）在同样的 `summary.txt` 文件中，位于 [`bench/examples/`](https://github.com/casys-kaist/LLMServingSim/tree/main/bench/examples)。

## 逐配置结果

### RTX 4090 — Llama-3.1-8B（TP=1 dense）

吞吐量时间线，vLLM（橙色）对比模拟器（蓝色）：

![RTX 4090 Llama-3.1-8B 吞吐量](/img/validation/rtx4090-llama-3.1-8b-throughput.png)

| 指标 | vLLM | 模拟器 | 差异 |
| --- | --- | --- | --- |
| TTFT 均值     |   65.46 s |   65.82 s | **+0.6%** |
| TTFT P99      |  137.36 s |  137.70 s | +0.3% |
| TPOT 均值     |   32.4 ms |   32.5 ms | **+0.2%** |
| TPOT P99      |   56.0 ms |   56.5 ms | +0.9% |
| 延迟均值  |   86.58 s |   86.98 s | **+0.5%** |
| 延迟 P99   |  153.63 s |  154.22 s | +0.4% |

这是整套中最紧的配置：每个分位数的每个指标都落在 +0.2% 到 +0.9% 之间。两件事让它成为可用的最干净对比。24 GB 显卡确实饱和了它的 KV 缓存，所以调度器两侧都处于真实的内存压力下，而不是有余量运行；且它的 `mem_util` 校准到 vLLM 实际解析出的块数，所以两边从相同的容量出发。延迟模型本身未动——剖析延迟按实测值进入——所以 +0.2% 的 TPOT 是免费预测而非拟合。

### RTXPRO6000 — Llama-3.1-8B（TP=1 dense）

![Llama-3.1-8B 吞吐量](/img/validation/rtxpro6000-llama-3.1-8b-throughput.png)

| 指标 | vLLM | 模拟器 | 差异 |
| --- | --- | --- | --- |
| TTFT 均值     |    7.10 s |    6.82 s | **-4.0%** |
| TTFT P99      |   19.76 s |   19.36 s | -2.0% |
| TPOT 均值     |   32.5 ms |   32.1 ms | **-1.0%** |
| TPOT P99      |   37.3 ms |   37.6 ms | +0.6% |
| 延迟均值  |   28.20 s |   27.69 s | **-1.8%** |
| 延迟 P99   |   37.64 s |   37.03 s | -1.6% |

同样的模型和并行度跑在 96 GB 卡上，它从不填满 KV 缓存（峰值到预算的 78%）。TPOT 保持在 1.0% 以内，延迟在 1.8% 以内；TTFT 均值 -4.0%、中位数 -8.6%，模拟器让首 token 略微提前出来。

### RTXPRO6000 — Qwen3-32B（TP=2 dense）

![Qwen3-32B 吞吐量](/img/validation/rtxpro6000-qwen3-32b-throughput.png)

| 指标 | vLLM | 模拟器 | 差异 |
| --- | --- | --- | --- |
| TTFT 均值     |   36.91 s |   37.37 s | **+1.3%** |
| TTFT P99      |   93.35 s |   94.21 s | +0.9% |
| TPOT 均值     |   80.3 ms |   81.0 ms | **+0.8%** |
| TPOT P99      |   97.1 ms |   98.4 ms | +1.3% |
| 延迟均值  |   90.41 s |   91.33 s | **+1.0%** |
| 延迟 P99   |  126.34 s |  127.93 s | +1.3% |

TP=2 在 `o_proj` / `down_proj` 上演练了 dense ALLREDUCE 集合通信。这是 RTXPRO6000 各运行中最均匀准确的：每个分位数的每个指标都落在 +0.8% 到 +1.7% 之间，且全部为正——模拟器以一个小而一致的余量过度预测，而非漂移。

### RTXPRO6000 — Qwen3-30B-A3B-Instruct-2507（DP=2 × EP=2 MoE）

![Qwen3-30B-A3B 吞吐量](/img/validation/rtxpro6000-qwen3-30b-a3b-throughput.png)

| 指标 | vLLM | 模拟器 | 差异 |
| --- | --- | --- | --- |
| TTFT 均值     |    1.09 s |    0.94 s | **-13.6%** |
| TTFT P99      |    9.59 s |    9.49 s | -1.0% |
| TPOT 均值     |   47.3 ms |   46.5 ms | **-1.7%** |
| TPOT P99      |   53.3 ms |   53.0 ms | -0.5% |
| 延迟均值  |   32.34 s |   31.65 s | **-2.2%** |
| 延迟 P99   |   43.90 s |   43.09 s | -1.8% |

解耦路径：跨两个实例数据并行、实例内专家并行，带波同步集合通信。TPOT 和延迟保持在 -1.7% 和 -2.2%，但 TTFT 均值读作 -13.6%、中位数 -21.8%。绝对数字解释了大部分原因：中位数是 138.8 ms 对比 108.6 ms，是整套最小数值上的 30 ms 差异。绝对排队占主导的尾部回到 P99 的 -1.0%。这个运行是四个中内存余量*最多*的（预算的 52%），因此它的 TTFT 误差不是容量效应。

## 本地复现

bench 模块自带复现脚本，可以重跑模拟器一侧并对照已提交的 vLLM 工件重跑比较：

```bash
# 模拟器侧：写出 bench/examples/<hardware>/<model>/outputs/sim.csv
./bench/examples/run.sh                       # 全部四个
./bench/examples/run.sh RTX4090/Llama-3.1-8B  # 或一次一个

# 比较：写出 bench/examples/<hardware>/<model>/validation/{summary.txt, *.png}
./bench/examples/validate.sh
./bench/examples/validate.sh RTX4090/Llama-3.1-8B
```

两个脚本都接受 `<hardware>/<model>`，并从目录布局中发现示例，因此本页每个数字都从已提交工件回来，无需编辑脚本。

验证步骤重新生成吞吐量 / 延迟 / 请求图与头条汇总。要重跑 vLLM 本身（而不是复用 `bench/examples/<hardware>/<model>/vllm/` 下的已提交工件），在 vLLM 容器内使用 `python -m bench run`；完整布局见 [`bench/README.md`](https://github.com/casys-kaist/LLMServingSim/blob/main/bench/README.md)。

## 下一步

- **[给贡献者 → 验证你的改动](contributor/validating-changes)**：`./serving/validate.sh` —— 开 PR 之前要跑的那个检查，以及如何报告移动了的数字。
- **[模拟器 → 读取输出](simulator/reading-output)**：逐请求 CSV 每一列的含义，以及如何从中推导你自己的指标。
