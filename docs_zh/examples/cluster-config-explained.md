---
title: 集群配置详解
sidebar_position: 1
---

# 集群配置详解

LLMServingSim 中的每次模拟都由 **一个 JSON 文件** 驱动：*集群配置*（cluster config）。它刻画了完整的硬件拓扑：多少个节点、每个节点多少个实例、每个实例运行在哪些 GPU 上、内存如何布局，以及模型如何并行化。

一旦读懂了这个文件，本节中的每个示例都只是同一形态的小变体。

## 最小可用配置

这就是 `configs/cluster/single_node_single_instance.json`：能运行的最小配置：

```json title="configs/cluster/single_node_single_instance.json"
{
  "num_nodes": 1,
  "link_bw": 16,
  "link_latency": 20000,
  "nodes": [
    {
      "num_instances": 1,
      "cpu_mem": {
        "mem_size": 512,
        "mem_bw": 256,
        "mem_latency": 0
      },
      "instances": [
        {
          "model_name": "meta-llama/Llama-3.1-8B",
          "hardware": "RTXPRO6000",
          "npu_mem": {
            "mem_size": 96,
            "mem_bw": 1597,
            "mem_latency": 0
          },
          "num_npus": 1,
          "tp_size": 1,
          "pd_type": null
        }
      ]
    }
  ]
}
```

也就是：**一个节点**、**一个实例**，在**一张 RTXPRO6000 GPU** 上运行 **Llama-3.1-8B**，**TP=1**（无并行）。

该文件有三个嵌套层级。我们自上而下逐一讲解。

## 1. 顶层：集群

```json
{
  "num_nodes": 1,
  "link_bw": 16,
  "link_latency": 20000,
  "nodes": [...]
}
```

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `num_nodes` | int | 集群中的物理节点数 |
| `link_bw` | float 或 float[] | ASTRA-Sim 拓扑链路带宽，单位 **GB/s** |
| `link_latency` | float 或 float[] | ASTRA-Sim 拓扑链路延迟，单位 **ns** |
| `nodes` | array | 每个节点一项（长度必须等于 `num_nodes`） |

对于多节点配置（例如机架里的两台机器），设置 `num_nodes: 2` 并添加第二个节点条目。`link_bw` / `link_latency` 可以是：

- 标量，广播到每个 ASTRA-Sim 拓扑维度
- 数组，每个最终的 `network.yml::npus_count` 维度一个值

**可选的顶层字段：**

| 字段 | 用途 |
| --- | --- |
| `cxl_mem` | CXL 内存扩展配置（参见 [CXL 内存层级](./memory-tiers/cxl-memory)） |

## 2. 节点层级

```json
{
  "num_instances": 1,
  "cpu_mem": {
    "mem_size": 512,
    "mem_bw": 256,
    "mem_latency": 0
  },
  "instances": [...]
}
```

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `num_instances` | int | 该节点上运行多少个服务实例 |
| `cpu_mem.mem_size` | float | 主机 CPU 内存容量（**GB**） |
| `cpu_mem.mem_bw` | float | CPU 内存带宽（**GB/s**） |
| `cpu_mem.mem_latency` | float | CPU 内存延迟（**ns**） |
| `instances` | array | 每个实例一项（长度 = `num_instances`） |

**可选的节点级字段：**

| 字段 | 用途 |
| --- | --- |
| `cpu_mem.pim_config` | `configs/pim/` 中某个 PIM 设备配置的名称（参见 [PIM attention 卸载](./disaggregated/pim-attention-offload)） |
| `power` | 功耗模型系数（参见 [功耗建模](./advanced/power-modeling)） |

## 3. 实例层级

真正的工作发生在这里。一个*实例*就是一个独立的 LLM 服务副本：一个模型、一种并行策略和一块 GPU。

```json
{
  "model_name": "meta-llama/Llama-3.1-8B",
  "hardware": "RTXPRO6000",
  "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
  "num_npus": 1,
  "tp_size": 1,
  "pd_type": null
}
```

### 必填字段

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `model_name` | string | Hugging Face 模型 id。必须匹配 `configs/model/{model_name}.json` 中的某个配置 |
| `hardware` | string | 硬件标签。必须匹配 `profiler/perf/{hardware}/`（例如 `RTXPRO6000`、`H100`） |
| `npu_mem` | object | 每 GPU 内存：`mem_size`（GB）、`mem_bw`（GB/s）、`mem_latency`（ns） |
| `pd_type` | string\|null | `"prefill"`、`"decode"`，或 `null` 表示预填充+解码合并 |

### 并行度字段（至少需要一个）

