---
sidebar_position: 2
title: 运行
---

# 运行剖析器

剖析器通过 `profiler/profile.sh` 调用：这是一个可编辑的模板。修改文件顶部的变量为您想要剖析的内容，然后运行它。

> 想添加一个全新的硬件目标（GPU 或非 GPU）？参见 **[添加新硬件](./adding-hardware)**。本页介绍日常的"我有一个配置，想剖析它"的流程。

## 快速开始

在 `/workspace` 的 vLLM Docker 容器内：

```bash
# Edit the variables at the top of profiler/profile.sh, then:
./profiler/profile.sh
```

该脚本会根据 HF `config.json` 的 `model_type` 字段自动解析模型架构，您无需在命令行指定它。匹配的架构 YAML 必须存在于 `profiler/models/<model_type>.yaml`。如果不存在，参见 **[添加模型架构](./adding-model-architecture)**。

## `profile.sh` 按顺序做什么

1. 读取 `configs/model/<MODEL>.json`（原始 HF `config.json`）。如果不存在且 `MODEL` 是 HF id，则从 Hub 下载并缓存到那里。
2. 按 `model_type` 选择匹配的架构 YAML。
3. 将模型配置写入 tmpdir；基于它启动 vLLM。
4. 扫描 **dense / per_sequence / attention / moe** 采样网格，将 CSV 写入 `profiler/perf/<HW>/<MODEL>/<variant>/tp<N>/`。
5. （如果 `SKIP_SKEW=0`，默认）运行异构解码偏斜扫描，并将按桶拟合的 alpha 写入 `skew_fit.csv`。
6. 写入 `meta.yaml` 汇总本次运行。

对于 `TP_DEGREES` 中的每个 TP 度数，剖析器通过 `hf_overrides` 划分模型的每 rank 形状，在单个 GPU 上模拟该 TP。**剖析任何 TP 度数都只需要一个 GPU**。

## 必需变量

| 变量 | 含义 |
| --- | --- |
| `MODEL` | HF 风格 `<org>/<name>`。必须在 `configs/model/<MODEL>.json` 有配置（首次运行自动下载） |
| `HARDWARE` | 自由格式标签，将成为 `profiler/perf/` 下的文件夹名。选一个有意义的（例如 `RTXPRO6000`、`H100`、`MI300X`） |

## 扫描形状

| 变量 | 默认值 | 含义 |
| --- | --- | --- |
| `TP_DEGREES` | `profile.sh` 中为 `1,2`（`--tp` 默认 `1`） | 逗号分隔的 TP 度数。**必须包含 `1`**（TP 稳定层在 TP=1 时剖析一次并复制到其他 TP 文件夹） |
| `MAX_NUM_BATCHED_TOKENS` | `2048` | 剖析器内部会为采样旁路余量将其提高 `+MSQ`；记录 meta 时再减回去 |
| `MAX_NUM_SEQS` | `256` | 用 `MSQ > 运行时 MSQ` 剖析，使 `n = 运行时_MSQ` 的混合场景保持可行 |

## 注意力网格

4D 注意力扫描覆盖 `(prefill_chunk, kv_prefill, n_decode, kv_decode)`。三个参数控制其形状：

| 变量 | 默认值 | 含义 |
| --- | --- | --- |
| `ATTENTION_MAX_KV` | `16384` | `kv_prefill` 和 `kv_decode` 轴的上界 |
| `ATTENTION_CHUNK_FACTOR` | `2.0` | `prefill_chunk` 轴的几何因子（倍增） |
| `ATTENTION_KV_FACTOR` | `2.0` | `kv` 轴的几何因子（倍增） |

更小的因子使轴更密集（更多采样、更慢）；更大的因子使其更稀疏（更少采样、更快）。

## 测量平均

```bash
MEASUREMENT_ITERATIONS=3
```

每个采样点计时的前向次数，取平均。由于 DVFS / 时钟抖动，单个样本在大 GEMM 上会波动 15–25%。`N=3` 将其降至约 5%，代价是约 3 倍的剖析时间。如果需要非常精确的数字，提高到 5。

## 偏斜扫描

在均匀注意力网格之后，剖析器会运行一个异构解码扫描，用于驱动模拟器的 FlashAttention-varlen 偏斜修正：

| 变量 | 默认值 | 含义 |
| --- | --- | --- |
| `SKIP_SKEW` | 未设置 | 设为 `1` 完全跳过偏斜扫描。模拟器随后不应用任何偏斜修正（`alpha = 0`） |
| `ONLY_SKEW` | 未设置 | 设为 `1` **只**运行偏斜步骤，不动 dense / per_seq / attention / moe。用于刷新 `skew.csv` |
| `SKEW_N_FACTOR` | `2.0` | `n`（总解码数）轴密度。更高 = 更少采样 |
| `SKEW_PC_FACTOR` | `2.0` | `pc`（预填充块）轴 |
| `SKEW_KP_FACTOR` | `2.0` | `kp`（预填充历史长度）轴 |
| `SKEW_KVS_FACTOR` | `2.0` | `kvs`（小解码 kv）轴 |

