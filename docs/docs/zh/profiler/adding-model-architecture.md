---
sidebar_position: 6
title: 添加模型架构
---

# 添加模型架构

剖析器按 HF 配置的 `model_type` 字段分发。如果您的模型的 `model_type` 已经映射到 `profiler/models/` 下的一个 YAML，那就可以了，直接运行 `profile.sh`。如果没有，您需要添加一个 YAML。

本页讨论的就是这种情况。

## 何时需要新 YAML

运行 `cat configs/model/<your-org>/<your-model>.json | jq .model_type` 并与随附架构比较：

| `model_type` | YAML | 覆盖 |
| --- | --- | --- |
| `llama` | `llama.yaml` | Llama 3.x dense（8B / 70B / 405B / 自定义形状）、Mistral 7B，以及具有相同块结构的衍生模型 |
| `qwen3` | `qwen3.yaml` | Qwen3 dense（0.6B / 4B / 7B / 14B / 32B），带每头 `qk_norm` |
| `qwen3_moe` | `qwen3_moe.yaml` | Qwen3 MoE（30B-A3B、235B-A22B） |
| `mixtral` | `mixtral.yaml` | `MixtralForCausalLM`（8x7B、8x22B） |
| `phimoe` | `phimoe.yaml` | `PhiMoEForCausalLM`（Phi-3.5-MoE） |

如果您的 `model_type` 是其中之一，您无需做任何事——现有 YAML 已经处理它。

如果是*新*的 `model_type`（例如 `gemma2`、`deepseek_v3`、`gpt_oss`），您需要一个新的 YAML。继续读。

## 何时还需要模拟器代码更改

当新模型每迭代的流程符合标准模式时，只加一个 YAML 就够了：

```
prologue → pre_attn → post_attn → (mlp_dense | mlp_moe) → head
```

如果新模型有真正新颖的块结构、滑动窗口注意力、多潜在注意力（MLA，如 DeepSeek V3）、双 MLP 解码器，您还需要扩展 `serving/core/trace_generator.py` 来走新的序列并附加正确的集合通信。我们会在本页末尾介绍。

## YAML 结构

每个架构 YAML 有两个顶层部分，没有其他（`extra="forbid"`，因此拼写错误或多余的键会在加载时验证失败，而不是静默地什么都不做）：

- `sequence:`：声明每迭代层的运行顺序。剖析器为每个序列层发出一次采样；模拟器的 `trace_generator` 在轨迹生成时走同一个列表。
- `catalog:`：将规范层名绑定到 CUDA 剖析器报告的 vLLM 类名。按剖析类别分为四个块。

### 最小示例：`llama.yaml`

```yaml
sequence:
  prologue:  [embedding]
  pre_attn:  [layernorm, qkv_proj, rotary_emb, attention]
  post_attn: [o_proj, layernorm]
  mlp_dense: [gate_up_proj, act_fn, down_proj]
  mlp_moe:   []
  head:      [final_layernorm, lm_head, sampler]


catalog:
  dense:
    embedding:
      vllm: VocabParallelEmbedding
    layernorm:
      vllm: RMSNorm
      within: LlamaDecoderLayer
      tp_stable: true
    qkv_proj:
      vllm: QKVParallelLinear
    rotary_emb:
      vllm: Llama3RotaryEmbedding
    o_proj:
      vllm: RowParallelLinear
      within: LlamaAttention
    gate_up_proj:
      vllm: MergedColumnParallelLinear
    act_fn:
      vllm: SiluAndMul
    down_proj:
      vllm: RowParallelLinear
      within: LlamaMLP
    final_layernorm:
      vllm: RMSNorm
      within: LlamaForCausalLM
      tp_stable: true
  per_sequence:
    lm_head:
      vllm: LogitsProcessor
    sampler:
      vllm: Sampler
      tp_stable: true
  attention:
    attention:
      vllm: Attention
```

### `catalog` 结构

**剖析类别是层所在的块**，而不是层上的字段。正好有四个块，都是可选的：

| 块 | 扫描轴 | CSV |
| --- | --- | --- |
| `dense` | `tokens`（批次总数） | `dense.csv` |
| `per_sequence` | `sequences`（请求数） | `per_sequence.csv` |
| `attention` | `(prefill_chunk, kv_prefill, n_decode, kv_decode)` | `attention.csv` |
| `moe` | `(tokens, activated_experts)` | `moe.csv` |

