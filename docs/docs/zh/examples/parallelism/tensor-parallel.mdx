---
title: 张量并行 (TP)
sidebar_position: 1
---

# 张量并行 (TP)

> **本示例演示：** 将单个实例的稠密权重分片到多张 GPU 上，并加入 TP-ALLREDUCE 集合通信。

最简单的非平凡并行。一个服务实例，但权重沿 head 维度切分到 N 张 GPU 上。每个 attention `o_proj` 和 MLP `down_proj` 都以一个 ALLREDUCE 收尾。

## 前置条件

- 已配置好模拟器容器（[模拟器安装](../../getting-started/installation/simulator)）
- 随附的 RTXPRO6000 剖析结果，`Qwen3-32B` 在 TP=2 下无需重新剖析。

## 集群配置

`configs/cluster/single_node_single_instance.json`（从随附配置略作修改，改用 `Qwen/Qwen3-32B` 且 `tp_size=2`）：

```json title="configs/cluster/single_node_single_instance.json (edited: Qwen3-32B at tp_size=2)"
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
          "model_name": "Qwen/Qwen3-32B",
          "hardware": "RTXPRO6000",
          "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
          "num_npus": 2,
          "tp_size": 2,
          "pd_type": null
        }
      ]
    }
  ]
}
```

把 TP=1 变成 TP=2 的两个字段：

- `num_npus: 2`：两张 GPU 分配给这个实例。
- `tp_size: 2`：两张 GPU 都参与张量并行 ALLREDUCE。

（`pp_size` 默认为 `1`，所以 `num_npus = tp_size * pp_size = 2` 成立。）

## 运行

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_single_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/tp2_run.csv' \
  --log-interval 1.0
```

`--dtype bfloat16` 与 `Qwen3-32B` 的已剖析 variant 匹配。

## 预期输出

吞吐日志大约每秒打印一次：

```text
[42.0s] Avg prompt throughput: 1204.0 tokens/s, Avg generation throughput: 420.0 tokens/s
        ├─Running Instance[0]: 8 reqs, Waiting: 0 reqs, Total # 2 NPUs, Each NPU Memory Usage 88412.34 MB (89.912 % Used), Prefix Cache Hit ratio 4.21 %, (5312 / 126188)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
[43.0s] Avg prompt throughput: 1138.0 tokens/s, Avg generation throughput: 440.0 tokens/s
        ├─Running Instance[0]: 8 reqs, Waiting: 0 reqs, Total # 2 NPUs, Each NPU Memory Usage 88412.34 MB (89.912 % Used), Prefix Cache Hit ratio 4.19 %, (5312 / 126780)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
```

`outputs/tp2_run.csv` 每完成一个请求就有一行。规范 schema（12 列，所有时间均为 ns）记录在 **[模拟器 → 读取输出](../../simulator/reading-output)**：

```csv
instance id,request id,model,input,output,arrival,end_time,latency,queuing_delay,TTFT,TPOT,ITL
0,0,Qwen/Qwen3-32B,1472,133,4059740,178654321,174594581,3739551,4063716,1306794,"[1306794, ...]"
```

## 亮点

- **GPU 内存减半**（对比 TP=1）：因为每张 GPU 只持有权重的一半。观察吞吐日志中的 `npu_mem`，在 TP=2 的 Qwen3-32B 上应该看到大约 `~32 GB` 的权重加载量，而不是 `~64 GB`。
- **首 token 时间（TTFT）略有上升**（对比 TP=1，当两者都能装下时）：因为每个 attention/MLP 对都要支付一次 ALLREDUCE 往返。配置中的 `link_bw=16 GB/s` 是相关旋钮，调高它会缩小 TP 集合通信开销。
- **每输出 token 时间（TPOT）可能下降**：当模型在 TP=1 时受内存带宽限制时，每个 token 获得更多带宽，超过了集合通信开销。

## 相关示例

- **[流水线并行](./pipeline-parallel)**：把层切分到多张 GPU 上，而不是把层内的权重切分。
- **[专家并行](./expert-parallel)**：TP 在 MoE 上的对应物；把专家分片到多张 GPU 上。
- **[多实例 LOAD 路由](../disaggregated/multi-instance)**——通过复制*整个* TP 组来横向扩展，而不是把单个组变大。
