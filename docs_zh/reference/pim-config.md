---
sidebar_position: 3
title: PIM 配置
---

# PIM 配置 schema

PIM（Processing-In-Memory，内存内处理）设备配置位于 `configs/pim/<name>.ini`，采用 **DRAMSim3 INI 格式**。当 `--enable-attn-offloading` 开启时，模拟器的 `pim_model.py` 读取这些配置来计算 PIM 侧的注意力延迟。

## 文件位置

```
configs/pim/
├── DDR4_8GB_3200_pim.ini
├── HBM2_1GB_2000_pim.ini
├── LPDDR4X_2GB_4266_pim.ini
├── LPDDR5_2GB_6400_pim.ini
└── README.md
```

集群配置通过节点的 `cpu_mem.pim_config` 字段引用其中之一（不带 `.ini` 扩展名）：

```json
"cpu_mem": {
  "mem_size": 512,
  "mem_bw": 256,
  "mem_latency": 0,
  "pim_config": "DDR4_8GB_3200_pim"
}
```

## 自带的配置及其派生值

四个自带文件，以及 `pim_model.py` 从它们派生的量（见 [这些数字如何派生](#这些数字如何派生)）：

| 文件 | 协议 | `data_rate` | 每通道容量 | 每通道带宽 | 读延迟 |
| --- | --- | --- | --- | --- | --- |
| `DDR4_8GB_3200_pim.ini` | DDR4 | 3200 MT/s | 8 GB | 25.6 GB/s | 13.86 ns |
| `HBM2_1GB_2000_pim.ini` | HBM | 2000 MT/s | 1 GB | 32.0 GB/s | 14.00 ns |
| `LPDDR4X_2GB_4266_pim.ini` | LPDDR4X | 4266 MT/s | 2 GB | 8.53 GB/s | 16.85 ns |
| `LPDDR5_2GB_6400_pim.ini` | LPDDR5 | 6400 MT/s | 2 GB | 12.80 GB/s | 10.62 ns |

每个文件名中的容量是**每通道**容量，而不是设备总量。一个节点有多少通道由 `cpu_mem.mem_size` 派生，而不是在 INI 中声明：一个 512 GB 的节点配 `DDR4_8GB_3200_pim` 会得到 `512 / 8 = 64` 个通道，总带宽为 `64 x 25.6 = 1638 GB/s`。

:::warning[添加第五个配置需要改代码]
`pim_model.py` 将 INI 的**文件名主干**与一张硬编码的已校准延迟系数表匹配。单独新增一个 `.ini` 会抛出 `ValueError: Unknown PIM spec: <stem>`。见 **[添加新的 PIM 配置](#添加新的-pim-配置)**。
:::

## INI 结构

自带文件携带**五个**小节，按 DRAMSim3 顺序：`[dram_structure]`、`[timing]`、`[power]`、`[system]`、`[other]`。

**加载器忽略小节标题。** `pim_model.py` 的 `load_flat_config()` 逐行读取文件，跳过任何以 `[` 或 `;` 开头的行，去掉 `#` 注释，并把每个 `key = value` 对展平到一个 dict 中。后果：

- 键名必须在**整个文件中唯一**，而不仅仅是小节内唯一。小节只是为人类读者和 DRAMSim3 本身服务的组织方式，仅此而已。
- 值按形状强制转换：含 `.` 的 token 变为 float，全数字的 token 变为 int，其他任何东西保持字符串。
- 任何行上的尾部 `# comments` 都是安全的，包括小节标题行。

一个自带文件约 50 个键中，模拟器读取**十一个**。其余的是为 DRAMSim3 保真度携带的，在这里是惰性的。

### 模拟器实际读取的键

| 键 | 小节 | 用途 |
| --- | --- | --- |
| `bankgroups` | `[dram_structure]` | `banks = bankgroups * banks_per_group` |
| `banks_per_group` | `[dram_structure]` | 同上 |
| `rows` | `[dram_structure]` | 每 bank 容量 |
| `columns` | `[dram_structure]` | 页大小 |
| `device_width` | `[dram_structure]` | 页大小、每 rank 设备数 |
| `CL` | `[timing]` | 读延迟 |
| `tCK` | `[timing]` | 读延迟 |
| `bus_width` | `[system]` | 通道带宽、每 rank 设备数 |
| `channel_size` | `[system]` | 每通道容量目标，单位 MB |
| `data_rate` | `[other]` | 通道带宽 |
| `idle_power` | `[other]` | 功耗模型，单位 mW |
| `peak_power` | `[other]` | 功耗模型，单位 mW |

`data_rate`、`idle_power` 和 `peak_power` **不是** DRAMSim3 字段。它们是 LLMServingSim 的补充，停放在 `[other]` 中，并且是必填的：没有它们的配置会抛出 `KeyError`。

### `[dram_structure]`

```ini
[dram_structure]
protocol = DDR4
bankgroups = 2
banks_per_group = 4
rows = 65536
columns = 1024
device_width = 16
BL = 8
pim_type = SINGLE
```

| 字段 | 类型 | 读取？ | 说明 |
| --- | --- | --- | --- |
| `protocol` | string | 否 | DRAM 标准。`DDR4`、`DDR5`、`HBM`、`LPDDR4X`、`LPDDR5` |
| `bankgroups` | int | **是** | 每设备 bank 组数 |
| `banks_per_group` | int | **是** | 每 bank 组 bank 数 |
| `rows` | int | **是** | 每 bank 行数 |
| `columns` | int | **是** | 每行列数 |
| `device_width` | int | **是** | 设备数据宽度，单位 bit（4 / 8 / 16 / 128） |
| `BL` | int | 否 | 突发长度。为 DRAMSim3 携带；带宽模型改用 `data_rate` |
| `pim_type` | enum | 否 | `SINGLE` / `DUAL`。`pim_model.py` 不读取 |

### `[timing]`

```ini
[timing]
tCK = 0.63          # clock period in ns
CL = 22             # CAS latency, in cycles
CWL = 16
tRCD = 22
tRP = 22
tRAS = 52
# ... the full DRAMSim3 timing set follows
```

只有 `tCK` 和 `CL` 被读取。本节其他所有内容都是为 DRAMSim3 保真度携带的，不影响仿真。

| 字段 | 单位 | 读取？ | 说明 |
| --- | --- | --- | --- |
| `tCK` | ns | **是** | 时钟周期 |
| `CL` | cycles | **是** | CAS 延迟 |
| 其他所有 | cycles | 否 | `CWL`、`tRCD`、`tRP`、`tRAS`、`tRFC`、`tREFI`、`tRRD_*`、`tWTR_*`、`tFAW`、`tWR`、`tRTP`、`tCCD_*`、`tCKE`、`tXS`、`tXP`、`tRTRS`、…… |

完整的 DRAMSim3 时序语义见 [DRAMSim3 文档](https://github.com/umd-memsys/DRAMsim3)。

### `[power]`

标准的 DRAMSim3 电流 / 电压轨。**其中没有一项被读取**：PIM 功耗来自 `[other]` 中的 `idle_power` / `peak_power`。

```ini
[power]
VDD = 1.2
IDD0 = 95
IPP0 = 4.0
IDD2P = 25
IDD2N = 37
IDD3P = 47
IDD3N = 56
IDD4W = 278
IDD4R = 302
IDD5AB = 280
IDD6x = 30
```

### `[system]`

```ini
[system]
channel_size = 8192
channels = 1
bus_width = 64
address_mapping = rorabgbachco
queue_structure = PER_BANK
row_buf_policy = OPEN_PAGE
```

| 字段 | 类型 | 读取？ | 说明 |
| --- | --- | --- | --- |
| `channel_size` | int | **是** | 每通道容量目标，单位 **MB**。取整为整数个 rank（见下文） |
| `channels` | int | 否 | **被忽略。** 通道数由节点的 `cpu_mem.mem_size` 派生，而不是来自该字段 |
| `bus_width` | int | **是** | 内存总线宽度，单位 bit |
| `address_mapping` | string | 否 | DRAMSim3 地址映射方案 |
| `queue_structure` | enum | 否 | DRAMSim3 排队策略 |
| `row_buf_policy` | enum | 否 | DRAMSim3 行缓冲策略 |

### `[other]`

```ini
[other]
epoch_period = 1587301
output_level = 1
data_rate = 3200 # MT/s
idle_power = 623 # mW
peak_power = 3803 # mW
```

| 字段 | 单位 | 读取？ | 说明 |
| --- | --- | --- | --- |
| `data_rate` | MT/s | **是** | 每秒传输数。驱动每通道带宽 |
| `idle_power` | mW | **是** | 每 DIMM 空闲功耗。变为 `power.dram.idle_power`，单位 W |
| `peak_power` | mW | **是** | 每 DIMM 活跃功耗。变为 `power.dram.pim_active_power`，单位 W |
| `epoch_period` | cycles | 否 | DRAMSim3 统计转储间隔 |
| `output_level` | int | 否 | DRAMSim3 冗长级别 |

## 这些数字如何派生

`PIMModel.init_dram_params()` 把 INI 加上节点的 `cpu_mem.mem_size` 变成四个值。全部是闭式推导，不会派生任何 DRAMSim3 进程。

**每通道容量**（`dimm_size`，单位 GB）：

```
banks            = bankgroups * banks_per_group
devices_per_rank = bus_width / device_width
page_size        = columns * device_width / 8          # bytes
megs_per_bank    = page_size * (rows / 1024) / 1024    # MB
megs_per_rank    = megs_per_bank * banks * devices_per_rank

# channel_size from the INI is a target, snapped to whole ranks
if megs_per_rank > channel_size:
    channel_size = megs_per_rank                       # one rank, minimum
else:
    channel_size = (channel_size / megs_per_rank) * megs_per_rank

ch_capacity = channel_size / 1024                      # GB
```

**每通道带宽**（GB/s）——注意 `BL` 和 `tCK` **不**出现在这里：

```
ch_bw = bus_width / 8 * data_rate / 1000
```

**通道数与总带宽**，来自节点的主机内存大小：

```
num_ch  = cpu_mem.mem_size / ch_capacity
mem_bw  = num_ch * ch_bw
```

**读延迟**（ns）：

```
mem_latency = CL * tCK
```

完整示例，512 GB 节点上的 `DDR4_8GB_3200_pim`：

```
banks            = 2 * 4 = 8
devices_per_rank = 64 / 16 = 4
page_size        = 1024 * 16 / 8 = 2048 B
megs_per_bank    = 2048 * 64 / 1024 = 128 MB
megs_per_rank    = 128 * 8 * 4 = 4096 MB
channel_size     = (8192 / 4096) * 4096 = 8192 MB -> ch_capacity = 8 GB
ch_bw            = 64 / 8 * 3200 / 1000 = 25.6 GB/s
num_ch           = 512 / 8 = 64
mem_bw           = 64 * 25.6 = 1638.4 GB/s
mem_latency      = 22 * 0.63 = 13.86 ns
```

### 这些值覆盖节点的 `cpu_mem`

当节点设置 `cpu_mem.pim_config` 时，`config_builder.py` 用上面派生的值替换该节点的 `cpu_mem.mem_bw` 和 `cpu_mem.mem_latency`，并对每个被覆盖的值记录一条警告。`cpu_mem.mem_size` **不**被覆盖：它是决定通道数的输入。因此使用 PIM 配置时，集群配置中的 `mem_bw` 和 `mem_latency` 是无效字段。

生成的 `memory_expansion.json` 中的 `remote_mem` 也会拾取 `pim-channels = cpu_mem.mem_size // ch_capacity`（整数除法）。

## PIM 注意力延迟模型

`get_pim_latency()` 不仿真 DRAM。它评估一条按 spec 校准、针对 Llama-3.1-8B 形状（`n_head=32`、`kv_head=8`、`head_dim=128`）的线性拟合，并按实际运行的模型重新缩放：

```
gqa_ratio = (n_head / kv_head) / (32 / 8)
kv_scale  = (n_head * head_dim) / (32 * 128)

latency_ns = (slope * gqa_ratio * L + intercept * kv_scale) / channel_split
```

`L` 是序列长度，`channel_split` 是轨迹生成器传入的通道并行度。校准系数位于 `pim_model.py::estimate_with_linear`：

| Spec | `slope` | `intercept` |
| --- | --- | --- |
| `LPDDR4X_2GB_4266_pim` | 432.4458 | 33918.1734 |
| `DDR4_8GB_3200_pim` | 333.2538 | 30675.2739 |
| `LPDDR5_2GB_6400_pim` | 282.4338 | 15996.7018 |
| `HBM2_1GB_2000_pim` | 242.0548 | 14513.5015 |

INI 的结构字段供给*容量、带宽和读延迟*。它们**不**供给注意力延迟，后者完全来自这张表。

## 添加新的 PIM 配置

新增 `.ini` 是必要但不充分的。spec 名称在代码中被白名单化，因此这需要两个步骤：

1. 把文件放到 `configs/pim/<name>.ini`。至少填写模拟器读取的十一个键：`bankgroups`、`banks_per_group`、`rows`、`columns`、`device_width`、`CL`、`tCK`、`bus_width`、`channel_size`、`data_rate`、`idle_power`、`peak_power`。复制一个自带文件来编辑，而不要从零开始，这样惰性的 DRAMSim3 字段能保持良好形式。
2. **在 `serving/core/pim_model.py` 的 `attn_model` dict 中添加一个 `"<name>": {"slope": ..., "intercept": ...}` 条目。** 键是文件名主干。没有它，`estimate_with_linear` 会在第一次发出卸载的注意力层时抛出 `ValueError: Unknown PIM spec: <name>`。
3. 从集群配置引用它：`"cpu_mem": {"pim_config": "<name>"}`（不带 `.ini` 扩展名）。
4. 用 `--enable-attn-offloading` 运行。

获取系数意味着在目标设备上测量或仿真 PIM 注意力延迟随序列长度的变化并拟合一条直线，采用重缩放所假定的 Llama-3.1-8B 头形状。结构性的 DRAMSim3 时序可以来自 JEDEC 数据手册，但 `slope` / `intercept` 无法从规格书直接读出。

## 使用位置

- **`serving/core/pim_model.py`**：扁平解析 INI，派生容量 / 带宽 / 读延迟，并评估线性注意力延迟模型。
- **`serving/core/config_builder.py`**：为每个设置 `cpu_mem.pim_config` 的节点实例化一个 `PIMModel`，并用它覆盖该节点的 `cpu_mem.mem_bw` / `mem_latency`。
- **`serving/core/trace_generator.py`**：使用 `--enable-attn-offloading` 时，在 NPU 注意力内核之前用 `PIM <channel>` / `PIM END` 标记包裹 PIM 注意力。
- **功耗模型**：`idle_power` / `peak_power` 变为 `power.dram.idle_power` 和 `power.dram.pim_active_power`（mW 到 W），派生的每通道容量变为 `power.dram.dimm_size`。两者都覆盖集群配置 `power.dram` 块声明的任何值。

PIM 卸载机制的完整说明见 **[模拟器 → PIM 卸载](../simulator/specialized/pim-offload)**。带完整示例见 **[示例 → PIM 注意力卸载](../examples/disaggregated/pim-attention-offload)**。

## 注意事项

1. **不带代码改动的新 INI 会崩溃。** `pim_model.py` 中的 `attn_model` 白名单以文件名主干为键。这是本页最常见的一个意外。
2. **`[system]` 中的 `channels` 不被读取。** 通道数是 `cpu_mem.mem_size / 每通道容量`。要建模更多并行 PIM 通道，提高节点的 `cpu_mem.mem_size` 或选择每通道容量更小的配置，而不是用 `channels`。
3. **`cpu_mem.mem_bw` 和 `cpu_mem.mem_latency` 在带 `pim_config` 的节点上被忽略。** 它们会被 INI 覆盖（带警告）。只有 `mem_size` 仍然重要。
4. **小节只是装饰。** 加载器展平文件，因此一个键在两个小节中重复出现时，静默保留最后一次出现。
5. **`BL` 和 `pim_type` 是惰性的。** 每个自带文件都写 `pim_type = SINGLE`；换成 `DUAL` 不会有任何变化，因为 `pim_model.py` 从不读取它。
6. **功耗单位是毫瓦。** `idle_power = 623` 表示每 DIMM 0.623 W。混入一个瓦级数值会把节点功耗放大 1000 倍。

## 下一步

- **[集群配置 → `cpu_mem.pim_config`](./cluster-config#cpu_mem)**——如何把这个文件接入集群。
- **[模拟器 → PIM 卸载](../simulator/specialized/pim-offload)**——仿真时会发生什么。