### `catalog` 条目字段

| 字段 | 必需 | 含义 |
| --- | --- | --- |
| `vllm` | ✓ | CUDA 剖析器报告的 vLLM **叶子类名**，例如 `QKVParallelLinear`、`RMSNorm`、`Attention`。不是属性路径 |
| `within` | 可选 | 一个**祖先**类名，用于当同一个 `vllm` 类在模型中出现多次时消歧。匹配规则：`node_class == vllm` **且**（`within` 未设置 **或** `within` 出现在节点的祖先类中） |
| `tp_stable` | 可选（默认 `false`） | 如果层的延迟不依赖 TP 度数（layernorm、sampler）则为 `true`。在 TP=1 剖析一次，由 writer 复制到每个 `tp<N>/` 文件夹 |

`within` 是让 `RMSNorm` 可以用三次的关键。Llama 在 `LlamaDecoderLayer` 内有一个输入 layernorm 和一个注意力后 layernorm，外加 `LlamaForCausalLM` 上的最终 norm——都是同一个类。`within: LlamaDecoderLayer` 把两个块级 norm 捕获为 `layernorm`，`within: LlamaForCausalLM` 把最后一个捕获为 `final_layernorm`。同样的技巧把 `o_proj`（`LlamaAttention` 内的 `RowParallelLinear`）与 `down_proj`（`LlamaMLP` 内同一个类）分开。

`(vllm, within)` 对必须在 catalog 中**全局唯一**；加载器按设计拒绝重复，否则一个被剖析的内核会被记到两个规范名上。

没有 `tp_collective` / `ep_collective` 字段。`o_proj` / `down_proj` 之后的 TP ALLREDUCE 和 `moe` 周围的 EP ALLTOALL 由模拟器根据**集群配置**附加，不在这里声明。

### `sequence` 部分参考

| 组 | 运行 | 说明 |
| --- | --- | --- |
| `prologue` | 每迭代开始一次 | Embedding 查找 |
| `pre_attn` | 每个解码器块一次 | 输入 layernorm、qkv_proj、rotary_emb、`attention`（以及 Qwen3 上的 `qk_norm`） |
| `post_attn` | 每个解码器块一次 | o_proj + 注意力后 layernorm |
| `mlp_dense` | 每个解码器块一次（dense 模型） | gate_up_proj + act_fn + down_proj |
| `mlp_moe` | 每个解码器块一次（MoE 模型） | `moe`，EP ALLTOALL 环绕由模拟器添加 |
| `head` | 每迭代结束一次 | final_layernorm + lm_head + sampler |

`attention` 在 `pre_attn` 中**显式列出**；它不是隐式的。序列组提到的每个名字都必须在 `catalog` 中存在，模拟器发出的每个 catalog 条目都必须出现在某个序列组中。

Dense 和 MoE 模型都声明全部六个组；未使用的组是空列表（dense 模型为 `mlp_moe: []`）。层可以在组内或跨组重复——`layernorm` 同时出现在 `pre_attn` 和 `post_attn` 中，这就是一个 catalog 条目覆盖两个 norm 的方式。

## MoE 专属 YAML

MoE 架构在 catalog 中增加一个 `moe` 块，并切换填充哪个 MLP 组。来自 `qwen3_moe.yaml`：

```yaml
sequence:
  prologue:  [embedding]
  pre_attn:  [layernorm, qkv_proj, qk_norm, rotary_emb, attention]
  post_attn: [o_proj, layernorm]
  mlp_dense: []
  mlp_moe:   [moe]
  head:      [final_layernorm, lm_head, sampler]

catalog:
  # ... dense entries ...
  moe:
    moe:
      vllm: Qwen3MoeSparseMoeBlock
```

这里命名的类是**稀疏块**，而不是 `FusedMoE`——后者是 CUDA 剖析器为整个专家路径报告的类。

完整的 MoE YAML 参见 `qwen3_moe.yaml`、`mixtral.yaml` 和 `phimoe.yaml`。

## 分步：添加新的 `model_type`

假设您想支持 `gemma2`（Google Gemma 2 系列）。HF 配置有 `model_type: "gemma2"`。工作流程：

### 1. 检查模型的 vLLM 源码

查看 `vllm/model_executor/models/<model>.py`。识别：

