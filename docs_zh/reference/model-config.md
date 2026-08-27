---
sidebar_position: 2
title: 模型配置
---

# 模型配置 schema

模型配置文件位于 `configs/model/<org>/<name>.json`，是**原样的 HuggingFace `config.json` 文件**：正是 `AutoModelForCausalLM` 会从 hub 下载的内容。模拟器和性能剖析器只读取其中一小部分字段；其余的被忽略。

本页记录的是其中要紧的子集。

## 文件位置

按模型组织：

```
configs/model/
├── meta-llama/
│   └── Llama-3.1-8B.json
├── Qwen/
│   ├── Qwen3-32B.json
│   └── Qwen3-30B-A3B-Instruct-2507.json
└── ...
```

**[集群配置](./cluster-config)** 中实例的 `model_name` 字段引用的是相对 `configs/model/` 的文件。

如果文件不存在且 `model_name` 看起来像 HF id，性能剖析器会在首次运行时下载并缓存它。模拟器**不会**自动下载；运行前你需要一个本地文件。

## 必填字段（模拟器读取的子集）

| 字段 | 类型 | 使用者 | 说明 |
| --- | --- | --- | --- |
| `model_type` | string | 性能剖析器 | 选择 `profiler/models/<model_type>.yaml` 处的架构 YAML。例如 `llama`、`qwen3`、`qwen3_moe`、`mixtral`、`phimoe` |
| `hidden_size` | int | 两者 | 模型嵌入 / 隐藏维度 |
| `num_hidden_layers` | int | 两者 | 解码器块数 |
| `num_attention_heads` | int | 两者 | 注意力头总数（用于 TP 缩放） |
| `num_key_value_heads` | int | 两者 | 不同的 KV 头数（用于 GQA 缩放） |
| `intermediate_size` | int | 两者 | MLP 中间维度 |
| `vocab_size` | int | 两者 | 嵌入 / `lm_head` 输出维度 |
| `head_dim` | int | 两者 | **当不等于 `hidden_size / num_attention_heads` 时很重要**（Qwen3 有显式 `head_dim`） |
| `max_position_embeddings` | int | 模拟器 | **必填。** 模型的上下文限制。模拟器将其每步 token 预算钳制到该值：`max_num_batched_tokens = min(max_num_batched_tokens, max_position_embeddings)` |

当配置中没有 `head_dim` 时，模拟器回退到 `hidden_size // num_attention_heads`。这对 Qwen3 是错误的（它有 `head_dim: 128` 和 `hidden_size: 2048` / `num_attention_heads: 32` → 会算出 64）。对于 HF 配置中有 `head_dim` 的模型，务必包含 `head_dim`。

## MoE 字段（仅 MoE 模型）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `num_local_experts` | int | 专家总数（Mistral 风格：例如 Mixtral 8x7B 为 `num_local_experts: 8`） |
| `num_experts` | int | 另一种命名（HF / Qwen 风格：例如 Qwen3-30B-A3B 为 `num_experts: 128`） |
| `num_experts_per_tok` | int | 每 token 的 top-K 激活数。典型值：2（Mixtral）、8（Qwen3 MoE） |
| `moe_intermediate_size` | int | 每专家 MLP 中间维度。通常小于稠密的 `intermediate_size` |

模拟器的 `config_builder.py` 接受 `num_local_experts` 或 `num_experts` 中的任意一个，并等价对待。

## 模拟器可能消费的可选字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `torch_dtype` | string | 默认权重 dtype。未传 `--dtype` 时使用。例如 `bfloat16`、`float16`、`float32` |
| `architectures` | array | 第一项的类名仅作信息参考；模拟器通过 `model_type` 分派 |

## 模拟器忽略的字段

HF 配置还有很多模拟器不用的字段——诸如 `bos_token_id`、`eos_token_id`、`attention_dropout`、`rope_*`、`rms_norm_eps`、`initializer_range`、`tie_word_embeddings`。保持 HF 配置的原样即可；被忽略的字段不影响仿真。

`max_position_embeddings` **不在**这一组里，尽管它看起来像纯 HF 字段：见上面的必填表。

