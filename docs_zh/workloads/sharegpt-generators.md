---
sidebar_position: 3
title: ShareGPT 生成器
---

# ShareGPT 生成器

ShareGPT 是事实上的标准推理基准测试，是经过人工挑选的真实人类 ↔ ChatGPT 对话数据集，涵盖广泛的 prompt 长度和用例。内置生成器将 ShareGPT（或任意兼容的 Hugging Face 文本数据集）转换为模拟器消费的 JSONL 格式，并为前缀缓存做了正确的分词。

## 快速运行

在 vLLM Docker 容器内的 `/workspace` 下：

```bash
python -m workloads.generators sharegpt \
  --model meta-llama/Llama-3.1-8B \
  --source shibing624/sharegpt_gpt4 \
  --num-reqs 300 --sps 10 --seed 42 \
  --output workloads/sharegpt-llama-3.1-8b-300-sps10.jsonl
```

这会生成一个 flat 格式的工作负载：300 个请求平均以 10 sessions/s 到达，使用 Llama-3.1-8B tokenizer 分词。

`workloads/examples/` 包含面向内置模型的、可直接编辑的模板，复制并调整：

```bash
ls workloads/examples/
# gen-llama-3.1-8b.sh
# gen-qwen3-30b-a3b.sh
# gen-qwen3-32b.sh
```

## 为什么使用 vLLM 容器

生成器导入 `transformers` 用于分词，并且（可选）导入 `vllm` 用于自由生成模式。两者都预装在 vLLM Docker 镜像中。在 `scripts/docker-vllm.sh` 内运行，你就不需要自己管理 Python 依赖。

对于受门控的模型（Llama 3.x 等），在启动容器前设置 `HF_TOKEN`，见 **[安装 → vLLM 设置](../getting-started/installation/vllm)**。

## 选项（分组）

### 源与模型

| Flag | 默认值 | 含义 |
| --- | --- | --- |
| `--model` | （必填） | HuggingFace 模型 id；用于分词（以及可选的自由生成） |
| `--source` | `shibing624/sharegpt_gpt4` | HF 数据集 id 或本地路径。任何带 `conversations` 字段的数据集都可以 |
| `--output` | （必填） | 输出 JSONL 路径 |

### 采样

| Flag | 默认值 | 含义 |
| --- | --- | --- |
| `--num-reqs` | （必填） | 要生成的请求/会话数 |
| `--sps` | （必填） | 每模拟秒的会话数（泊松到达） |
| `--seed` | `42` | 用于采样和到达时间的 RNG 种子 |
| `--first-arrival-sec` | `0` | 第一个请求到达时间的偏移 |

### 长度过滤

从源数据集中丢弃这些范围之外的请求：

| Flag | 默认值 | 含义 |
| --- | --- | --- |
| `--min-input-toks` | `0` | 最小 prompt token 数（分词后） |
| `--max-input-toks` | `16384` | 最大 prompt token 数 |
| `--min-output-toks` | `0` | 最小输出 token 数 |
| `--max-output-toks` | `16384` | 最大输出 token 数 |
| `--max-kv-toks` | `16384` | `input + output` token 数上限（KV 缓存占用） |
| `--max-sessions` | `5000` | 过滤前采样的源会话数上限 |

一个合理的起点：`--min-input-toks 256 --min-output-toks 512` 会过滤掉对真实服务流量没有代表性的过短对话。

### 定长模式

用于受控压力测试，固定 prompt 和输出长度：

| Flag | 默认值 | 含义 |
| --- | --- | --- |
| `--fix-len` | 关 | 启用定长模式 |
| `--fix-input-length` | `128` | prompt token 数 |
| `--fix-output-length` | `512` | 输出 token 数 |

在该模式下，生成器仍然从源数据集拉取真实对话以获得前缀缓存真实性，但会把每个对话截断/填充到固定长度。

### 脉冲到达模式

一种突发式到达模式，近似"整点所有人都来打 API"的生产现象：

| Flag | 默认值 | 含义 |
| --- | --- | --- |
| `--pulse` | 关 | 启用脉冲模式 |
| `--pulse-n` | `10` | 每个脉冲的请求数 |
| `--pulse-delay-sec` | `60` | 脉冲之间的时间 |
| `--pulse-poisson` | 关 | 在每个脉冲内，使用配置的 `--sps` 的泊松到达，而不是一次性全部到达 |

