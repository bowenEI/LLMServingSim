---
title: 多实例 LOAD 路由
sidebar_position: 1
---

# 多实例与 LOAD 路由

> **本示例演示：** 在同一节点上运行两个独立的 serving 实例，并使用 vLLM 风格的负载感知请求路由。

这是最简单的"横向扩展"模式：在多个实例上复制同一模型，让路由器为每个新请求选择负载最轻的实例。这正是真实生产部署（vLLM、TGI、SGLang）在负载均衡器下所做的。

## 前置条件

- 已配置模拟器容器
- 为 `meta-llama/Llama-3.1-8B` 打包的 RTXPRO6000 剖析数据

## 集群配置

`configs/cluster/single_node_multi_instance.json`：

```json title="configs/cluster/single_node_multi_instance.json"
{
  "num_nodes": 1,
  "link_bw": 16,
  "link_latency": 20000,
  "nodes": [
    {
      "num_instances": 2,
      "cpu_mem": {"mem_size": 512, "mem_bw": 256, "mem_latency": 0},
      "instances": [
        {
          "model_name": "meta-llama/Llama-3.1-8B",
          "hardware": "RTXPRO6000",
          "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
          "pd_type": null,
          "tp_size": 1
        },
        {
          "model_name": "meta-llama/Llama-3.1-8B",
          "hardware": "RTXPRO6000",
          "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
          "pd_type": null,
          "tp_size": 1
        }
      ]
    }
  ]
}
```

两个要点：

- `num_instances: 2` 与匹配的 `instances` 数组长度。
- 每个实例相互独立，同一模型、同一硬件，**没有** `dp_group`（因此它们不共享专家，也不进行波同步）。

## 运行

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_multi_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/multi_instance_run.csv' \
  --request-routing-policy LOAD \
  --log-interval 1.0
```

`--request-routing-policy LOAD` 是默认值，这里显式写出是为了清晰。可选值：

- `LOAD`：vLLM 风格的负载最轻优先——得分 `waiting * 4 + running`
- `RR`：纯轮询
- `RAND`：随机选择
- `CUSTOM`：可在 `serving/core/router.py` 中自定义

## 预期输出

```text
[20.0s] Avg prompt throughput: 2412.0 tokens/s, Avg generation throughput: 820.0 tokens/s
        ├─Running Instance[0]: 6 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 63218.51 MB (64.301 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 74208)
        ├─Running Instance[1]: 4 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 63204.51 MB (64.287 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 71950)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used (Instance[0]: 0.00 %, Instance[1]: 0.00 %)
[21.0s] Avg prompt throughput: 2508.0 tokens/s, Avg generation throughput: 860.0 tokens/s
        ├─Running Instance[0]: 6 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 63290.51 MB (64.374 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 75462)
        ├─Running Instance[1]: 5 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 63276.51 MB (64.360 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 73204)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used (Instance[0]: 0.00 %, Instance[1]: 0.00 %)
```

路由器会优先填充负载较轻的实例。使用 LOAD 策略时，待处理 token（running + waiting）和活跃 KV 缓存占用都会影响选择，与 vLLM 使用的算法相同。

输出 CSV 与往常一样，每个完成的请求一行；每行有一个 `instance_id` 列，因此你可以按副本拆分。

## 值得关注的点

- **典型工作负载下吞吐量约为单实例的 2 倍**，但受共享主机带来的 PCIe / 链路争用影响（通过 `link_bw` 建模）。
- **内存线性翻倍**：模型被完全复制。权重内存没有免费的午餐；这正是 TP / EP / DP+EP 要解决的问题。
- **每实例独立的 KV 缓存。** 前缀缓存默认按实例独立，落在实例 1 上的请求无法复用实例 0 上计算过的前缀，除非启用前缀共享（参见[前缀缓存](../memory-tiers/prefix-caching)）。

## 相关示例

- **[张量并行](../parallelism/tensor-parallel)**：使用 2 块 GPU 的另一种方式（一个更大的实例，而不是两个副本）。
- **[预填充/解码拆分](./prefill-decode-split)**：多实例，但每个实例承担*专业化*角色。
- **[DP+EP MoE](../parallelism/dp-ep-moe)**：用于 MoE 的多实例，带跨实例专家共享。
