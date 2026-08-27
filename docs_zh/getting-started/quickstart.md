---
sidebar_position: 3
title: 快速入门
---

# 快速入门

在一分钟内运行你的第一次端到端模拟。

本教程假定你已经完成了 [安装 → 模拟器设置](./installation/simulator)，并且位于模拟器容器内的 `/app/LLMServingSim`。

## 运行示例

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_single_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/example_single_run.csv' \
  --log-interval 1.0
```

就这么简单。模拟器将：

1. 从 `configs/cluster/single_node_single_instance.json` 加载集群拓扑（单张 RTXPRO6000 GPU 以 TP=1 运行 Llama-3.1-8B）。
2. 按照请求的到达时间从 `workloads/example_trace.jsonl` 流式读取请求。
3. 每个调度迭代驱动 ASTRA-Sim 以获得周期计数。
4. 将每个请求的延迟指标写入 `outputs/example_single_run.csv`。

你应该大约每秒看到一次吞吐量、内存和功耗输出行。运行结束后：

```bash
head outputs/example_single_run.csv
```

显示每个请求的输出。列依次为 `instance id`、`request id`、`model`、`input`、`output`、`arrival`、`end_time`、`latency`、`queuing_delay`、`TTFT`、`TPOT`、`ITL` —— 参见 **[读取输出](../simulator/reading-output)**。

## 这些 flag 的含义

| Flag | 作用 |
| --- | --- |
| `--cluster-config` | 集群拓扑 + 硬件。自动生成 ASTRA-Sim 输入文件。 |
| `--dtype` | 模型权重精度（`float16`、`bfloat16`、`float32`、`fp8`、`int8`）。选择匹配的剖析数据包。省略时使用模型配置中的 `torch_dtype`。 |
| `--block-size` | KV 缓存块大小（以 token 计）。默认 `16`。 |
| `--dataset` | 请求（或代理会话）的 JSONL 文件。 |
| `--output` | 每请求指标写入位置。 |
| `--log-interval` | 打印吞吐量 / 内存 / 功耗摘要行的频率（秒）。 |

完整 flag 列表位于 [参考 → CLI flags](../reference/cli-flags)。

## 尝试不同场景

`serving/run.sh` 附带几个可直接运行的示例：多实例、预填充/解码分离、带 EP 的 MoE、前缀缓存、CXL 内存、PIM 卸载与子批交错：

```bash
./serving/run.sh
```

该脚本中的每个块都是自包含的，可直接复制到你自己的脚本中。浏览驱动它们的集群配置：

```bash
ls configs/cluster/
```

## 接下来

- **[模拟器 → 架构概述](../simulator/architecture)**：了解模拟器内部如何运行。
- **[模拟器 → 读取输出](../simulator/reading-output)**：了解 `*.csv` 中的各项指标。
- **[工作负载 → JSONL 格式](../workloads/jsonl-format)**：用自己的轨迹驱动模拟器。
- **[性能剖析器概述](../profiler/overview)**：如果你想添加新硬件或模型。