| 字段 | 类型 | 默认值 | 含义 |
| --- | --- | --- | --- |
| `num_npus` | int | 推断 | 该实例的总 GPU 数，等于 `tp_size * pp_size` |
| `tp_size` | int | 推断 | 张量并行度 |
| `pp_size` | int | `1` | 流水线并行度 |
| `ep_size` | int | `tp_size`（MoE）/ `1`（稠密模型） | 专家并行度 |
| `dp_group` | string\|null | `null` | 字符串相同的实例组成一个数据并行组，每轮迭代波同步；对 MoE 而言它们还在组内共享专家 |

你只需要提供 `num_npus` 或 `tp_size` **其中之一**，另一个会被推断出来。所以：

- `tp_size: 4` → `num_npus = 4 * pp_size`（PP 默认为 1，因此是 4）
- `num_npus: 4, pp_size: 2` → `tp_size = 2`

**需要记住的并行度规则：**

- `num_npus == tp_size * pp_size`（始终成立）
- `pp_size <= num_hidden_layers`：流水线阶段只能在 transformer block 边界上切割，因此阶段不能为空
- TP 与 EP 共享**同一批** GPU：稠密层做 TP-ALLREDUCE，MoE 层做 EP-ALLTOALL
- 没有 `dp_group` 时：`ep_size <= tp_size`
- 有 `dp_group` 时：EP 可以扩展到单个实例的 GPU 之外（参见 DP+EP 示例）
- 对 MoE 模型：`ep_size` 必须整除 `num_local_experts`

### 可选的高级字段

| 字段 | 用途 |
| --- | --- |
| `placement` | 逐层 / 逐块权重 + KV 缓存放置（参见 [CXL 内存](./memory-tiers/cxl-memory)） |
| 14 个运行时覆盖项中的任意一个 | 每实例调度器 / 内存 / dtype 设置（见下文） |

## 每实例运行时覆盖项

到目前为止，上面所有内容描述的都是*硬件*。实例还可以携带**运行时设置**，这正是异构集群得以实现的原因：`python -m serving` 的 14 个 flag 可以按实例重新指定，因此同一次运行中的预填充实例与解码实例可以以完全不同的方式调度。

优先级只有一层：

```
instances[i].<field>   >   --<field> on the CLI   >   built-in default
```

写在实例里的字段对该实例生效。其他每个实例保持 CLI 所给的值。实例之间没有合并，也没有继承。

### 14 个可覆盖字段

| 字段 | 覆盖 | 按实例设置的典型原因 |
| --- | --- | --- |
| `max_num_seqs` | `--max-num-seqs` | 在预填充实例上收窄批，在解码实例上放宽 |
| `max_num_batched_tokens` | `--max-num-batched-tokens` | 大的预填充块，小的解码步 |
| `long_prefill_token_threshold` | `--long-prefill-token-threshold` | 防止单个长提示独占预填充实例 |
| `block_size` | `--block-size` | 在碎片化影响不大的地方使用更粗的块 |
| `dtype` | `--dtype` | 以两种精度服务同一个模型 |
| `kv_cache_dtype` | `--kv-cache-dtype` | 仅在解码实例上用 FP8 KV |
| `enable_chunked_prefill` | `--enable-chunked-prefill` | 在预填充上分块，在解码上从不分块 |
| `enable_prefix_caching` | `--enable-prefix-caching` | 在前缀重复处启用缓存，不重复处跳过 |
| `npu_mem.mem_util` | `--npu-memory-utilization` | 只给一个实例留余量 |
| `reserve_full_isl` | `--reserve-full-isl` | 在 decode-only 实例上放宽准入 |
| `enable_local_offloading` | `--enable-local-offloading` | 在一个实例上做权重卸载 |
| `enable_attn_offloading` | `--enable-attn-offloading` | 在一个实例上做 PIM attention |
| `enable_sub_batch_interleaving` | `--enable-sub-batch-interleaving` | 在卸载实例上重叠 NPU 与 PIM |
| `enable_block_copy` | `--enable-block-copy` | 在一个实例上按层忠实还原专家方差 |

注意 `mem_util` 的位置：它是**唯一**嵌套在另一个对象内部的覆盖项，因为它存在的意义是缩放 `npu_mem.mem_size`，并且遵循该块的 `mem_*` 命名。

```json
"npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0, "mem_util": 0.8}
```

### 一个异构示例

`configs/cluster/single_node_heterogeneous.json` 运行一个 Qwen3-32B 预填充实例和一个解码实例，两者都是 TP=2，但调度器设置相反：

