---
title: 子批交错
sidebar_position: 2
---

# 子批交错

> **本示例演示：** 把每个批次一分为二，GPU 稠密层运行其中一半，同时 PIM 注意力运行另一半，让两个设备都不会闲置。

[PIM 注意力卸载](../disaggregated/pim-attention-offload) 单独使用时常会回退预填充 TTFT：GPU 完成它的稠密层后，要等 PIM 在注意力上追上来。子批交错修复了这个问题。调度器把批次切成两半（`BATCH_1` 和 `BATCH_2`），轨迹生成器交替执行——一半的 GPU 工作与另一半的 PIM 工作重叠。两个设备都保持忙碌；总迭代时间降到两者中较慢者的量级。

这是 PIM 卸载的自然后续步骤，**没有 `--enable-attn-offloading` 就不要启用它**。

## 前置条件

- 已配置模拟器容器
- 为 `meta-llama/Llama-3.1-8B` 打包的 RTXPRO6000 剖析数据
- 一个 PIM 设备配置（`configs/pim/DDR4_8GB_3200_pim.ini`）；打包的 `single_node_pim_instance.json` 已经引用了它

## 集群配置

与 [PIM 注意力卸载](../disaggregated/pim-attention-offload) 相同的配置——`configs/cluster/single_node_pim_instance.json`。不需要任何配置改动；子批交错是运行时 CLI flag。

## 运行

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_pim_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --enable-attn-offloading \
  --enable-sub-batch-interleaving \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/pim_sub_batch_run.csv' \
  --log-level WARNING
```

两个 flag 协同工作：

- `--enable-attn-offloading` 把轨迹中的 GPU 注意力内核替换为 PIM 内核。
- `--enable-sub-batch-interleaving` 随后把每次迭代的批次切成两半，发出交错的轨迹：一半的 GPU 稠密层与另一半的 PIM 注意力重叠。

交错要求 `pp_size == 1`。交错的轨迹在每一个组边界处让两个子批都停在 transformer 块的中间，因此流水线阶段不会有单一的激活可交给下一阶段；模拟器在启动时拒绝这种组合，而不是发出无法调度的图。

## 预期输出

心跳块形状不变：

```text
[10.0s] Avg prompt throughput: 1436.0 tokens/s, Avg generation throughput: 620.0 tokens/s
        ├─Running Instance[0]: 8 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 63412.51 MB (64.499 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 14360)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
[11.0s] Avg prompt throughput: 1442.0 tokens/s, Avg generation throughput: 640.0 tokens/s
        ├─Running Instance[0]: 8 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 63486.51 MB (64.574 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 15802)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
```

**没有 `pim_busy` / `gpu_busy` 字段**——模拟器不跟踪设备利用率计数器。交错在发出的轨迹内部重叠迭代的 NPU 与 PIM 两半，因此唯一可见的效果是更短的迭代：比不带 `--enable-sub-batch-interleaving` 的同一配置更高的生成吞吐量和更低的 TPOT。分别运行两者并比较最终的 `Mean TPOT (ms)` 行。

`outputs/pim_sub_batch_run.csv` 与任何其他运行有相同的每请求 schema；变化的是每迭代的延迟，而不是列集合。

## 值得关注的点

- **预填充 TTFT 得到恢复。** 纯 PIM 卸载会回退预填充（PIM 的每通道算力比 GPU 的并行注意力单元窄）。有了交错，GPU 的稠密工作隐藏了大部分 PIM 预填充成本。
- **解码基本不变。** 解码注意力本来就受内存限制、对 PIM 友好，因此子批交错对解码密集型工作负载增益不大。收益集中在预填充侧。
- **半批粒度是唯一的旋钮。** 调度器总是 50/50 拆分。如果批次只有 1 个请求，交错静默地空操作（你无法在不破坏每请求语义的情况下把一个请求拆成两半）。
- **轨迹标签。** 如果你读取生成的轨迹文件（`astra-sim/inputs/runs/<run_id>/trace/...`），每一层携带的是 `BATCH_1` 或 `BATCH_2` misc 标签，而不是通常的 `NONE`。这确认交错确实被发出。

## 相关示例

- **[PIM 注意力卸载](../disaggregated/pim-attention-offload)** —— 前置条件。子批交错是它之上的恢复层。
- **[功耗建模](./power-modeling)**：在本示例旁边开启 `power:` 块，可以看到交错如何把能量重新分配到 NPU active 与 PIM 计算之间。

## 了解更多

- **[模拟器 → PIM 卸载](../../simulator/specialized/pim-offload)**：PIM 设备模型以及轨迹生成器如何发出 `PIM {channel}` / `PIM END` 标记。子批交错基于它们之上。
- **[参考 → 轨迹格式](../../reference/trace-format)**：`BATCH_1` / `BATCH_2` misc 标签语义。
