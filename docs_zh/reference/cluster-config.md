---
sidebar_position: 1
title: 集群配置
---

# 集群配置 schema

通过 `--cluster-config` 传入的 JSON 文件的逐字段正式 schema。带示例的引导式讲解见 **[示例 → 集群配置详解](../examples/cluster-config-explained)**。本页是**查找参考**：每个字段、每个类型、每个默认值。

## 文件位置

配置位于 `configs/cluster/<name>.json`。模拟器在启动时读取一次该文件，`serving/core/config_builder.py` 生成派生的 ASTRA-Sim 输入文件（`network.yml`、`system.json`、`memory_expansion.json`）。

## 顶层

```json
{
  "num_nodes": 1,
  "link_bw": 16,
  "link_latency": 20000,
  "nodes": [...],
  "cxl_mem": {...}
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `num_nodes` | int | ✓ |  | 集群中的物理节点数 |
| `link_bw` | float 或 float[] | ✓ |  | ASTRA-Sim 拓扑链路带宽，单位 **GB/s**。标量适用于每个拓扑维度；数组必须匹配最终 `network.yml::npus_count` 的秩 |
| `link_latency` | float 或 float[] | ✓ |  | ASTRA-Sim 拓扑链路延迟，单位 **ns**。标量适用于每个拓扑维度；数组必须匹配最终 `network.yml::npus_count` 的秩 |
| `nodes` | array | ✓ |  | 长度必须等于 `num_nodes` |
| `cxl_mem` | object | 可选 | 缺省 | CXL 内存扩展（见下文） |

示例：如果 `network.yml` 最终会有 `npus_count: [4, 2]`，你可以设置 `link_bw: [900, 100]` 和 `link_latency: [0, 20000]`，为每个拓扑维度分配不同的带宽 / 延迟。

## `cxl_mem`（顶层，可选）

```json
"cxl_mem": {
  "mem_size": 1024,
  "mem_bw": 60,
  "mem_latency": 250,
  "num_devices": 4
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `mem_size` | float | ✓ | 每设备容量，单位 **GB** |
| `mem_bw` | float | ✓ | 每设备带宽，单位 **GB/s** |
| `mem_latency` | float | ✓ | 访问延迟，单位 **ns** |
| `num_devices` | int | 可选（默认 `1`） | CXL 设备数（`cxl:0` 到 `cxl:N-1`） |

存在时，实例可以在其 `placement` 字段中引用 `cxl:N`。

## 每节点（`nodes[i]`）

```json
{
  "num_instances": 2,
  "cpu_mem": {"mem_size": 512, "mem_bw": 256, "mem_latency": 0},
  "instances": [...],
  "power": {...},
  "cpu_mem.pim_config": "DDR4_8GB_3200_pim"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `num_instances` | int | ✓ | 该节点上的服务实例数 |
| `cpu_mem` | object | ✓ | 主机 CPU 内存配置（见下文） |
| `instances` | array | ✓ | 长度必须等于 `num_instances` |
| `power` | object | 可选 | 功耗模型配置（见下文） |

### `cpu_mem`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `mem_size` | float | ✓ | 主机 CPU 内存容量，单位 **GB** |
| `mem_bw` | float | ✓ | CPU 内存带宽，单位 **GB/s** |
| `mem_latency` | float | ✓ | CPU 内存延迟，单位 **ns** |
| `pim_config` | string | 可选 | `configs/pim/` 中某个 PIM 设备配置的名称。见 **[PIM 配置](./pim-config)** |

### `power`（可选）

在该节点上启用功耗模型。完整 schema 见 **[示例 → 功耗建模](../examples/advanced/power-modeling)**。顶层结构：

```json
"power": {
  "base_node_power": 60,
  "npu": {"<hardware>": {...}},
  "cpu": {...},
  "dram": {...},
  "link": {...},
  "nic": {...},
  "storage": {...}
}
```

| 子字段 | 必填 | 说明 |
| --- | --- | --- |
| `base_node_power` | ✓ | 常开主机平台功耗，单位 **W** |
| `npu.<hardware>.idle_power` | ✓ | NPU 空闲瓦数 |
| `npu.<hardware>.standby_power` | ✓ | NPU 计算后待机瓦数 |
| `npu.<hardware>.active_power` | ✓ | NPU 活跃计算瓦数 |
| `npu.<hardware>.standby_duration` | ✓ | 计算后保持待机的时间，单位 **ns** |
| `cpu.idle_power`、`cpu.active_power`、`cpu.util` | ✓ | CPU 基线 + 利用率比例 |
| `dram.dimm_size`、`dram.idle_power`、`dram.energy_per_bit` | ✓ | DIMM 大小、空闲功耗、每比特能量 |
| `link.num_links`、`link.idle_power`、`link.energy_per_bit` | ✓ | 网络链路功耗 |
| `nic.num_nics`、`nic.idle_power` | ✓ | NIC 数量与基线 |
| `storage.num_devices`、`storage.idle_power` | ✓ | 存储设备 |

表格无法展示的三条规则：

- **功耗建模在集群范围内是全有或全无。** 如果*任何*节点省略 `power`，`config_builder.py` 会为**每个**节点静默禁用功耗建模。没有按节点选择加入的机制。
- **`npu` 需要为该节点上每个不同的 `hardware` 提供一个条目。** 键是实例的 `hardware` 字符串，节点上的每个实例都必须能找到自己的键。异构节点每个硬件标签需要一个块。
- **`dram.dimm_size` 和 `dram.idle_power` 在 `--enable-attn-offloading` 下变为可选。** 启用 PIM 后，两者改由 PIM 配置提供（`dimm_size` 来自派生的每通道容量，`idle_power` 来自 INI 的 `idle_power`），只有 `dram.energy_per_bit` 保持必填。见 **[PIM 配置](./pim-config)**。

## 每实例（`instances[i]`）

```json
{
  "model_name": "Qwen/Qwen3-32B",
  "hardware": "RTXPRO6000",
  "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
  "num_npus": 2,
  "tp_size": 2,
  "pp_size": 1,
  "ep_size": 1,
  "dp_group": null,
  "pd_type": null,
  "max_num_seqs": 128,
  "max_num_batched_tokens": 2048,
  "placement": {...}
}
```

### 必填字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `model_name` | string | HF id。必须匹配 `configs/model/<model_name>.json` 下的某个配置（见 **[模型配置](./model-config)**） |
| `hardware` | string | 硬件标签。必须匹配 `profiler/perf/<hardware>/` |
| `npu_mem.mem_size` | float | 每 GPU NPU 内存，单位 **GB** |
| `npu_mem.mem_bw` | float | 每 GPU NPU 内存带宽，单位 **GB/s** |
| `npu_mem.mem_latency` | float | 每 GPU NPU 内存延迟，单位 **ns** |
| `pd_type` | string \| null | `"prefill"`、`"decode"` 或 `null`（组合） |

### 并行度（`num_npus` / `tp_size` 至少一个）

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `num_npus` | int | 由 `tp_size * pp_size` 推断 | 该实例的总 GPU 数 |
| `tp_size` | int | 由 `num_npus // pp_size` 推断 | 张量并行度 |
| `pp_size` | int | `1` | 流水线并行度 |
| `ep_size` | int | `tp_size`（MoE）/ `1`（稠密） | 专家并行度 |
| `dp_group` | string \| null | `null` | 组 ID。字符串相同的实例组成一个数据并行组，每次迭代波同步；对于 MoE，它们还在组内共享专家 |

**约束：**

- `num_npus == tp_size * pp_size`（始终成立）
- `pp_size <= num_hidden_layers`：流水线阶段在 transformer 块边界上切分，因此一个阶段不能为空
- 无 `dp_group` 时：`ep_size <= tp_size`
- 对于 MoE：`ep_size` 必须整除 `num_local_experts`
- `dp_group` 的所有成员必须在 `tp_size`、`pp_size` 和 `ep_size` 上一致
- 对于 `dp_group` 中的 **MoE** 模型，`ep_size` 是组内 EP 的总度数：它必须能被 `dp_group_size` 整除，且 `ep_size / dp_group_size <= tp_size`。对于**稠密**模型，`ep_size` 不是要在组内分摊的度数，因此两项检查都不适用——稠密模型上的纯数据并行受支持（`single_node_dp_instance.json`）

### 运行时覆盖（可选）

`python -m serving` 的参数中恰好有 **14** 个可以按实例重新指定，让一次集群运行可以承载异构实例——一个 `max_num_seqs` 收紧的 prefill 实例紧挨着一个 `max_num_seqs` 放开的 decode 实例，或者两个 `mem_util` 不同的实例。每一个都在 `serving/__main__.py` 的 `_build_instance_runtime_configs()` 中解析。

**优先级**只有一层深度，不做合并：

```
instances[i].<field>   >   --<field> on the CLI   >   built-in default
```

查找逻辑字面上就是 `instance.get("<field>", args.<field>)`，因此集群配置中存在的字段对该实例生效，其余每个实例保留 CLI 值。

| 字段 | 类型 | CLI 回退 | 说明 |
| --- | --- | --- | --- |
| `max_num_seqs` | int | `--max-num-seqs` | 该实例的最大活跃序列数。`0` 表示不限 |
| `max_num_batched_tokens` | int | `--max-num-batched-tokens` | 该实例的每迭代 token 预算。`0` 表示不限 |
| `long_prefill_token_threshold` | int | `--long-prefill-token-threshold` | 分块预填充的每请求分块上限 |
| `block_size` | int | `--block-size` | KV 缓存块大小（token 数） |
| `dtype` | string | `--dtype` | 该实例的权重 / 剖析 dtype |
| `kv_cache_dtype` | string | `--kv-cache-dtype` | KV 缓存 dtype，用于内存核算与剖析变体选择 |
| `enable_chunked_prefill` | bool | `--enable-chunked-prefill` | 在该实例的调度器中启用分块预填充 |
| `enable_prefix_caching` | bool | `--enable-prefix-caching` | 启用该实例的本地前缀缓存 |
| `npu_mem.mem_util` | float | `--npu-memory-utilization` | `npu_mem.mem_size` 中可用于权重加 KV 缓存的比例。KV 容量为 `mem_size * mem_util - 模型权重`，划分为 `block_size` 个块 |
| `reserve_full_isl` | bool | `--reserve-full-isl` | 仅当请求的整个序列都能容纳时才准入，而不仅是其第一个分块 |
| `enable_local_offloading` | bool | `--enable-local-offloading` | 为该实例发出带本地卸载的图转换 |
| `enable_attn_offloading` | bool | `--enable-attn-offloading` | 为该实例发出 PIM 注意力卸载 |
| `enable_sub_batch_interleaving` | bool | `--enable-sub-batch-interleaving` | 为该实例启用子批交错 |
| `enable_block_copy` | bool | `--enable-block-copy` | 在重复的 transformer 块间复用同一个块轨迹 |

#### `npu_mem.mem_util` 是唯一嵌套的覆盖项

其余 13 个是实例对象上的普通键。`mem_util` 位于 `npu_mem` 块**内部**，因为它的唯一职责是缩放 `mem_size`，并且遵循该块的 `mem_*` 命名：

```json
{
  "model_name": "meta-llama/Llama-3.1-8B",
  "hardware": "RTXPRO6000",
  "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0, "mem_util": 0.8},
  "tp_size": 1,
  "pd_type": null,
  "max_num_seqs": 64
}
```

它必须是 `(0, 1]` 中的数字——它是一个*比例*，所以是 `0.9`，绝不是 `90`。其他任何值都会在启动时直接报错而不是被钳制。

:::caution[KV 缓存饱和时将其与实测运行对齐]
`mem_util` 决定 KV 缓存的大小，而这只有在一次运行真正把它填满时才会体现在结果中——低于上限时不会有任何抢占，容量不可见。在有富余的显卡上，保持默认值即可。

当一次运行确实饱和时，默认值是错误的数字：模拟器不建模 vLLM 的激活峰值或 CUDA 上下文，因此这里的 `0.9` 给出的 KV 缓存**多于** vLLM 在相同比例下得到的。从 bench 运行的 `meta.json` 读取 `kv_cache.num_gpu_blocks`，并选择其 **KV Cache Initialization** 横幅报告相同块数的那个 `mem_util`。在自带的 RTX 4090 示例上——24 GB，钉在其上限——该值是 `0.833919`，它把运行从 -20.7% TTFT / +12.9% TPOT 带到 +0.6% / +0.2%。见 [验证](../validation) 与 [KV 缓存与内存](../simulator/scheduling/kv-cache-and-memory)。
:::
#### `0` 表示不限，但有一个例外

`max_num_seqs` 和 `max_num_batched_tokens` 经由一个 `_runtime_limit()` 辅助函数路由，它将 `0` 映射为无穷大：

- `max_num_seqs: 0` — 真正的无界并发。
- `max_num_batched_tokens: 0` — 实际上**并非**无界。调度器随后计算
  `min(max_num_batched_tokens, max_position_embeddings)`，因此有效预算变为 **[模型配置](./model-config)** 中的模型上下文长度。对于
  `microsoft/Phi-mini-MoE-instruct` 那是 4096，而不是无穷大。

其他数值覆盖项都不特殊对待 `0`：
`long_prefill_token_threshold: 0` 表示*禁用*（无每请求上限），与 CLI 参数一致，而 `block_size: 0` 直接无效。

#### `dtype` 解析有三层，而不是两层

`dtype` 是唯一在 CLI 之下还有回退的覆盖项：

```
instances[i].dtype   >   --dtype   >   model config torch_dtype   >   bfloat16
```

解析后的值必须是 `float16` / `bfloat16` / `float32` / `fp8` / `int8` 之一，并且它选择剖析**变体文件夹**，因此对应的 `profiler/perf/<hardware>/<model>/<variant>/tp<N>/` 数据包必须存在。`kv_cache_dtype` 也按实例校验——只有 `auto` 或 `fp8`。

#### 校验门

两种组合在配置加载时按实例被拒绝：

| 被拒绝的组合 | 报错 | 原因 |
| --- | --- | --- |
| 没有 `enable_attn_offloading: true` 的 `enable_sub_batch_interleaving: true` | `RuntimeError` | 没有可与 NPU 子批重叠的东西 |
| `pp_size > 1` 下的 `enable_sub_batch_interleaving: true` | `RuntimeError` | 交错轨迹在每个阶段边界处让两个子批都停在块中间，因此流水线阶段没有单一的隐藏状态可向下传递 |

两道门读取的都是*有效*值，因此从 CLI 继承 `--enable-sub-batch-interleaving` 到某个本地禁用了 `enable_attn_offloading` 的实例上，同样会失败。

#### **不**按实例生效的参数

其余 15 个 CLI 参数是集群级的。在实例对象内设置它们会被静默忽略——没有任何东西读取该键：

| 范围 | 参数 |
| --- | --- |
| 集群 / 后端 | `--cluster-config`、`--network-backend` |
| 路由器（按定义跨实例） | `--request-routing-policy`、`--expert-routing-policy` |
| 共享的低层 KV 池 | `--enable-prefix-sharing`、`--prefix-storage` |
| 工作负载（每次运行一个） | `--dataset`、`--num-reqs`、`--skip-prefill` |
| 运行管道 | `--output`、`--run-id`、`--inputs-root`、`--save-trace-text`、`--keep-inputs`、`--log-interval`、`--log-level` |

#### 完整示例

`configs/cluster/single_node_pd_per_instance_config.json` 用不同的调度器限制拆分 prefill 和 decode，`configs/cluster/single_node_heterogeneous.json` 将它们与不同的分块预填充设置配对。带注解的讲解见
**[示例 → 集群配置详解](../examples/cluster-config-explained#per-instance-runtime-overrides)**。

### `placement`（可选）

逐层 / 逐块的权重 + KV 缓存放置规则。带完整示例见
**[示例 → CXL 扩展内存](../examples/memory-tiers/cxl-memory)**。

```json
"placement": {
  "default": {"weights": "npu", "kv_loc": "npu", "kv_evict_loc": "cpu"},
  "blocks": [
    {"blocks": "0-3", "weights": "cxl:0", "kv_loc": "npu", "kv_evict_loc": "cpu"}
  ],
  "layers": {
    "embedding": {"weights": "cxl:1", "kv_loc": "npu", "kv_evict_loc": "cpu"}
  }
}
```

| 子字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `default` | object | ✓ | 不在 `blocks` 或 `layers` 中的层 / 块的兜底规则 |
| `blocks` | array | 可选 | 按解码器块区间的覆盖 |
| `layers` | object | 可选 | 按命名层的覆盖 |

每个规则对象有三个字符串字段：

| 字段 | 允许的值 | 说明 |
| --- | --- | --- |
| `weights` | `npu` / `cpu` / `cxl:<id>` | 该层的权重所在位置 |
| `kv_loc` | `npu` / `cpu` / `cxl:<id>` | 活跃 KV 块所在位置（仅注意力层） |
| `kv_evict_loc` | `npu` / `cpu` / `cxl:<id>` | 被逐出的 KV 块溢出的位置 |

`blocks` 字符串是短横线与逗号分隔的区间：
`"0-3"`、`"4-7"`、`"8,9,10"`、`"11-23"`。层名键必须匹配架构 YAML 中的规范层名。

## 校验规则

结构校验，在 `config_builder.py` 中：

- `num_nodes == len(nodes)`，且每节点 `num_instances == len(instances)`。
- 顶层必须同时存在 `link_bw` 和 `link_latency`。
- 每个实例都需要 `model_name`、`hardware`、`npu_mem` 和 `pd_type`；`npu_mem` 需要 `mem_size`、`mem_bw`、`mem_latency`。`cpu_mem` 以及（若存在）`cxl_mem` 也需要同样的三个键。
- `num_npus == tp_size * pp_size`，且 `pp_size <= num_hidden_layers`。
- `dp_group` 必须是字符串或 `null`，共享同一 `dp_group` 的所有实例必须在 `tp_size`、`pp_size` **和** `ep_size` 上一致。
- 硬件文件夹必须存在于 `profiler/perf/<hardware>/<model_name>/<variant>/tp<tp_size>/`。

内存校验，在 `memory_model.py` 中，按 **GPU** 评估（权重已按 `tp_size` / `ep_size` 分片）：

- `weight_per_gpu <= npu_mem.mem_size`，忽略 `mem_util`。失败时抛出 `Model size ...GB exceeds total NPU memory ...GB`。
- `npu_mem.mem_size * mem_util - weight_per_gpu` 必须至少能容纳一个 `block_size` token 的 KV 块。这是两者中更紧的一条，也是 `mem_util` 真正把控的一条：把 `mem_util` 降得足够低就会在这里失败，错误消息会给出请求的字节数、权重字节数和差额。

运行时校验，每实例，在 `serving/__main__.py` 中：

- `dtype` 必须是五个受支持的值之一，`kv_cache_dtype` 必须是 `auto` / `fp8` 之一。
- `npu_mem.mem_util` 必须是 `(0, 1]` 中的数字。
- 上文的两道子批交错门。

## 下一步

- **[模型配置](./model-config)**：`model_name` 所解析文件的 schema。
- **[PIM 配置](./pim-config)**：`cpu_mem.pim_config` 所解析文件的 schema。
