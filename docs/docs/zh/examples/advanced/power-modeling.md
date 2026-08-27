---
title: 功耗建模
sidebar_position: 1
---

# 功耗建模

> **本示例演示：** 开启逐节点功耗模型，让模拟器在吞吐量日志中输出实时瓦数，并在运行结束时输出逐组件的能耗分解。

功耗模型是可选加入的：只有当节点的配置包含 `power:` 块时，它才跟踪功耗。打包的 `single_node_power_instance.json` 是一个开箱即用的示例。

## 前置条件

- 已配置模拟器容器
- 为 `meta-llama/Llama-3.1-8B` 打包的 RTXPRO6000 剖析数据（无需额外剖析）

## 集群配置

`configs/cluster/single_node_power_instance.json` 在节点的常规 `instances` 之外添加了一个 `power:` 块：

```json title="configs/cluster/single_node_power_instance.json（节选）"
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
          "pd_type": null,
          "tp_size": 1
        }
      ],
      "power": {
        "base_node_power": 60,
        "npu": {
          "RTXPRO6000": {
            "idle_power": 35,
            "standby_power": 300,
            "active_power": 600,
            "standby_duration": 18
          }
        },
        "cpu":     {"idle_power": 10, "active_power": 200, "util": 0.15},
        "dram":    {"dimm_size": 32,  "idle_power": 2.0,   "energy_per_bit": 6.0},
        "link":    {"num_links": 1,   "idle_power": 5,     "energy_per_bit": 4.0},
        "nic":     {"num_nics": 1,    "idle_power": 20},
        "storage": {"num_devices": 2, "idle_power": 5}
      }
    }
  ]
}
```

`npu.<hardware>` 键按实例的 `hardware` 字段查找功耗系数，因此多硬件集群为每种硬件类型列出一条。

逐字段的 schema（`base_node_power`、`idle_power`、`standby_duration`、`energy_per_bit` 等）参见[集群配置 → power](../../reference/cluster-config)。

## 运行

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_power_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/power_run.csv' \
  --log-interval 1.0
```

不需要新的 CLI flag。集群配置中 `power:` 块的存在就是触发器；移除此块即可得到不跟踪功耗的基线运行。

## 预期输出

心跳块会新增一条 `Avg power consumption` 分支：

```text
[42.0s] Avg prompt throughput: 1204.0 tokens/s, Avg generation throughput: 420.0 tokens/s
        ├─Running Instance[0]: 8 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 88412.34 MB (89.912 % Used), Prefix Cache Hit ratio 4.21 %, (5312 / 126188)
        ├─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
        └─Avg power consumption: 712.4 W
[43.0s] Avg prompt throughput: 1138.0 tokens/s, Avg generation throughput: 440.0 tokens/s
        ├─Running Instance[0]: 8 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 88412.34 MB (89.912 % Used), Prefix Cache Hit ratio 4.19 %, (5312 / 126780)
        ├─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
        └─Avg power consumption: 698.1 W
```

这个标签没有说明的两件事。它是**区间平均值**，不是瞬时读数：`get_current_power()` 把自上次心跳以来累积的能量除以经过的时间。而且它是一个**集群级**的总数，对所有节点求和——不是每节点——因此在多节点运行中，你无法从这一行做归因。逐节点的拆分要到最终汇总才出现。

该数字覆盖 NPU、CPU、DRAM、链路、NIC、存储，以及每个节点常开的基础功耗。

运行结束时，模拟器打印逐组件的能耗分解：

```text
─────── Power summary (node 0) ───────
   NPU active     :   12,453 J  (78%)
   NPU standby    :    1,012 J   (6%)
   NPU idle       :       89 J   (1%)
   CPU            :    1,233 J   (8%)
   DRAM           :      442 J   (3%)
   Link           :      388 J   (2%)
   Base + NIC + storage : 332 J  (2%)
   ─────────────────────────────────
   Total energy   :   15,949 J
```

这个分解才是可操作的输出。`NPU active` 占主导的运行是计算受限的；`NPU idle` 显著的是利用不足；`Link` 能量不成比例的是 ALLREDUCE 受限（当 `tp_size > 1` 时值得检查）。

## 值得关注的点

- **吞吐量 vs. 瓦数的权衡。** 调高 `--max-num-seqs` 会同时提高吞吐量和 `NPU active` / `standby` 时间，但斜率因工作负载而异——每 token 能耗在解码密集型负载上改善，在预填充密集型负载上恶化。
- **Standby 与 idle 的差距。** `standby_duration`（内核结束后的 ns 数）决定 NPU 多久回落到 `idle_power`。突发性工作负载在 `idle` 上花更多时间；稳态工作负载保持在 `standby` / `active`。`NPU idle > NPU standby` 通常意味着工作负载没有让 GPU 饱和。
- **基础节点功耗是常数。** 主机侧消耗（`base_node_power`）不取决于模拟器在做什么；它是能效比较需要考虑的常开开销。

## 相关示例

- **[子批交错](./sub-batch-interleaving)** —— 与功耗模型配合得很干净。重叠 PIM 注意力与 GPU 计算会同时改变吞吐量和能耗分解。
- **[CXL 内存](../memory-tiers/cxl-memory)** —— 添加 `cxl_mem` 设备与逐设备放置规则会给心跳块增加一个 `CXL[...]` 分支（仅在 `--prefix-storage CXL` 时）；能耗汇总随后会包含 CXL 传输能耗。

## 了解更多

- **[模拟器 → 功耗模型](../../simulator/specialized/power-model)**：逐组件的数学、NPU 状态机，以及 `standby_duration` 如何参与。
- 实现位于 `serving/core/power_model.py`。
