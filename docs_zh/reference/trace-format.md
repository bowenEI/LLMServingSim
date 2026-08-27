---
sidebar_position: 4
title: 轨迹文件格式
---

# 轨迹文件格式

模拟器的 `trace_generator.py` 构建每个批的轨迹，Chakra 转换器将其变成 ASTRA-Sim 消费的 `.et` 文件。本页是该轨迹的**逐字段规范**。

轨迹通常**在内存中**直接交给转换器，每个层一个字段元组，永远不会变成文本：转换器在模拟器进程内运行，所以先把字段格式化成填充列、再拆开纯属开销。下面的文本形式仍然精确地表达了字段的含义，而且当你用 `--save-trace-text` 请求时写出的也正是它——所以在检查模拟器发出了什么时，它依然是应当阅读的格式。

关于该轨迹如何产生的*内部机制*，见 **[模拟器 → 轨迹生成](../simulator/trace-generation)**。

## 文件位置

```
astra-sim/inputs/runs/<run_id>/trace/<hardware>/<model>/instance_<i>_batch_<b>.txt
```

每个（实例 × 批）一个文件，位于运行专属的 ASTRA-Sim 输入根目录下——仅在传入 `--save-trace-text` 时写出。默认情况下根本不会产生文本文件；行直接进入转换器。

这也包括事件处理器的轨迹（`event_handler.txt`），它与任何其他轨迹一样由行构建。

## 文件结构

```
COLOCATED		model_parallel_NPU_group: {pp_size}		pp_stage_boundaries: 73,145,217
{num_layers}
Layername    comp_time    input_loc    input_size    weight_loc    weight_size    output_loc    output_size    comm_type    comm_size    misc
embedding_0    5621    REMOTE:0    40    LOCAL    1050673152    LOCAL    81920    NONE    0    NONE
layernorm_0    1240    LOCAL    81920    LOCAL    8192    LOCAL    81920    NONE    0    NONE
qkv_proj_0    8324    LOCAL    81920    LOCAL    25165824    LOCAL    245760    NONE    0    NONE
...
sampler_291    25933    LOCAL    2565120    LOCAL    0    REMOTE:0    40    NONE    0    NONE
```

### 头部（第 1–3 行）

| 行 | 内容 | 含义 |
| --- | --- | --- |
| 1 | `{mode}\t\tmodel_parallel_NPU_group: {pp_size}` + 可选 `\t\tpp_stage_boundaries: {i1},{i2},…` | 模式标记，后跟以双制表符分隔的 `key: value` 对。`model_parallel_NPU_group` 是流水线并行度。`pp_stage_boundaries` 仅在 `pp_size > 1` 时写出：第一个阶段之后的每个阶段开始的 `pp_size - 1` 个层行索引，在任何前置的 `kv_load`/`kv_evict` 行之后计数 |
| 2 | `{num_layers}` | 后面跟随的行数，**包括**任何 `kv_load` / `kv_evict` 行 |
| 3 | 列头 | 字段名 |

模式标记来自实例的 `pd_type`：

| 标记 | `pd_type` | 转换器路径 |
| --- | --- | --- |
| `COLOCATED` | `null` | 组合的 prefill + decode |
| `PREFILL` | `"prefill"` | 向配对的 decode NPU 添加逐层 KV SEND |
| `DECODE` | `"decode"` | 添加对应的 RECV |

任何其他 `pd_type` 都会在轨迹生成时抛出 `ValueError: Unknown instance type`。

### 层行

每行有 11 个字段，由 `serving/core/utils.py::_FMT` 写成**左对齐列**——`Layername` 最小 30 字符，其余每个 15 字符，**并且除最后一个字段外每个字段后都有一个显式空格**。没有制表符分隔。

