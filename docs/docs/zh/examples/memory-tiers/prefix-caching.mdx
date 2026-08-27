---
title: 前缀缓存
sidebar_position: 1
---

# 前缀缓存

> **本示例演示：** 在具有共享 prompt 前缀的请求之间复用预先计算的 KV 缓存，包括跨实例共享的第二层 CPU 池。

对于许多请求共享系统提示词、RAG 上下文或长指令（例如 agent 轨迹）的工作负载，为每个请求重新计算预填充是浪费的。前缀缓存会保留前缀 KV 块（默认在 NPU 内存中；可选地在 CPU 或 CXL 中），并在命中时复用它们。

LLMServingSim 内置块哈希前缀缓存（移植自 vLLM v0.19.0 的块池），有三种形态：

1. **每实例 NPU 池**（默认，始终开启）。
2. **跨实例共享 CPU 池**：第二层前缀缓存，模拟挂接 LMCache 或 vLLM 的 `OffloadingConnector`。
3. **CXL 后备池**：与上相同，但位于 CXL 内存中。

## 前置条件

- 已配置模拟器容器
- 具有共享前缀的工作负载（打包的 `example_trace.jsonl` 有一些；真实的 ShareGPT 或 agentic 轨迹则有很多）

## 集群配置

最简单的配置使用 `configs/cluster/single_node_multi_instance.json`（一个节点上两个实例，无特殊内存配置）。共享 CPU 池通过运行时 CLI flag 开启，而不是通过配置：

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
        { "...": "second instance, identical" }
      ]
    }
  ]
}
```

`cpu_mem.mem_size`（这里为 512 GB）限制 CPU 前缀池可以增长到的上限。

## 运行

### 每实例前缀缓存（默认）

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_multi_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/prefix_default_run.csv'
```

`--enable-prefix-caching` 默认开启。前缀块保存在每个实例自己的 NPU 内存中；如果一个请求落在实例 A，其前缀命中了实例 B 上的缓存块，也不会发生复用。

### 共享 CPU 前缀池

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_multi_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --enable-prefix-caching --enable-prefix-sharing --prefix-storage CPU \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/prefix_cpu_pool_run.csv'
```

两个额外 flag：

- `--enable-prefix-sharing`：开启第二层池。
- `--prefix-storage CPU`：池位于 `cpu_mem`。其他选项：`CXL`（需要 `cxl_mem` 配置块）、`None`（仅 NPU）。

当 NPU 前缀被逐出时，它会溢出到 CPU 池而不是消失。**任何**实例上的请求现在都可以在查找时命中 CPU 池。

## 预期输出

启用共享 CPU 池后，吞吐量日志会增加前缀命中率计数器：

```text
[20.0s] Avg prompt throughput: 2412.0 tokens/s, Avg generation throughput: 820.0 tokens/s
        ├─Running Instance[0]: 6 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 63218.51 MB (64.301 % Used), Prefix Cache Hit ratio 41.82 %, (31024 / 74208)
        ├─Running Instance[1]: 4 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 63204.51 MB (64.287 % Used), Prefix Cache Hit ratio 42.11 %, (30298 / 71950)
        └─Node[0]: Total CPU Memory Usage 8192.00 MB, 1.600 % Used, Prefix Cache Hit ratio 36.04 %, (52664 / 146158)
```

各实例的比例是 NPU 层的命中；`Node` 行上的比例是共享 CPU 池的，它取代了每实例的 CPU 拆分，因为 `--enable-prefix-sharing --prefix-storage CPU` 使池成为节点级。

`prompt_t`（prompt 吞吐量）统计**所有**输入 token，包括从缓存服务的那些，与 vLLM 的报告约定一致。

## 值得关注的点

- **即使在共享前缀巨大的工作负载上，NPU 内存压力也保持有界。** CPU 池吸收逐出。
- **跨实例复用**是多副本部署的杀手级特性。没有前缀共享时，一个 90% 前缀重叠的工作负载在 N 个实例下，前缀缓存的效果实际上只剩 1/N。
- **当 CPU 内存成为瓶颈时，CXL 池是一个选项。** 设置 `--prefix-storage CXL` 并在集群配置中添加 `cxl_mem` 块（参见[CXL 内存层](./cxl-memory)）。此时池位于 CXL 内存中，按 CXL 延迟访问。
- **块感知跟踪。** 模拟器的 `prompt_t` 累加器包含前缀缓存命中 token，因此它报告的 prompt 吞吐量与 vLLM 一致（vLLM 也统计缓存 token）。

## 相关示例

- **[CXL 内存层](./cxl-memory)**：用 CXL 内存支撑前缀池。
- **[多实例 LOAD 路由](../disaggregated/multi-instance)** —— 本示例所基于的多实例基线。