- 解码器块类。
- 每个层属性名（`self.qkv_proj`、`self.attention`……）。
- layernorm 是 pre-attn / post-attn / 两者都有。
- 是否有任何额外层（有些模型有 MLP 后 layernorm 等）。
- 对于 MoE：专家如何排列。

### 2. 编写 `profiler/models/gemma2.yaml`

从最接近的现有 YAML 开始（例如 Gemma 风格 dense 模型用 `llama.yaml`）并调整：

- 将 `vllm` 类名更新为模型的类名，并在同一个类出现多次的地方设置 `within`。
- 把任何额外层（例如 Gemma 2 的 MLP 后 layernorm）加到 catalog 和 `sequence`。
- 在延迟不依赖 TP 的层上设置 `tp_stable: true`。

### 3. 尝试剖析

```bash
MODEL="google/gemma-2-9b" \
HARDWARE="<your-hw>" \
TP_DEGREES=1 \
SKIP_SKEW=1 \
./profiler/profile.sh
```

从 TP=1 和 `SKIP_SKEW=1` 开始以获得最快的反馈。剖析器会：

- 如果 `sequence` 中的任何层通过您指定的 `cls` 在模型上找不到，会大声警告。
- 跳过找不到的层（带警告），这样您可以迭代。

如果 YAML 正确，您会得到干净的 CSV。运行一次小模拟来确认。

### 4. 尝试模拟

在您的 `cluster_config.json` 中：

```json
{
  "model_name": "google/gemma-2-9b",
  "hardware": "<your-hw>",
  "tp_size": 1,
  ...
}
```

运行 `python -m serving --cluster-config ... --dataset workloads/example_trace.jsonl ...`。

如果有任何不对（找不到层、死循环、缺少集合通信），模拟器会告诉您 YAML 中它不知道如何处理哪一层。修复并重试。

### 5. 提交 + 开 PR

一旦成功，发一个添加 `profiler/models/gemma2.yaml` 的 PR。PR 标题用 `Add gemma2 architecture support`，并包含：

- 您用来验证的 HF 模型 id。
- 一次冒烟测试模拟的输出（小工作负载的 TTFT / TPOT）。
- 是否测试了 MoE（或者没有，Gemma 2 不是 MoE，但其他新增可能是）。

## 何时还需要修改 `serving/core/trace_generator.py`

YAML 单独无法表达的三个标志。每个都需要一小段 Python 添加：

### 滑动窗口注意力

一些模型（Mistral、带滑动窗口的 Llama 3.1）把注意力限制在固定大小的窗口内。模拟器的 KV 缓存预算需要考虑这一点，总 KV 不会超过窗口大小增长。

位置：扩展 `trace_generator.py` 中的注意力类别查找，将 `kv_decode` 在窗口大小处截断，并更新 `memory_model.py::get_kv` 按请求限制 KV 块。

### MLA（多潜在注意力，DeepSeek V3）

DeepSeek V3 把 KV 压缩进一个小的潜在表示，并在注意力时解压。KV 大小比 `num_heads * head_dim * seq_len` 暗示的小得多。

位置：用 MLA 情形扩展 `memory_model.py::calculate_sizes`，使用潜在维度（`kv_lora_rank`）而不是 `num_kv_heads * head_dim`。

### 双 MLP 解码器

一些模型（例如实验架构）每个块有两个 MLP 而不是一个。轨迹生成需要知道每个块发出两次 `mlp_dense` 运行。

位置：添加一个新的 `sequence` 组（例如 `mlp_dense_2`），让 `trace_generator._emit_sequence` 走两者。

这些都是相对较小的改动（每个约 30–60 行）。YAML + 现有轨迹生成器处理 95% 的新架构而无需碰 Python。

## 在哪里验证

一旦您的 YAML 就位，随附的 `bench/` 验证套件就是粗略检查：在新模型上端到端运行 vLLM + 通过模拟器运行同一工作负载 + 看看它们匹配得多近。如果 TTFT / TPOT / 吞吐量都在约 5% 以内，您的 YAML +（可选的）trace_generator 改动就很好。

验证方法论和逐模型结果参见 GitHub 上的 [`bench/README.md`](https://github.com/casys-kaist/LLMServingSim/tree/main/bench)。

## 接下来

- **[输出数据包](./output-bundle)**：给定一个可用的 YAML，剖析器产生什么 CSV。
- **[模拟器 → 轨迹生成](../simulator/trace-generation)**：trace_generator 在运行时走您的 `sequence:` 做什么。
