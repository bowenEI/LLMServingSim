---
title: 预填充/解码拆分
sidebar_position: 2
---

# 预填充/解码拆分（P/D split）

> **本示例演示：** 将一个实例专门用于预填充、另一个专门用于解码，并在两者之间移交 KV 缓存。

预填充受计算限制且呈突发性。解码受内存带宽限制且平稳。将它们混在同一实例上会迫使做出妥协（长预填充拖住解码迭代，解码批次在小批量下无法充分利用算力）。将预填充和解码分离到不同实例，可以让各自针对自己的瓶颈进行调优，这是 DistServe 推广、现已成为生产 serving 标准的模式。

## 前置条件

- 已配置模拟器容器
- 为 `meta-llama/Llama-3.1-8B` 打包的 RTXPRO6000 剖析数据

## 集群配置

`configs/cluster/single_node_pd_instance.json`：

```json title="configs/cluster/single_node_pd_instance.json"
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
          "pd_type": "prefill",
          "tp_size": 1
        },
        {
          "model_name": "meta-llama/Llama-3.1-8B",
          "hardware": "RTXPRO6000",
          "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
          "pd_type": "decode",
          "tp_size": 1
        }
      ]
    }
  ]
}
```

唯一关键的字段：**`pd_type`**。

- `"prefill"`：该实例只运行预填充迭代。它接收请求，计算 prompt 的 KV 缓存，移交缓存，然后回到它的预填充队列。
- `"decode"`：该实例只对已完成预填充的请求做解码迭代。
- `null`（其他示例）：预填充+解码合并（默认）。

路由器会自动把新请求发送到 `"prefill"` 实例，在首个 token 生成后把请求转移到 `"decode"` 实例。KV 缓存转移成本通过实例间链路建模。

## 运行

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_pd_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/pd_split_run.csv' \
  --log-interval 1.0
```

## 预期输出

```text
[15.0s] Avg prompt throughput: 3104.0 tokens/s, Avg generation throughput: 620.0 tokens/s
        ├─Running Instance[0]: 8 reqs, Waiting: 2 reqs, Total # 1 NPUs, Each NPU Memory Usage 55412.51 MB (56.360 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 46560)
        ├─Running Instance[1]: 12 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 71238.51 MB (72.454 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 0)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used (Instance[0]: 0.00 %, Instance[1]: 0.00 %)
[16.0s] Avg prompt throughput: 3612.0 tokens/s, Avg generation throughput: 640.0 tokens/s
        ├─Running Instance[0]: 10 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 55486.51 MB (56.435 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 50172)
        ├─Running Instance[1]: 12 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 71402.51 MB (72.621 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 0)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used (Instance[0]: 0.00 %, Instance[1]: 0.00 %)
```

`P=` 与 `D=` 计数是按角色的批次大小。解码实例的 KV 缓存随请求不断转入而增长；预填充实例的 KV 缓存则受限于当前正在预填充的请求。

## 值得关注的点

- **TTFT 只由预填充实例决定**，没有解码负载与它竞争。可以通过独立扩展预填充副本轻松调优。
- **TPOT 由解码实例决定。** 缓存转移表现为预填充结束与首个解码步之间的一次性成本（通过 `link_bw` 建模）。
- **内存利用率差异显著。** 预填充实例的 KV 缓存只是"在途"；解码实例为每个活跃请求累积 KV 块。在长时间运行的工作负载下，解码实例通常是内存瓶颈。
- **生产级并行。** 这一模式由 [DistServe](https://arxiv.org/abs/2401.09670) 和 Mooncake 推广。调优预填充:解码副本比例是主要旋钮，对突发性的长上下文工作负载，可以试试 `num_instances: 3`（两个预填充、一个解码）。

## 相关示例

- **[多实例 LOAD 路由](./multi-instance)**：角色对等的版本。是比较 TTFT/TPOT 的实用基线。
- **[集群配置详解](../cluster-config-explained#3-per-instance-level)** —— `pd_type` 的字段级参考。
