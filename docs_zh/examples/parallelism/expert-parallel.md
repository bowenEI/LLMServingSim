---
title: 专家并行 (MoE)
sidebar_position: 3
---

# 专家并行 (MoE)

> **本示例演示：** 在单个实例内把 MoE 专家分片到多张 GPU 上，并在 MoE block 周围加入 ALLTOALL 集合通信。

对于混合专家（mixture-of-experts）模型，跨 GPU 分摊工作有两种选择：TP（把专家内部的每个线性层分片）或 EP（把不同的专家放到不同的 GPU 上）。EP 与 MoE 天然契合，因为它*只*涉及专家；层的其余部分仍然使用 TP。

默认情况下 `ep_size` 与 `tp_size` 共享同一批 GPU：TP 跑稠密部分（qkv、o_proj、gate_up_proj、down_proj），EP 跑专家。

## 前置条件

- 已配置好模拟器容器
- `Qwen/Qwen3-30B-A3B-Instruct-2507` 的随附 RTXPRO6000 剖析结果

## 集群配置

`configs/cluster/single_node_moe_single_instance.json`：

```json title="configs/cluster/single_node_moe_single_instance.json"
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
          "model_name": "Qwen/Qwen3-30B-A3B-Instruct-2507",
          "hardware": "RTXPRO6000",
          "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
          "num_npus": 2,
          "tp_size": 2,
          "ep_size": 2,
          "pd_type": null
        }
      ]
    }
  ]
}
```

MoE 专属旋钮：

- `ep_size: 2`：专家在这 2 张 GPU 上拆分。
- TP=2 + EP=2 共享同一批 2 张 GPU。稠密层在同一对上跑 TP-ALLREDUCE，MoE 层跑 EP-ALLTOALL。

Qwen3-30B-A3B 有 **128 个专家**，因此每张 GPU 持有 **64 个**。`ep_size` 整除 `num_local_experts` 的约束会在启动时检查。

## 运行

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_moe_single_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/moe_ep2_run.csv' \
  --log-interval 1.0
```

`--expert-routing-policy` 默认为 `BALANCED`。选项：

- `BALANCED`：对负载均衡训练门控的闭式鸽笼近似（确定性、快速）
- `RR`：按 token 轮询（round-robin）
- `RAND`：按 token 均匀随机（可设种子）
- `CUSTOM`：可在 `serving/core/gate_function.py` 中插拔

## 预期输出

```text
[10.0s] Avg prompt throughput: 903.0 tokens/s, Avg generation throughput: 320.0 tokens/s
        ├─Running Instance[0]: 4 reqs, Waiting: 0 reqs, Total # 2 NPUs, Each NPU Memory Usage 72104.88 MB (73.298 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 9142)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
[11.0s] Avg prompt throughput: 921.0 tokens/s, Avg generation throughput: 330.0 tokens/s
        ├─Running Instance[0]: 4 reqs, Waiting: 0 reqs, Total # 2 NPUs, Each NPU Memory Usage 72180.88 MB (73.375 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 10063)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
```

与同一模型上假设的 TP=2 EP=1 运行相比：每次前向传播现在增加两个 ALLTOALL 阶段（把 token 分发给专家 GPU，再收集回来），而不是在每个稠密线性层上做 TP-ALLREDUCE。每个 token 只激活 8 个专家，每 token 的计算量大幅缩小。

## 亮点

- **专家权重内存减半**（对比 EP=1）：每张 GPU 持有 128 个专家中的 64 个。按 Qwen3-30B-A3B 的专家大小，每张 GPU 能省下数 GB。
- **ALLTOALL 取代 TP-ALLREDUCE** 出现在 MoE block 中。每次迭代 ALLTOALL 的 `comm_size` 是 `local_tokens * hidden_size * fp`：与*激活* token 数成正比，而不是权重——因此延迟随批大小扩展，而不是模型大小。
- **每个 token 的激活专家数**比专家总数更重要。Qwen3-30B-A3B 激活 128 个中的 8 个，这才是内部专家内核上的负载，与 EP 度数无关。

## 相关示例

- **[DP+EP MoE](./dp-ep-moe)**：把 EP 扩展到多个实例。当 EP 需要增长到超过单个实例的 GPU 时，这就是你要用的。
- **[张量并行](./tensor-parallel)**：稠密模型对应的并行。
