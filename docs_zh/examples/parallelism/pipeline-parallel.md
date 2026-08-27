---
title: 流水线并行 (PP)
sidebar_position: 2
---

# 流水线并行 (PP)

> **本示例演示：** 把模型的 decoder 层切分到多张 GPU 上（每个 GPU 一个阶段），使每次迭代以微批（micro-batch）的形式流经流水线。

PP 是与 TP 正交的轴：TP 在*层内*切分权重，PP 在*设备间*切分层。每张 GPU 运行 decoder block 栈中连续的一段，并把中间激活交给下一阶段。调度器把在途批数限制在 `pp_size`，轨迹生成器挑选阶段边界（总是在 transformer block 边界上，与 vLLM `get_pp_indices` 使用的切分规则相同），Chakra 为每个阶段 NPU 生成一个 `.et` 文件，并在这些边界处插入 send/recv。

## 前置条件

- 已配置好模拟器容器
- `meta-llama/Llama-3.1-8B` 的随附 RTXPRO6000 剖析结果

## 集群配置

流水线并行完全由多 GPU 实例上的 `pp_size` 驱动。随附的三个配置覆盖了它：`single_node_pp_instance.json`（4 张 GPU 作为 `pp=4`）、`single_node_tp_pp_instance.json`（`tp=2 x pp=2`）和 `single_node_moe_pp_instance.json`（MoE，`tp=2 x pp=2` 且 `ep=2`）。第一个：

```json title="configs/cluster/single_node_pp_instance.json"
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
          "num_npus": 4,
          "tp_size": 1,
          "pp_size": 4,
          "pd_type": null
        }
      ]
    }
  ]
}
```

关键字段：

- `num_npus: 4`、`tp_size: 1`、`pp_size: 4`：不变式是 `num_npus = tp_size * pp_size`，因此模拟器把 Llama-3.1-8B 的 32 个 decoder block 分成四个阶段、每阶段八个，每张 GPU 一个阶段，阶段内部没有 TP。
- 组合 TP × PP 时设置 `num_npus: 4, tp_size: 2, pp_size: 2`（即 `single_node_tp_pp_instance.json`）：两个阶段各 16 个 block，每个阶段再分片到两张 GPU 上。
- `pp_size` 不能超过模型的 `num_hidden_layers`——没有 decoder block 的流水线阶段会在启动前就被拒绝。

## 运行

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_pp_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/example_pp_run.csv' \
  --num-reqs 10
```

没有新的 CLI flag，并行度完全由集群配置驱动。换成 `single_node_tp_pp_instance.json` 或 `single_node_moe_pp_instance.json` 即可把 PP 与 TP、EP 组合起来。

## 预期输出

吞吐日志看起来与标准的单实例运行一样：

```text
[20.0s] Avg prompt throughput: 1436.0 tokens/s, Avg generation throughput: 540.0 tokens/s
        ├─Running Instance[0]: 8 reqs, Waiting: 0 reqs, Total # 4 NPUs, Each NPU Memory Usage 44032.19 MB (44.774 % Used), Prefix Cache Hit ratio 1.02 %, (1424 / 139612)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
[21.0s] Avg prompt throughput: 1502.0 tokens/s, Avg generation throughput: 560.0 tokens/s
        ├─Running Instance[0]: 8 reqs, Waiting: 0 reqs, Total # 4 NPUs, Each NPU Memory Usage 44118.19 MB (44.861 % Used), Prefix Cache Hit ratio 1.01 %, (1424 / 141114)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
```

与 TP=1 基线相比，有两点值得注意：

- **`npu_mem` 大约减半**（每张 GPU 只持有 decoder 层的一半，因此每设备的权重 + KV 缓存都变小了）。
- **短突发期间 `batch` 可能在较低值处饱和**，因为调度器在 `inflight == pp_size` 时停止下发，这种背压防止向流水线过度注入工作。

## 亮点

- **内存切分是真实的。** 每个阶段只持有自己那一份 decoder 层，因此每 GPU 的权重 + KV 缓存占用大约缩小到 1/`pp_size`。PP=2 可以装下在 TP=1 上装不下的模型。
- **阶段间激活传输是真实的。** 调高集群配置中的 `link_bw` / `link_latency` 会明显改变迭代时间，因为 Chakra 在阶段之间插入的 send/recv 节点与其他集合通信一样走模拟网络。可以用它来研究互连选型如何影响 PP 扩展。
- **流水线深度限制在途批数。** `inflight ≤ pp_size` 是 PP 驱动的调度约束。当 `pp_size=2` 且 token 预算允许 6 个批时，你会看到调度器在流水线中最多同时排队 2 个批。稳态流水线重叠（批 *k+1* 在阶段 0 上、批 *k* 在阶段 1 上）会自然地从 ASTRA-Sim 独立执行每个阶段的 `.et` 文件这一过程中涌现。
- **没有建模的内容。** 在单次迭代内部，批是按顺序穿越各阶段的单一整体——一次迭代*内部*没有微批拆分，也没有流水线调度方案（1F1B、交错等）可选。因此这些方案中会出现的填充/排空气泡不会出现；流水线的收益完全来自把连续迭代重叠最多 `pp_size` 层。
- **`--enable-sub-batch-interleaving` 在 `pp_size > 1` 时会被拒绝。** 交错轨迹会在每个组边界处把两个子批都留在 block 中间，因此阶段没有单一的激活可以交接。

## 相关示例

- **[张量并行](./tensor-parallel)**：层内对应的并行。TP × PP 组合是有效的，并且在大规模下很常见。
- **[多实例 LOAD 路由](../disaggregated/multi-instance)**：再上一级的扩展——跨实例复制完整的 TP × PP 组。

## 深入了解

- **[模拟器 → 并行机制](../../simulator/parallelism-mechanics)**：`num_npus`、`tp_size` 和 `pp_size` 如何校验，以及如何贯穿调度器 / 轨迹生成器。
- PP 的 `inflight` 列表位于 `serving/core/scheduler.py`；阶段边界在 `serving/core/trace_generator.py`（`_pp_stage_boundaries`）中选定，并在 `astra-sim/extern/graph_frontend/chakra/src/converter/llm_converter.py`（`get_stage_edges`、`convert_common` / `convert_prefill`）中连同 send/recv 插入一起被消费。