偏斜扫描每个用例触发 3 次采样（`t_mean`、`t_max`、`t_skew`），因此用 `>2.0` 的因子稀疏化可以大幅缩短剖析时间。方法论参见 **[偏斜与 alpha 拟合](./skew-alpha-fit)**。

## 恢复 vs 强制

| 变量 | 默认值 | 含义 |
| --- | --- | --- |
| `FORCE` | 未设置 | 设为 `1` 擦除该变体的所有 CSV 并从头重新剖析 |

默认是**恢复**：现有 CSV 逐行预加载，只有身份键尚不存在的采样才会被触发。这让您可以在改变可行性之后（例如将 `MAX_NUM_SEQS` 从 128 提高到 256）在**几分钟**内而不是几小时内扩展先前的扫描。恢复适用于每个类别以及偏斜；`FORCE=1` 会全部清空。

## 输出命名

| 变量 | 默认值 | 含义 |
| --- | --- | --- |
| `VARIANT` | 自动推导 | 覆盖变体文件夹名 |

省略时，`<variant>` 由 `DTYPE` + `KV_CACHE_DTYPE` 自动组合：

- `bfloat16` → `bf16`
- `bfloat16` + `fp8` KV → `bf16-kvfp8`
- `fp8` + `fp8` KV → `fp8-kvfp8`

您几乎不需要覆盖它。只对命名的实验性运行（量化方案、消融）显式设置。

## Dtype

| 变量 | 默认值 | 含义 |
| --- | --- | --- |
| `DTYPE` | `bfloat16` | 模型权重 dtype：`bfloat16` / `float16` / `float32` / `fp8`。未设置时从 `torch_dtype` 推断 |
| `KV_CACHE_DTYPE` | `auto` | KV 缓存 dtype：`auto`（继承 `DTYPE`）/ `fp8` / 等。`fp8` 使模拟器中 KV 内存减半 |

## 详细程度

```bash
VERBOSITY="--silent"        # warnings only
VERBOSITY="--verbose"       # DEBUG + vLLM stdout
VERBOSITY=""                # default (INFO)
```

## 直接调用 `python -m profiler`

`profile.sh` 是一个便捷包装；其中每个变量都映射到一个 flag。当您想脚本化一次扫描时，或者使用 `profile.sh` 完全不暴露的 `slice` 子命令时，自己调用该模块。

```bash
python -m profiler profile <model> --hardware <hw> [options]
python -m profiler slice   <model> --hardware <hw> --tp-refresh N --group G [options]
```

`<model>` 是 HF 风格的 `<org>/<name>`，解析到 `configs/model/<org>/<name>.json`，或者是以 `.json` 结尾的显式路径。HF 风格 id 首次使用时从 Hub 自动下载（遵循 `HF_TOKEN`）；显式路径从不获取，因此文件缺失会报错。

### 两个子命令共享的 flags

| Flag | 默认值 | `profile.sh` 变量 |
| --- | --- | --- |
| `--hardware` | **必需** | `HARDWARE` |
| `--tp` | `1` | `TP_DEGREES` |
| `--variant` | 从 dtype 自动推导 | `VARIANT` |
| `--dtype` | vLLM 默认（模型的 `torch_dtype`） | `DTYPE` |
| `--kv-cache-dtype` | `auto` | `KV_CACHE_DTYPE` |
| `--max-num-batched-tokens` | `2048` | `MAX_NUM_BATCHED_TOKENS` |
| `--max-num-seqs` | `256` | `MAX_NUM_SEQS` |
| `--attention-max-kv` | `16384` | `ATTENTION_MAX_KV` |
| `--attention-chunk-factor` | `2.0` | `ATTENTION_CHUNK_FACTOR` |
| `--attention-kv-factor` | `2.0` | `ATTENTION_KV_FACTOR` |
| `--measurement-iterations` | `3` | `MEASUREMENT_ITERATIONS` |
| `--skip-skew` | 关 | `SKIP_SKEW=1` |
| `--only-skew` | 关 | `ONLY_SKEW=1` |
| `--skew-n-factor` | `2.0` | `SKEW_N_FACTOR` |
| `--skew-pc-factor` | `2.0` | `SKEW_PC_FACTOR` |
| `--skew-kp-factor` | `2.0` | `SKEW_KP_FACTOR` |
| `--skew-kvs-factor` | `2.0` | `SKEW_KVS_FACTOR` |
| `--force` | 关（恢复） | `FORCE=1` |
| `--out-root` | `profiler/perf` | — |
| `--model-config-root` | `configs/model` | — |
| `--log-level` | `INFO` | `VERBOSITY` |
| `--silent` | — | `VERBOSITY="--silent"` |
| `--verbose` | — | `VERBOSITY="--verbose"` |

