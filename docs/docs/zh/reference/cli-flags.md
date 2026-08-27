---
sidebar_position: 1
title: CLI 参数
---

# `python -m serving` CLI 参数

`python -m serving` 接受的所有命令行参数的完整参考。关于每个参数的概念层面（它在内部*做什么*），请参阅 **[模拟器](../simulator/architecture)**。

:::tip[其中 14 个可按实例设置]
下面标记为**（按实例）**的参数也可以写入集群配置中某个单独的 `instances[i]` 对象，对该实例而言该值优先于 CLI 值。这正是单次运行服务异构实例的方式。其余 15 个参数是集群级的。请参阅 **[集群配置 → 运行时覆盖](./cluster-config#runtime-overrides-optional)**。
:::

## 集群拓扑

| Flag | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--cluster-config` | path | `configs/cluster/single_node_single_instance.json` | 集群配置 JSON 的路径。见 **[集群配置](./cluster-config)** |
| `--network-backend` | choice | `analytical` | 网络仿真后端。`analytical`（快）或 `ns3`（详细，WIP） |

## 批处理与调度

这些参数是部署默认值。集群配置可以为每个 `instances[i]` 覆盖对应的运行时旋钮；见 **[集群配置](./cluster-config#runtime-overrides-optional)**。

| Flag | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--max-num-seqs` **（按实例）** | int | `128` | 批中的最大序列数。`0` = 不限 |
| `--max-num-batched-tokens` **（按实例）** | int | `2048` | 每次迭代所有请求的最大 token 数（token 预算）。会被钳制到模型配置的 `max_position_embeddings`，因此 `0`（"不限"）解析为上下文长度而不是无穷大 |
| `--long-prefill-token-threshold` **（按实例）** | int | `0` | 分块预填充中每请求每步的 token 上限。`0` = 禁用 |
| `--enable-chunked-prefill` **（按实例）** | bool | `True` | 将长预填充拆分到多次迭代。使用 `--no-enable-chunked-prefill` 禁用 |
| `--npu-memory-utilization` **（按实例，即 `npu_mem.mem_util`）** | float | `0.9` | NPU 内存中可用于权重加 KV 缓存的比例。对应 vLLM 的 `--gpu-memory-utilization`；KV 容量为 `npu_mem.mem_size * 该值 - 模型权重`。按实例用 `npu_mem.mem_util` 覆盖 |
| `--reserve-full-isl` / `--no-reserve-full-isl` **（按实例）** | flag | 开 | 仅当请求的整个序列都能容纳时才准入，而不仅是其第一个分块。对应 vLLM 的 `scheduler_reserve_full_isl`；没有它，分块预填充会过度准入并导致 KV 缓存抖动 |
| `--block-size` **（按实例）** | int | `16` | KV 缓存块大小（token 数） |
| `--skip-prefill` | flag | 关 | 跳过预填充，仅运行解码 |

## 路由

| Flag | 选项 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--request-routing-policy` | `LOAD` / `RR` / `RAND` / `CUSTOM` | `LOAD` | 跨实例请求路由 |
| `--expert-routing-policy` | `BALANCED` / `RR` / `RAND` / `CUSTOM` | `BALANCED` | MoE 专家 token 路由 |
| `--enable-block-copy` **（按实例）** | bool | `True` | 跨层重放一个块的轨迹（设为 False 以获得逐层 EP 方差） |

## 精度

| Flag | 选项 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--dtype` **（按实例）** | `float16` / `bfloat16` / `float32` / `fp8` / `int8` | 模型的 `torch_dtype`，回退 `bfloat16` | 模型权重 dtype |
| `--kv-cache-dtype` **（按实例）** | `auto` / `fp8` | `auto`（继承 dtype） | KV 缓存 dtype。`fp8` 将 KV 内存减半，并选择 `*-kvfp8` 剖析变体 |

## 前缀缓存与卸载

| Flag | 默认值 | 说明 |
| --- | --- | --- |
| `--enable-prefix-caching` **（按实例）** | `True` | 基于带链式块哈希的分层块池的前缀缓存。使用 `--no-enable-prefix-caching` 禁用 |
| `--enable-prefix-sharing` | 关 | 节点内跨实例共享的第二层前缀池 |
| `--prefix-storage` | `None` | 第二层池所在位置。`None` / `CPU` / `CXL` |
| `--enable-local-offloading` **（按实例）** | 关 | 权重卸载到 NPU（在剖析中计入权重读取） |
| `--enable-attn-offloading` **（按实例）** | 关 | 注意力计算卸载到 PIM |
| `--enable-sub-batch-interleaving` **（按实例）** | 关 | 将 GPU 计算与 PIM 注意力重叠。需要 `--enable-attn-offloading` |

## 数据集与输出

| Flag | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--dataset` | path | `None` | JSONL 工作负载文件。见 **[工作负载 → JSONL 格式](../workloads/jsonl-format)** |
| `--num-reqs` | int | `0` | 从数据集加载的条目数（`0` = 全部）。对于 agentic，每个条目是一个会话 |
| `--output` | path | `None` | 每请求 CSV 输出路径。为 `None` 时仅输出到 stdout。字面量 `{run_id}` 会被替换为当前运行的 run id |

## 运行隔离

每次调用都会在运行专属的输入根目录下写入 ASTRA-Sim 中间产物，这样并行仿真不会互相覆盖各自生成的配置、轨迹或 Chakra workload。默认情况下，生成的文本轨迹在 Chakra 转换后被删除，运行专属输入根目录在仿真成功后也会被删除。

| Flag | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--run-id` | string | 自动生成 | 本次仿真运行的路径安全 id。用于 `astra-sim/inputs/runs/<run-id>` 和 `{run_id}` 输出占位符 |
| `--inputs-root` | path | `astra-sim/inputs/runs/<run-id>` | 覆盖生成的 ASTRA-Sim 输入根目录，例如将中间产物放到本地 SSD 或 tmpfs 上 |
| `--save-trace-text` / `--no-save-trace-text` | bool | `false` | 将每个批的轨迹以文本形式写出，供检查。流水线中没有东西会读取它——Chakra 转换器直接接收轨迹行——因此只在请求时生成，而且它是模拟器所发出内容的唯一人类可读形式。隐含 `--keep-inputs` |
| `--keep-inputs` / `--no-keep-inputs` | bool | `false` | 仿真成功后保留 `astra-sim/inputs/runs/<run-id>` 下生成的 ASTRA-Sim 输入：Chakra `.et` workload 以及生成的 network / system / memory 配置，以便手动通过 ASTRA-Sim 重放一次运行 |

## 日志

| Flag | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `--log-interval` | float | `1.0` | 吞吐量 / 内存日志行之间的秒数 |
| `--log-level` | choice | `WARNING` | `WARNING`（默认）/ `INFO` / `DEBUG` |

## 快速参考：哪个参数对应哪个特性

| 特性 | 参数 |
| --- | --- |
| 多实例（通过集群配置实现并行） | （集群配置 `num_instances`） |
| 张量并行 | （集群配置 `tp_size`） |
| MoE 专家并行 | （集群配置 `ep_size`） |
| DP+EP MoE | （集群配置 `dp_group`） |
| 前缀缓存 | `--enable-prefix-caching`（默认开）、`--enable-prefix-sharing`、`--prefix-storage` |
| 分块预填充 | `--enable-chunked-prefill`（默认开）、`--long-prefill-token-threshold` |
| PIM 注意力卸载 | `--enable-attn-offloading`（集群配置设置 `pim_config`） |
| FP8 KV 缓存 | `--kv-cache-dtype fp8` |
| ns3 后端 | `--network-backend ns3` |
| 一次运行中的异构实例 | （集群配置按实例覆盖；见上面的提示） |

关于每个特性的完整概念性说明，请浏览 **[模拟器](../simulator/architecture)** 部分。可运行的示例见 **[示例](../examples)**。