不使用 `--pulse-poisson` 时，脉冲到达都在每个脉冲窗口开始时触发，用于测试模拟器的突发处理行为。

### vLLM 自由生成模式（可选）

不使用源数据集的响应字段作为输出 token，而是用 vLLM **重新生成**输出。这会生成与你在模拟器中运行的模型相匹配的输出：

| Flag | 默认值 | 含义 |
| --- | --- | --- |
| `--use-vllm` | 关 | 使用 vLLM 自由生成输出 |
| `--vllm-tp` | `1` | 离线引擎的 `tensor_parallel_size` |
| `--vllm-dtype` | `bfloat16` | vLLM 权重 dtype |
| `--vllm-max-num-seqs` | `1024` | `max_num_seqs`。故意设得很高——这是吞吐任务，不是延迟测量 |
| `--vllm-max-num-batched-tokens` | `16384` | `max_num_batched_tokens`，同样为吞吐设得很高 |
| `--vllm-max-model-len` | 模型的最大值 | 覆盖 `max_model_len` |
| `--vllm-temperature` | `0.0` | 采样温度。`0` = 贪心，这让给定种子的生成可复现 |
| `--vllm-repetition-penalty` | `1.1` | 降低已生成 token 的权重。`1.0` 禁用它 |

:::note[为什么重复惩罚默认高于 1.0]
在 `1.0` 下自由生成往往会越过自然停止点继续啰嗦，因此 EOS 永远不会触发，每个请求都会跑到 `--max-output-toks`。`1.1` 让自然 EOS 落在典型的 ShareGPT 长度（约 500-1000 token）上，这正是让结果输出长度分布看起来像真实数据集分布的原因。
:::

上面的五个 `--vllm-*` 引擎旋钮是生成任务本身的吞吐设置。它们对模拟运行**没有任何**影响：生成器只记录 token 计数和 id，所以这里的 `--vllm-max-num-seqs 1024` 并不意味着工作负载应该以 `--max-num-seqs 1024` 来模拟。

使用 `--use-vllm` 时：

1. prompt 取自 ShareGPT。
2. vLLM 用该模型生成新的响应。
3. prompt 和响应都被分词；`input_tok_ids` 和 `output_tok_ids` 被填充。

不使用 `--use-vllm` 时：

- prompt 和响应都作为文本来自 ShareGPT 条目。
- 只有 prompt 用 `--model` 的 tokenizer 重新分词，用于 `input_tok_ids`。

当你特别希望输出 token ID 与模型实际会生成的内容一致时，使用 `--use-vllm`。对大多数模拟运行来说这并不需要（模拟器不生成文本，它只计数 token），但对下游评估或想要完全自洽的轨迹时很有用。

## 输出格式

生成器为每个请求写一行 JSONL：

```json
{"input_toks": 1472, "output_toks": 133, "arrival_time_ns": 4059740, "input_tok_ids": [...], "output_tok_ids": [...]}
```

始终是 **flat 格式**：ShareGPT 条目没有依赖链。agentic 工作负载见 **[智能体会话](./agentic-sessions)**。

输出文件名约定为 `sharegpt-<model-short>-<n>-sps<rate>.jsonl`（与内置文件一致）。

## 提示

1. **使用模拟器将要运行的同一个模型进行分词。** 否则模拟器中的前缀缓存命中率不会与生产环境看到的一致。内置的 JSONL 文件遵循这个约定，并与其各自的模型配对。
2. **`--max-sessions` 限制的是源采样，不是输出。** 如果你应用了严格的长度过滤却没有得到足够多的存活请求，就增大它。默认 5000 对大多数 `--num-reqs` 值都够用。
3. **脉冲模式非常适合健全性测试。** 干净的突发模式能暴露平滑泊松到达可能掩盖的调度器行为（队列堆积、公平性、队头阻塞）。
4. **生成速度。** 不使用 `--use-vllm` 时，生成受分词限制，几秒内完成。使用 `--use-vllm` 时，你要付出真实的 vLLM 推理成本，根据 `--num-reqs` 从几分钟到几小时。缓存输出的 JSONL。
5. **跨模拟器运行复用 JSONL。** 生成一次，模拟多次。文件很小（约 MB）且自包含。

## 下一步

- **[JSONL 格式](./jsonl-format)**：生成器产物的 schema 参考。
- **[智能体会话](./agentic-sessions)**：用于闭环工作负载。ShareGPT 生成器只产生 flat 工作负载。