`mlp_only_layers` **确实**被忽略，而这条有一个值得知道的后果。Qwen3-MoE 携带它来标记哪些解码器层使用稠密 MLP 而不是 MoE 块，`configs/model/Qwen/Qwen3-30B-A3B-Instruct-2507.json` 带有它。模拟器按*模型*一次性决定 MoE 与否（当配置有 `num_local_experts` 或 `num_experts` 时 `is_moe` 为真），并对每一层都应用 MoE 路径，因此混合模型的稠密层会被建模为 MoE 层。在 Qwen3-30B-A3B 上该列表为空，所以今天不会损失什么——但一个真正混合的配置会被静默错误建模。

## 示例

### Llama 3.1 8B（稠密）

```json
{
  "architectures": ["LlamaForCausalLM"],
  "model_type": "llama",
  "hidden_size": 4096,
  "intermediate_size": 14336,
  "num_attention_heads": 32,
  "num_hidden_layers": 32,
  "num_key_value_heads": 8,
  "vocab_size": 128256,
  "max_position_embeddings": 131072,
  "torch_dtype": "bfloat16"
}
```

（`head_dim` 默认为 `4096 / 32 = 128`，对 Llama 3.1 是正确的。）

### Qwen3-32B（稠密，显式 `head_dim`）

```json
{
  "architectures": ["Qwen3ForCausalLM"],
  "model_type": "qwen3",
  "hidden_size": 5120,
  "intermediate_size": 25600,
  "num_attention_heads": 64,
  "num_hidden_layers": 64,
  "num_key_value_heads": 8,
  "head_dim": 128,
  "vocab_size": 151936,
  "max_position_embeddings": 40960,
  "torch_dtype": "bfloat16"
}
```

（默认会是 `5120 / 64 = 80`，但 Qwen3 用 128。必须包含 `head_dim`。）

### Qwen3-30B-A3B（MoE）

```json
{
  "architectures": ["Qwen3MoeForCausalLM"],
  "model_type": "qwen3_moe",
  "hidden_size": 2048,
  "intermediate_size": 6144,
  "num_attention_heads": 32,
  "num_hidden_layers": 48,
  "num_key_value_heads": 4,
  "head_dim": 128,
  "num_experts": 128,
  "num_experts_per_tok": 8,
  "moe_intermediate_size": 768,
  "vocab_size": 151936,
  "max_position_embeddings": 262144,
  "torch_dtype": "bfloat16"
}
```

## 添加新模型

1. 将原样的 HF `config.json` 放到 `configs/model/<org>/<name>.json`。
2. 确认上面的必填字段都存在。
3. 如果模型的 HF 配置中有 `head_dim`，**显式添加 `head_dim`**。
4. 确保 `profiler/models/<model_type>.yaml` 存在。如果不存在，你需要一个新的架构 YAML，见 **[性能剖析器 → 添加模型架构](../profiler/adding-model-architecture)**。

## 注意事项

1. **`head_dim` 回退是静默的。** 如果忘记包含它，而模型实际的 `head_dim` 又不同于 `hidden_size / num_attention_heads`，模拟器仍会运行，但会算出错误的 KV 缓存大小。对照 HF 模型卡片校验你的配置。
2. **`num_local_experts` 与 `num_experts`**：同一概念，不同模型家族的不同命名约定。选模型 HF 配置用的那个即可；模拟器两者都处理。
3. **`model_type` 区分大小写**，必须精确匹配 `profiler/models/<model_type>.yaml` 处的某个 YAML。
4. **`max_position_embeddings` 会静默封顶 token 预算。** 调度器和轨迹生成器都把它读作 `min(max_num_batched_tokens, max_position_embeddings)`。在短上下文的模型上这会毫无警告地咬人：自带的 `microsoft/Phi-mini-MoE-instruct` 有 `max_position_embeddings: 4096`，因此 `--max-num-batched-tokens 8192` 实际以 4096 运行。它还设定了 `max_num_batched_tokens: 0`（"不限"）的上限，后者解析为 `max_position_embeddings` 而不是无穷大。
5. **它用直接索引读取，而不是 `.get()`。** 没有 `max_position_embeddings` 的配置会在调度器构造时抛出 `KeyError`，而不是回退到默认值。

## 下一步

- **[集群配置](./cluster-config)**：通过 `instances[].model_name` 引用模型配置。
- **[性能剖析器 → 添加模型架构](../profiler/adding-model-architecture)**——何时编写新的 `<model_type>.yaml`。