```json title="configs/cluster/single_node_heterogeneous.json (instances only)"
"instances": [
  {
    "model_name": "Qwen/Qwen3-32B",
    "hardware": "RTXPRO6000",
    "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
    "num_npus": 2,
    "tp_size": 2,
    "pd_type": "prefill",
    "max_num_seqs": 32,
    "max_num_batched_tokens": 8192,
    "enable_chunked_prefill": true,
    "enable_prefix_caching": true
  },
  {
    "model_name": "Qwen/Qwen3-32B",
    "hardware": "RTXPRO6000",
    "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
    "num_npus": 2,
    "tp_size": 2,
    "pd_type": "decode",
    "max_num_seqs": 256,
    "max_num_batched_tokens": 0,
    "enable_chunked_prefill": false,
    "enable_prefix_caching": false
  }
]
```

解读：预填充实例接纳少量序列但拥有较大的 token 预算，因为一次预填充步骤需要较长的分块。解码实例接纳大量序列且不设 token 上限，因为每次解码步骤每个序列只贡献一个 token。

`configs/cluster/single_node_pd_per_instance_config.json` 是同一思路的 Llama-3.1-8B 版本，另外还覆盖了 `long_prefill_token_threshold`、`block_size`、`dtype` 和 `kv_cache_dtype`。

:::caution[`max_num_batched_tokens: 0` 不是无限]
`0` 表示"无限制"，但调度器随后会应用 `min(max_num_batched_tokens, max_position_embeddings)`。对 Qwen3-32B 而言那是 40960，所以上面的解码实例实际运行在 40960，而不是无界。参见 **[模型配置](../reference/model-config)**。
:::

### 不能按实例设置的内容

其余 15 个 flag 是集群级的。写在实例对象内部不会有任何作用：没有任何键读取它，也不会报错。

| 作用域 | Flags |
| --- | --- |
| 集群 / 后端 | `--cluster-config`、`--network-backend` |
| 路由器（按定义跨实例） | `--request-routing-policy`、`--expert-routing-policy` |
| 共享的更低层 KV 层级 | `--enable-prefix-sharing`、`--prefix-storage` |
| 工作负载（每次运行一个） | `--dataset`、`--num-reqs`、`--skip-prefill` |
| 运行机制 | `--output`、`--run-id`、`--inputs-root`、`--save-trace-text`、`--keep-inputs`、`--log-interval`、`--log-level` |

### 两种被拒绝的组合

两者都会在加载配置时针对*生效*值按实例检查：

- `enable_sub_batch_interleaving` 但没有 `enable_attn_offloading`——没有东西可以与 NPU 子批重叠。
- `enable_sub_batch_interleaving` 搭配 `pp_size > 1`：交错轨迹会在每个阶段边界处把两个子批都留在 block 中间，因此流水线阶段没有单一的隐藏状态可以交接。

