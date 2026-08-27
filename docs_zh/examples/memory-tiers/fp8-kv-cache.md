---
title: FP8 KV 缓存
sidebar_position: 3
---

# FP8 KV 缓存

> **本示例演示：** 用 8 位浮点（1 字节 / 元素）存储键和值，而不是 bf16/fp16（2 字节），从而将 KV 缓存内存消耗减半。为更大的批次或更长的上下文释放 NPU 内存。

`--kv-cache-dtype fp8` 就是这个 flag。它做两件事：

1. **轨迹生成器**把 variant 文件夹查找从 `<dtype>`（例如 `bf16`）切换到 `<dtype>-kvfp8`（例如 `bf16-kvfp8`），因此注意力延迟来自 FP8-KV 剖析数据包。
2. **内存模型**把每块 KV 缓存的字节数减半（`bytes_per_block` 用 `kv_fp = 1` 而不是 `2`），因此在相同的 `npu_mem` 下，调度器可以容纳约 2 倍的活跃 token。

## 前置条件

- 已配置模拟器容器
- 一个带 **`-kvfp8` variant** 的剖析数据包，用于你的 `(hardware, model)` 组合。打包的 RTXPRO6000 性能数据只附带 `bf16` variant——见下方提示框。

> ⚠️ **你需要 FP8-KV 剖析数据包。** 如果 `profiler/perf/<hardware>/<model>/<variant>-kvfp8/` 不存在，模拟器会在启动时退出，并给出指向缺失文件夹的清晰 `FileNotFoundError`。目前打包的：
>
> | 硬件 | 模型 | 附带的 variants |
> | --- | --- | --- |
> | `RTXPRO6000` | `meta-llama/Llama-3.1-8B` | `bf16` |
> | `RTXPRO6000` | `Qwen/Qwen3-32B` | `bf16` |
> | `RTXPRO6000` | `Qwen/Qwen3-30B-A3B-Instruct-2507` | `bf16` |
>
> 要在今天使用本示例，请先用 `KV_CACHE_DTYPE=fp8 ./profiler/profile.sh` 剖析 `-kvfp8` variant（参见**[性能剖析器 → 添加硬件](../../profiler/adding-hardware)**），然后重新运行。

## 集群配置

任何单实例集群配置都适用；FP8 KV 是运行时 CLI flag，不是配置字段。示例使用打包的简单配置：

```json title="configs/cluster/single_node_single_instance.json"
{
  "num_nodes": 1,
  "link_bw": 16,
  "link_latency": 20000,
  "nodes": [
    {
      "num_instances": 1,
      "cpu_mem": {"mem_size": 512, "mem_bw": 256, "mem_latency": 0},
      "instances": [
        {
          "model_name": "meta-llama/Llama-3.1-8B",
          "hardware": "RTXPRO6000",
          "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
          "num_npus": 1,
          "tp_size": 1,
          "pd_type": null
        }
      ]
    }
  ]
}
```

## 运行

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_single_instance.json' \
  --dtype bfloat16 --kv-cache-dtype fp8 --block-size 16 \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/fp8_kv_run.csv' \
  --log-interval 1.0
```

两个 dtype flag 组合使用：

- `--dtype bfloat16`：权重仍为 bf16（由权重侧剖析 variant 决定）。
- `--kv-cache-dtype fp8`：KV 缓存为 fp8。variant 解析器在权重 variant 后追加 `-kvfp8`，因此本次运行从 `profiler/perf/RTXPRO6000/meta-llama/Llama-3.1-8B/bf16-kvfp8/` 读取注意力延迟。

## 预期输出

吞吐量日志形状看起来不变，但相同批次大小下的内存占用要小得多：

```text
[42.0s] Avg prompt throughput: 2416.0 tokens/s, Avg generation throughput: 860.0 tokens/s
        ├─Running Instance[0]: 16 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 68204.26 MB (69.362 % Used), Prefix Cache Hit ratio 3.18 %, (4096 / 128704)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
```

作为对比，同一台机器上用 `--kv-cache-dtype auto`（即 bf16）在 `batch=16` 下运行同一工作负载，要么 OOM，要么在内存压力下产生小得多的批次。每 token 内存成本中 KV 缓存那一半消失了。

## 值得关注的点

- **KV 受限工作负载的吞吐量上升。** 长上下文解码主要由 KV 缓存内存决定；减半后在相同的 `npu_mem` 下有效批次大小翻倍。解码吞吐量随之上升。
- **TTFT 略有变化。** 预填充注意力读取 FP8-KV 剖析数据，其每 token 成本略有不同（注意力内核会即时做 dtype 转换）。通常长预填充上小幅受益，短预填充上中性。
- **模拟器不做精度声明。** 与其他所有旋钮一样，`--kv-cache-dtype fp8` 是一个*延迟 / 内存*旋钮，不是数值精度旋钮。模拟器不校验 FP8 KV 是否在真实 vLLM 中产生正确输出；那是 vLLM 的问题。模拟器只收取正确的字节与延迟。

## 相关示例

- **[前缀缓存](./prefix-caching)**：正交，经常组合使用。每 token KV 减半加上前缀块复用，会叠加内存节省。
- **[CXL 内存](./cxl-memory)**：应对内存压力的另一种方式——溢出到第二层而不是原地压缩。

## 了解更多

- **[模拟器 → KV 缓存与内存](../../simulator/scheduling/kv-cache-and-memory)**：`bytes_per_block` 公式以及 `kv_fp` 如何流入调度器的内存检查。
- **[性能剖析器 → 输出数据包](../../profiler/output-bundle)**：variant 命名（`bf16` 对比 `bf16-kvfp8` 对比 `fp8` 对比 `fp8-kvfp8`）以及剖析器如何发出每一个。