`--out-root` 和 `--model-config-root` 没有对应的 `profile.sh` 变量。用 `--out-root` 将数据包写到 `profiler/perf/` 之外的地方，用 `--model-config-root` 指向不同的 HF 配置树——在剖析假设形状而不将其加入仓库时很有用。

`--log-level`、`--silent` 和 `--verbose` 互斥。`--silent` 是 `WARNING`，`--verbose` 是 `DEBUG` **加上** vLLM 自己的 stdout，`--log-level` 会显式覆盖两者。

`--tp` 必须包含 `1`：TP 稳定层（layernorm、sampler）在 TP=1 时剖析一次并由 writer 复制到其他 `tp<N>/` 文件夹，因此没有 TP=1 的扫描就没有可复制的来源。

### `slice`：刷新一对 (tp, category)

完整扫描之后，只迭代单个类别而不重做其余部分：

```bash
python -m profiler slice meta-llama/Llama-3.1-8B \
    --hardware RTXPRO6000 --tp-refresh 1 --group attention
```

| Flag | 必需 | 描述 |
| --- | --- | --- |
| `--tp-refresh` | ✓ | 要刷新的单个 TP 度数。必须是 `--tp` 的成员 |
| `--group` | ✓ | `dense`、`per_sequence`、`attention`、`moe` 之一 |

它在该 TP 启动一个引擎，只触发该类别的网格，并重写 `tp<N>/<group>.csv` 以及 `meta.yaml`。如果架构 YAML 在 `catalog.<group>` 中没有条目，会报错——例如在 dense 模型上请求 `moe`。

注意 `slice` 只处理四个均匀类别。偏斜扫描不是 `--group` 值；用 `python -m profiler profile ... --only-skew` 刷新它。

## 多模型批量扫描：`profile-all.sh`

一次性为多个模型启动一个新的 GPU 目标：

```bash
./profiler/profile-all.sh
```

这会循环调用 `python -m profiler profile`，遍历一个固定的模型列表（目前是 `Qwen/Qwen3-32B`、`Qwen/Qwen3-30B-A3B-Instruct-2507`、`meta-llama/Llama-3.1-8B`），在 TP=1 和 TP=2 下运行。`profile.sh` 的所有参数都可以作为环境变量识别：

```bash
HARDWARE=H100 \
TP_DEGREES=1,2,4 \
ATTENTION_CHUNK_FACTOR=1.5 \
./profiler/profile-all.sh
```

要更改模型列表，编辑脚本顶部的 `MODELS=( ... )` 数组。这个文件设计为就地复制或调整，而不是当作稳定的 CLI。

## 预期运行时间

单个模型 + 单个 TP 在 RTXPRO6000 级别硬件上的粗略数字（`MAX_NUM_BATCHED_TOKENS=2048`、`MAX_NUM_SEQS=256`、默认因子）：

| 步骤 | 时间 |
| --- | --- |
| `dense` | 秒级 |
| `per_sequence` | 秒级 |
| `attention`（均匀 4D 网格） | 5–15 分钟 |
| `moe`（仅 MoE） | 10–30 分钟 |
| `skew` 扫描 | 10–25 分钟 |
| `skew_fit`（后处理） | 秒级 |

用 `profile-all.sh` 做一次完整的多 TP、多模型扫描通常需要 **1–4 小时**。当您不需要 varlen 偏斜修正时，用 `SKIP_SKEW=1` 可以快得多。

基于 Rich 的 logger 会渲染逐步进度条；用 `--silent` 重定向 stdout 以获得更安静的运行。

## 输出

剖析数据位于：

```
profiler/perf/<HARDWARE>/<MODEL>/<variant>/
├── meta.yaml
└── tp<N>/
    ├── dense.csv
    ├── per_sequence.csv
    ├── attention.csv
    ├── moe.csv         (MoE models only)
    ├── skew.csv         (skew-enabled runs)
    └── skew_fit.csv     (skew-enabled runs)
```

Schema 参考：**[输出数据包](./output-bundle)**。

## 提示

1. **启动新的 `(hardware, model)` 组合时总是从 `SKIP_SKEW=1` 开始**，先完成均匀网格，确定其余部分正常工作后再加偏斜。
2. **`profile.sh` 用于就地编辑。** 不要试图通过 flag 参数化它；对大幅偏离的场景复制一份。
3. **剖析恢复是细粒度的**：如果单个采样崩溃，您可以修复问题后重新运行；之前完成的采样会保持缓存。
4. **先稀疏化注意力网格**。4D 注意力扫描是最长的步骤。如果只需要粗略数字，把 `ATTENTION_CHUNK_FACTOR` 提高到 `4.0`，之后再以 `2.0` 重新运行以获得精确度。
5. **不要跨 CUDA 驱动版本剖析。** 驱动升级会使内核计时改变几个百分点；要么在驱动变更后重新剖析，要么接受漂移。

## 接下来

- **[输出数据包](./output-bundle)**：您刚产生的 CSV 的 schema。
- **[偏斜与 alpha 拟合](./skew-alpha-fit)**：偏斜扫描在底层做什么。