完整语义（包括 `dtype` 的三级回退和 `mem_util` 的范围检查）见 **[参考 → 集群配置](../reference/cluster-config#runtime-overrides-optional)**。

## DP+EP：需要更多解释的拓扑

当多个实例共享同一个 `dp_group` 时，它们构成一个**多维 ASTRA-Sim 拓扑**，最内层维度在前：`[tp_size, dp_group_size]`，当 `pp_size > 1` 时为 `[tp_size, pp_size, dp_group_size]`。集合通信按维度限定范围：

- **TP ALLREDUCE** 只跑在 TP 维上（实例内部）
- **EP** 跑在 DP 维上，当 EP 跨越单个实例的 GPU 时还包括 TP 维。PP 维从不参与——vLLM 的 EP 组固定了流水线阶段。

DP 组中的所有实例共享**一个** ASTRA-Sim 进程，采用波同步调度。MoE 专家权重按 `ep_size` 分片：每个实例持有 `num_local_experts / ep_size` 个专家。

具体示例：Qwen3-30B-A3B 有 128 个专家。使用 `tp_size=1, ep_size=2, dp_group="A"` 并配两个实例时，每个实例持有 64 个专家。每个 token 的激活通过 ALLTOALL 穿越 DP 组。

这就是 [DP+EP MoE](./parallelism/dp-ep-moe) 示例。

## `config_builder.py` 会拿这个文件做什么

启动模拟器时，`serving/core/config_builder.py` 读取集群配置，并在 `astra-sim/inputs/` 下**生成三个 ASTRA-Sim 输入文件**：

| 生成的文件 | 由什么驱动 |
| --- | --- |
| `network/network.yml` | `link_bw`、`link_latency`、`[tp_size, (pp_size,) dp_group_size]` 拓扑 |
| `system/system.json` | 内存带宽、调度策略、每个维度的集合通信实现 |
| `memory/memory_expansion.json` | CXL 设备及任何扩展内存层级 |

这些不需要手写，每次运行都会根据集群配置重新生成。

## 随附配置

仓库在 `configs/cluster/` 下随附了 **27** 个可运行的配置。没有链接的那些可以直接运行，但没有专属示例页面：

| 配置 | 形态 | 由谁使用 |
| --- | --- | --- |
| `single_node_single_instance.json` | 1 节点、1 实例、Llama-3.1-8B、TP=1 | 默认配置；[张量并行](./parallelism/tensor-parallel) 把它提升到 `tp_size=2` |
| `single_node_single_instance_H100.json` | H100 上的 Llama-3.1-70B、TP=4 | — |
| `single_node_multi_instance.json` | 1 节点、2 实例 | [多实例 LOAD 路由](./disaggregated/multi-instance) |
| `single_node_4_instance_2TP.json` | 1 节点、4 个 TP=2 实例 | — |
| `single_node_heterogeneous.json` | 运行设置相反的 P/D 对 | [每实例运行时覆盖项](#per-instance-runtime-overrides) |
| `single_node_pd_instance.json` | 预填充/解码分离 | [预填充/解码拆分](./disaggregated/prefill-decode-split) |
| `single_node_pd_per_instance_config.json` | 带每实例运行时限制的 P/D | [每实例运行时覆盖项](#per-instance-runtime-overrides) |
| `single_node_pp_instance.json` | 4 张 GPU 作为 `pp=4` | [流水线并行](./parallelism/pipeline-parallel) |
| `single_node_tp_pp_instance.json` | 4 张 GPU 作为 `tp=2 x pp=2` | [流水线并行](./parallelism/pipeline-parallel) |
| `single_node_moe_single_instance.json` | Qwen3-MoE、TP=2 EP=2 | [专家并行](./parallelism/expert-parallel) |
| `single_node_moe_dp_ep_instance.json` | 一个 DP 组中的 2 个 MoE 实例、EP=2 | [DP+EP MoE](./parallelism/dp-ep-moe) |
| `single_node_dp_instance.json` | DP=2 x TP=2、稠密模型、4 张 GPU | — |
| `rtx4090_single_instance.json` | RTX 4090、Llama-3.1-8B TP=1、校准过 `mem_util` | [验证](../validation) |
| `rtx4090_tp2_instance.json` | 2x RTX 4090 作为 `tp=2`、Llama-3.1-8B。需要先有 RTX4090 的 `tp=2` 剖析结果——随附的只有 `tp1`，因此按原样运行会抛出 `FileNotFoundError` | [性能剖析器](../profiler/overview) |
| `rtx4090_multi_instance.json` | 2 个独立的 TP=1 RTX 4090 实例 | — |
| `single_node_moe_dp_tp_instance.json` | DP=2 x TP=2 MoE、EP=2、4 张 GPU | — |
| `single_node_moe_dp_pp_instance.json` | DP=2 x PP=2 MoE、EP=2、4 张 GPU | — |
| `single_node_moe_dp_tp_pp_instance.json` | DP=2 x TP=2 x PP=2 MoE、EP=4、8 张 GPU | — |
| `single_node_moe_multi_instance.json` | 2 个 MoE 实例、无 DP 组 | — |
| `single_node_moe_pd_instance.json` | 带 P/D 分离的 MoE | — |
| `single_node_moe_pp_instance.json` | MoE 在 4 张 GPU 上、`tp=2 x pp=2`、`ep=2` | [流水线并行](./parallelism/pipeline-parallel) |
| `single_node_cxl_instance.json` | CXL 内存扩展 | [CXL 内存层级](./memory-tiers/cxl-memory) |
| `single_node_memory_instance.json` | 权重 / KV `placement` 控制 | [CXL 内存层级](./memory-tiers/cxl-memory) |
| `single_node_pim_instance.json` | 支持 PIM 的内存 + 功耗模型 | [PIM attention 卸载](./disaggregated/pim-attention-offload) |
| `single_node_power_instance.json` | 启用功耗建模 | [功耗建模](./advanced/power-modeling) |
| `dual_node_multi_instance.json` | 2 节点、每节点 2 实例 | 多节点配置 |
| `dual_node_moe_dp_ep_intra_inter_instance.json` | 2 节点 DP+EP MoE、按维度的 `link_bw` / `link_latency` | [DP+EP MoE](./parallelism/dp-ep-moe) |

## 下一步

现在你已经会读集群配置了，挑一个示例看看同一形态如何产生截然不同的拓扑：

- **[张量并行](./parallelism/tensor-parallel)**：最简单的非平凡示例：单实例上的 TP=2。
- **[多实例 LOAD 路由](./disaggregated/multi-instance)**——展示 `num_instances > 1` 的效果。
- **[DP+EP MoE](./parallelism/dp-ep-moe)**：这个模拟器能建模的最有趣的拓扑。