那个尾部空格是承重的。`{:<15}` 会填充短于列的值，但对已经填满列的值什么也不输出，因此一个 15 字符的字段会直接顶到下一个字段上，读者会把两者看成合并成一个。`ALLREDUCE:1,0,0`——一个带三维 `involved_dim` 的 `comm_type`——恰好 15 个字符。把宽度当作最小列宽，而不是保证。两个读者（`trace_generator` 自己的重读和 Chakra 转换器）都按任意空白切分（分别是 `re.findall(r'\S+', line)` 和 `line.strip().split()`），因此列宽仅为人类可读性服务，任何字段都不能包含空格。

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `Layername` | string | 规范层名 + 索引（例如 `qkv_proj_0`、`attention_31`） |
| `comp_time` | int | 计算延迟，单位**纳秒** |
| `input_loc` | enum | 输入张量所在位置（见 [内存位置](#内存位置)） |
| `input_size` | int | 输入张量大小，单位字节 |
| `weight_loc` | enum | 该层权重所在位置 |
| `weight_size` | int | 权重大小，单位字节 |
| `output_loc` | enum | 输出张量将被写入的位置 |
| `output_size` | int | 输出张量大小，单位字节 |
| `comm_type` | enum | 该层之后的集合通信类型（见 [通信](#通信类型)） |
| `comm_size` | int | 集合通信消息大小，单位字节。当 `comm_type` 为 `NONE` 时通常为 `0`，但**并不总是**：在 `PREFILL` 轨迹上，`qkv_proj` 在这里携带逐层 P/D KV 传输量，同时 `comm_type` 保持 `NONE`（见 [下文](#无集合通信时的-comm_size)） |
| `misc` | string | 杂项标签（子批交错等；通常为 `NONE`） |

## 内存位置

`input_loc`、`weight_loc` 和 `output_loc` 字段使用以下之一：

| 值 | 含义 | 由谁提供 |
| --- | --- | --- |
| `LOCAL` | NPU 内存 | 每实例 NPU |
| `REMOTE:{node_id}` | 指定节点上的 CPU 内存 | 每节点 `cpu_mem` |
| `CXL:{device_id}` | CXL 设备内存 | 顶层 `cxl_mem` 块 |
| `STORAGE` | 存储层（仅功耗模型使用） | （无） |

数字 id 匹配 `astra-sim/astra-sim/system/AstraMemoryAPI.hh` 中的 C++ 枚举：

| 符号 | 值 |
| --- | --- |
| `LOCAL` | 1 |
| `REMOTE` | 2 |
| `CXL` | 3 |
| `STORAGE` | 4 |

它们必须在轨迹与 C++ 枚举之间保持同步；不匹配会导致静默的错误计数。

### 第一层和最后一层必须使用 REMOTE

Chakra 转换器从**第一**层的 `input_loc` 发出 `MEM_LOAD_NODE`，从**最后**层的 `output_loc` 发出 `MEM_STORE_NODE`。两者都必须是 `REMOTE:{node_id}`（CPU 侧）：模拟器把请求进入 / 离开 NPU 建模为主机侧传输。

这就是为什么上面的示例中 `embedding_0` 有 `input_loc=REMOTE:0`、`sampler_*` 有 `output_loc=REMOTE:0`。`MEM_STORE_NODE` 按最后一行的 `output_size` 定大小——采样出的 token id，每序列 4 字节——而不是按它的 `input_size`，后者是 sampler 在 NPU 上消费的 logits 张量。

## 通信类型

`comm_type` 字段选择该层之后 ASTRA-Sim 运行的集合通信：

| 值 | 含义 | 何时发出 |
| --- | --- | --- |
| `NONE` | 无集合通信 | 大多数层 |
| `ALLREDUCE` | 在所涉维度上执行 all-reduce | `o_proj` 和 `down_proj` 之后（TP > 1） |
| `ALLTOALL` | all-to-all 分发 / 合并 | MoE 块周围（EP 感知） |

### 维度限定

对于多维 ASTRA-Sim 拓扑（DP+EP 布局），`comm_type` 可以带**维度限定后缀**：

| 后缀 | 含义 |
| --- | --- |
| `ALLREDUCE` | 默认，所有维度都涉及 |
| `ALLREDUCE:1,0` | 维度 0 = 涉及（`True`），维度 1 = 不涉及（`False`）。即在 2D `[tp, dp]` 拓扑中仅 TP 的 ALLREDUCE |
| `ALLTOALL:0,1` | 维度 0 = 不涉及，维度 1 = 涉及。即跨 DP 组的仅 EP 的 ALLTOALL |

Chakra 转换器通过 `_parse_comm_type` 解析这些，并把 `involved_dim` BoolList 写入 `.et` 文件。ASTRA-Sim 的 `Workload::issue_comm()` 读取 BoolList，并在指定的维度上路由集合通信。

## 无集合通信时的 comm_size

在 `PREFILL` 轨迹上，每个 `qkv_proj` 行都携带非零的 `comm_size`，同时 `comm_type` 保持 `NONE`。这不是矛盾：转换器的 prefill 路径在每个层的 KV 投影之后发出点对点 SEND 而不是集合通信，而 SEND 只需要大小、源、目标和标签——没有要命名的集合通信类型。

该值是**逐层、逐秩的 K+V** 字节数，遵循 `kv_cache_dtype`。它刻意**不是**该层的 `output_size`，后者是整个 QKV 激活：读取它会把 Q 也算进去，使传输量虚高 `(q_dim + 2 * kv_dim) / (2 * kv_dim)`——在 Llama-3.1-8B 上是 3 倍。

其他地方，`comm_type` 为 `NONE` 时 `comm_size` 为 `0`。

## 特殊标记

一些层被标记包裹：

### `kv_load` / `kv_evict`（分层 KV 召回）

配置了低层 KV 层（`--prefix-storage CPU` 或 `CXL`）时，从它召回块的那一步会在第一个真实层**之前**前置最多两行：

```
kv_load    0    LOCAL    0    REMOTE:0    8388608    LOCAL    0    NONE    0    NONE
kv_evict   0    LOCAL    0    REMOTE:0    2097152    LOCAL    0    NONE    0    NONE
```

它们不是计算：`comp_time` 为 `0`，字节数放在 `weight_size` 中，因此转换器把它们的费用算作对 `weight_loc` 所命名的层的内存传输——即实例的 `placement` 中的 `kv_evict_loc`，而不是 `kv_loc`。

每行仅在其字节数非零时发出，因此一步可以有两者、其一或都没有。没有 `--prefix-storage` 时就没有可召回的较低层，两个计数始终为 `0`，因此两行都永不出现。`batch.evict` 在每种模式下都是 `0`：从 NPU 逐出不花任何代价，因为数据要么是已完成请求的缓存，要么早已在关键路径之外写下去了。

两个值得知道的后果：

- 头部第 2 行的 `{num_layers}` 计数包含这些行。
- `pp_stage_boundaries` 索引在它们被剥离**之后**计数，因此无论一步是否召回了什么，索引都保持稳定。

### 层名后缀

每行的 `Layername` 都会追加 `_{i}`，其中 `i` 是该行在整个文件中的索引——*包括*任何 `kv_load` / `kv_evict` 行。因此同一模型的同一层在不同迭代上可以携带不同的后缀，后缀是标识符而不是层号。`EXPERT` 和 `PIM` 标记行是例外：它们原样写出，不带后缀。

### `EXPERT {i}` / `EXPERT END`（MoE）

包裹每秩的专家计算：

```
EXPERT 0
moe_expert_local_3_rank0    1842    LOCAL    524288    LOCAL    9437184    LOCAL    524288    ALLTOALL    524288    NONE
EXPERT END
EXPERT 1
moe_expert_local_3_rank1    1804    LOCAL    524288    LOCAL    9437184    LOCAL    524288    ALLTOALL    524288    NONE
EXPERT END
```

ASTRA-Sim 在秩 `i` 上并行运行每个 `EXPERT {i}` 块，在周围的 ALLTOALL 处同步。

### `PIM {channel}` / `PIM END`（PIM 卸载）

包裹 PIM 侧的注意力计算：

```
PIM 0
pim_attention_3    4126    LOCAL    245760    LOCAL    0    LOCAL    245760    NONE    0    NONE
PIM END
```

多个 `PIM <channel>` 块可以首尾相接出现，以建模多通道并行注意力。

## 子批交错（`misc`）

当 `--enable-sub-batch-interleaving` 开启时，层在 `misc` 中携带批标签：

```
qkv_proj_3    4128    ...    NONE    0    BATCH_1
pim_attention_3    8264    ...    NONE    0    BATCH_2
o_proj_3    3845    ...    NONE    0    BATCH_1
```

`BATCH_1` 和 `BATCH_2` 两半并行运行，通常是 GPU 在某一半上计算，同时 PIM 注意力在另一半上运行。

## 完整轨迹示例（单实例，TP=1，稠密模型）

按 `_FMT` 的真实列宽重现，因此这是生成器写出的逐字节内容（横向滚动查看完整行）：

```
COLOCATED		model_parallel_NPU_group: 1
292
Layername                      comp_time       input_loc       input_size      weight_loc      weight_size     output_loc      output_size     comm_type       comm_size       misc
embedding_0                    5386            REMOTE:0        40              LOCAL           1050673152      LOCAL           81920           NONE            0               NONE
layernorm_1                    2416            LOCAL           81920           LOCAL           8192            LOCAL           81920           NONE            0               NONE
qkv_proj_2                     36000           LOCAL           81920           LOCAL           50331648        LOCAL           122880          NONE            0               NONE
rotary_emb_3                   2795            LOCAL           102400          LOCAL           0               LOCAL           102400          NONE            0               NONE
attention_4                    7985            LOCAL           81920           LOCAL           0               LOCAL           81920           NONE            0               NONE
o_proj_5                       25611           LOCAL           81920           LOCAL           33554432        LOCAL           81920           NONE            0               NONE
... (decoder blocks 1..31 elided) ...
final_layernorm_289            2624            LOCAL           81920           LOCAL           8192            LOCAL           81920           NONE            0               NONE
lm_head_290                    714006          LOCAL           81920           LOCAL           1050673152      LOCAL           2565120         NONE            0               NONE
sampler_291                    24746           LOCAL           2565120         LOCAL           0               REMOTE:0        40              NONE            0               NONE
```

一个层的 `output_size` 一般而言**不是**下一层的 `input_size`：`qkv_proj` 输出 Q+K+V，而 `rotary_emb` 只声明 Q+K，`attention` 从 KV 缓存读取 K/V 而不是从激活中读取。两者在 transformer 块边界处一致（`layernorm` 进、`down_proj`/`moe` 出——都是隐藏状态），这就是为什么流水线阶段只能在那里切分。

## Chakra 转换器如何消费它

Chakra 转换器（`astra-sim/extern/graph_frontend/chakra/src/converter/llm_converter.py`）遍历轨迹并发出 Chakra protobuf 节点：

| 轨迹行 | Chakra 节点 |
| --- | --- |
| 第一层 | 输入传输的 `MEM_LOAD_NODE` |
| 每个计算行 | 按 `comp_time` 键控的 `COMP_NODE` |
| 最后一层 | 输出传输的 `MEM_STORE_NODE` |
| `comm_type != NONE` | 带可选 `involved_dim` BoolList 的 `COMM_COLL_NODE` |
| `EXPERT {i}` 块 | 在秩 `i` 上运行的子图 |
| `PIM <channel>` 块 | 路由到 PIM 设备的子图 |

`.et` 文件就是 `controller.write_flush` 随后发送给 ASTRA-Sim 的内容。

## 注意事项

1. **轨迹中的 `comp_time` 是纳秒**，但底层的剖析 CSV 使用微秒。转换发生在模拟器启动时的 `_load_perf_db()` 中。
2. **列对齐无关紧要。** 两个读者都按任意空白切分，因此制表符、单个空格和 `_FMT` 的填充是等价的。真正要紧的是任何字段都不能包含空格，因为那会被读成两个字段。
3. **不要手工编辑生产轨迹。** 它们每次迭代都会重新生成；手工编辑会被覆盖。要注入自定义时序，修改剖析 CSV 或轨迹生成器。
4. **`comm_size` 是总载荷，而不是每秩的。** ASTRA-Sim 在内部按环中节点数做除法。

## 下一步

- **[模拟器 → 轨迹生成](../simulator/trace-generation)**——每一行如何产生。
- **[集群配置](./cluster-config)**：`placement` 规则决定 `weight_loc` 和 `kv_loc`。
