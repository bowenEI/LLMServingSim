---
title: DP+EP MoE
sidebar_position: 4
---

# DP+EP MoE

> **本示例演示：** 使用 `dp_group` 把专家并行延伸到多个实例。两个实例构成一个 2D ASTRA-Sim 拓扑，一个轴上是 TP，另一个轴上是 EP。

这是 LLMServingSim 能建模的最有趣的拓扑。两个服务实例各自运行自己的 TP 组，但通过跨实例 ALLTOALL **共享专家**。2D ASTRA-Sim 网络网格在 dim 0 上路由 TP-ALLREDUCE，在 dim 1 上路由 EP-ALLTOALL。

## 前置条件

- 已配置好模拟器容器
- `Qwen/Qwen3-30B-A3B-Instruct-2507` 的随附 RTXPRO6000 剖析结果
- 一个 agentic 数据集（或任何请求量足够让两个实例都忙起来的工作负载）

## 集群配置

`configs/cluster/single_node_moe_dp_ep_instance.json`：

```json title="configs/cluster/single_node_moe_dp_ep_instance.json"
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
          "model_name": "Qwen/Qwen3-30B-A3B-Instruct-2507",
          "hardware": "RTXPRO6000",
          "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
          "num_npus": 1, "tp_size": 1, "ep_size": 2, "dp_group": "A",
          "pd_type": null
        },
        {
          "model_name": "Qwen/Qwen3-30B-A3B-Instruct-2507",
          "hardware": "RTXPRO6000",
          "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
          "num_npus": 1, "tp_size": 1, "ep_size": 2, "dp_group": "A",
          "pd_type": null
        }
      ]
    }
  ]
}
```

把"两个独立实例"变成 DP+EP 集群的两个要素：

- 两个实例上的 **`dp_group: "A"`**，字符串相同的实例组成一个 DP 组。
- **`ep_size: 2`** 而 `tp_size: 1`：EP 跨越 DP 组（`ep_size > tp_size` 只有在设置了 `dp_group` 时才允许）。

`config_builder.py` 看到 DP 组后发出一个大小为 `[tp_size, dp_group_size] = [1, 2]` 的拓扑——最内层维度在前，当 `pp_size > 1` 时中间会插入一个 `pp_size` 维度。集合通信通过 `involved_dim` BoolList 按维度限定范围：

- TP-ALLREDUCE：`[True, False]`：只涉及 dim 0（实例内部，这里因为 `tp_size=1` 是无操作）
- EP-ALLTOALL：`[False, True]`：只涉及 dim 1（跨两个实例）

## 运行

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_moe_dp_ep_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --dataset 'workloads/swe-bench-qwen3-30b-a3b-50-sps0.2.jsonl' \
  --output 'outputs/dp_ep_moe_run.csv' \
  --num-reqs 1
```

flag 说明：

- 随附的 SWE-bench 风格 agentic 数据集很合适，因为每个会话有多个链式子请求，能让两个实例都保持活跃。
- `--num-reqs 1` 表示一个*会话*（多个子请求）。想要更长的运行就调大它。

## 预期输出

```text
[4.0s] Avg prompt throughput: 9063.0 tokens/s, Avg generation throughput: 1074.0 tokens/s
        ├─Running Instance[0]: 23 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 32634.88 MB (33.198 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 20285)
        ├─Running Instance[1]: 22 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 32981.38 MB (33.550 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 24147)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used (Instance[0]: 0.00 %, Instance[1]: 0.00 %)
[5.0s] Avg prompt throughput: 5342.0 tokens/s, Avg generation throughput: 1504.0 tokens/s
        ├─Running Instance[0]: 27 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 32987.38 MB (33.556 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 23234)
        ├─Running Instance[1]: 26 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 33312.88 MB (33.888 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 26861)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used (Instance[0]: 0.00 %, Instance[1]: 0.00 %)
```

这两行来自 [`bench/examples/RTXPRO6000/Qwen3-30B-A3B-Instruct-2507/outputs/sim.log`](https://github.com/casys-kaist/LLMServingSim/tree/main/bench/examples)，即已提交的 DP+EP 验证运行。心跳日志中没有任何内容点名 ALLTOALL 或 DP 组：波同步只表现为两个实例步调一致地推进，这就是为什么它们的 `Running` 计数彼此相差不超过 1。

`batch=4+4` 记号反映的是每实例批（实例 0 + 实例 1）。`alltoall` 字段显示波同步 ALLTOALL 消息大小，等于 `max(total_len_per_instance) * hidden_size * fp_size`。

## 亮点

- **专家权重跨实例拆分**，而不只是跨 GPU。`ep_size=2` 且共 128 个专家时，每个实例持有 64 个。与单实例 EP=1 相比，每 GPU 的权重内存大约减半。
- **两个实例共享一个 ASTRA-Sim 进程。** DP 组内的波同步调度意味着模拟器为两个实例生成的 `.et` 文件在 ALLTOALL 上共享 stream ID，迫使 ASTRA-Sim 阻塞到两个 NPU 都到达该集合通信为止。
- **空闲实例得到哑批（dummy batch）。** 当一个实例没有待处理的工作时，调度器合成一个 1-decode-token 的批，使它仍能参与该波的 ALLTOALL。同样，当一个实例提前结束时，它会继续生成哑批直到整个组结束。
- **`comm_size` 是同步的。** 即使实例 A 的批比实例 B 大得多，两者也向 ASTRA-Sim 传相同的 ALLTOALL 大小（取最大值），因此网络模型看到的是更重的那一侧。

## 相关示例

- **[专家并行](./expert-parallel)**：同一个 MoE 模型在单个实例上（一个 TP 组内的 EP）。
- **[多实例 LOAD 路由](../disaggregated/multi-instance)**——多实例的*非* DP 版本：不共享专家的独立副本。
- **[集群配置详解](../cluster-config-explained#dpep-the-topology-that-needs-more-explanation)**——`dp_group` 如何点亮 2D 拓扑的字段级讲解。
