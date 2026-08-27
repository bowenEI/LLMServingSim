---
sidebar_position: 2
title: JSONL 格式
---

# JSONL 格式

工作负载文件是行分隔的 JSON（`.jsonl`）。每一行是一个 JSON 对象，表示**要么**一个独立请求（flat 格式），**要么**一个带链式 LLM 调用的会话（agentic 格式）。两种格式可以在同一个文件中共存，加载器按行自动检测。

## Flat 格式

每一行是一个独立请求：

```json
{"input_toks": 1472, "output_toks": 133, "arrival_time_ns": 4059740, "input_tok_ids": [1, 2, 3, ...], "output_tok_ids": [4, 5, 6, ...]}
```

### 字段

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | --- | --- |
| `input_toks` | int | ✓ | prompt token 数 |
| `output_toks` | int | ✓ | 要生成的 token 数 |
| `arrival_time_ns` | int | ✓ | 请求到达的时间（纳秒，相对于模拟开始时刻） |
| `input_tok_ids` | list&lt;int&gt; | 可选 | 预先分词的 prompt ID。**没有它们，该请求的前缀缓存会被禁用**，见 [下面](#why-token-ids-matter) |
| `output_tok_ids` | list&lt;int&gt; | 可选 | 预先分词的输出 ID。附加到同一个哈希链上，因此生成的 token 会成为可缓存的块 |

两者只在接收实例开启了前缀缓存时才被读取；使用 `--no-enable-prefix-caching` 时它们会被完全忽略。

没有任何检查保证 `len(input_tok_ids) == input_toks`。两者用途不同——`input_toks` 驱动调度和 KV 容量计算，ids 只驱动块哈希——所以不匹配也不会报错。它只会静默地改变被哈希的块数量：链覆盖 `floor(len(ids) / block_size)` 个块，因此 ids 短于 `input_toks` 时 prompt 的尾部不可缓存，ids 更长时会哈希请求从未计算过的块。

### 何时使用 flat

- ShareGPT 风格的基准测试（独立 prompt）。
- 生产轨迹回放（每个 prompt 是一个独立请求）。
- 固定泊松到达模式的压力测试。

## Agentic 格式

每一行是一个**会话**，包含多次链式 LLM 调用。每次调用的到达时间由前一次调用的完成时间加上两者之间的 `tool_duration_ns` 决定，模拟器遵循这条依赖链：

```json
{
  "session_id": "session_0",
  "arrival_time_ns": 4059740,
  "sub_requests": [
    {"input_toks": 1472, "output_toks": 133, "tool_duration_ns": 127348767},
    {"input_toks": 1582, "output_toks": 125, "tool_duration_ns": 197295027},
    {"input_toks": 1734, "output_toks": 77,  "tool_duration_ns": 0}
  ]
}
```

### 顶层字段

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | --- | --- |
| `session_id` | string | 可选 | 用于键控依赖链的标识符。默认为从运行中的请求 id 推导出的 `session_<n>`。当你想让该值稳定且有意义时提供它 |
| `arrival_time_ns` | int | ✓ | **第一个**子请求到达的时间 |
| `sub_requests` | list&lt;object&gt; | ✓ | 有序的 LLM 调用链。空列表会被**静默跳过**——该行不贡献任何请求，也不会报错 |

### 子请求字段

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | --- | --- |
| `input_toks` | int | ✓ | 本次 LLM 调用的 prompt token 数 |
| `output_toks` | int | ✓ | 生成的 token 数 |
| `tool_duration_ns` | int | 可选（默认 `0`） | 本次调用完成后、下一个子请求变为可调度之前要等待的时间。通过 `.get(..., 0)` 读取，因此省略它意味着下一个调用立即释放 |
| `input_tok_ids` | list&lt;int&gt; | 可选 | 与 flat 格式相同 |
| `output_tok_ids` | list&lt;int&gt; | 可选 | 与 flat 格式相同 |

最后一个子请求的 `tool_duration_ns` 会被读取但没有效果——没有下一个调用需要释放——所以把它设为 `0` 是惯例而非要求。

### 何时使用 agentic

- **使用工具的智能体**（浏览器智能体、代码智能体、带检索步骤的 RAG）。
- **SWE-bench 风格的基准测试**，其中每个会话涉及多次编辑 + 测试 + 重试。
- **多轮对话**，轮次之间带模拟的用户思考时间。

模拟器通过 `Router._deferred_sessions` 处理依赖链——最初只排队第一个子请求；其余的在各自的前驱完成后释放。运行时机制见 **[模拟器 → 请求生命周期](../simulator/request-lifecycle#agentic-sessions-when-stage-10-is-not-the-end)**。

## 混合格式

单个 `.jsonl` 文件可以同时包含 flat 和 agentic 条目。加载器检查每一行：

- 有 `sub_requests` 键？→ agentic。
- 否则 → flat。

这偶尔很有用：agentic SWE-bench 工作负载可以包含几个 flat 的"基线"请求用于健全性检查。

## 为什么 token ID 很重要

可选的 `input_tok_ids` 字段是前缀缓存端到端工作的关键：

- 没有它，模拟器只知道"prompt 有 N 个 token"，但无法识别两个 prompt 何时共享前缀。
- 有了它，路由器在加载时计算 token ID 的逐块哈希。调度器随后在运行时使用这些哈希，将请求与前缀缓存索引进行匹配。

对于许多请求共享系统 prompt 的 ShareGPT 风格轨迹，拥有 token ID 可以使前缀缓存命中率比没有时高 5-10 倍。**尽可能预先分词。** 内置生成器会帮你做这件事。

如果你的数据集只有原始文本，你有两个选择：

1. 在工作负载生成时运行 tokenizer 来填充 `input_tok_ids`。ShareGPT 生成器就是这么做的。
2. 完全跳过 token ID，接受**零**前缀缓存命中。

选项 2 不是优雅降级。`request_block_hashes()` 对没有 `input_hash_ids` 的请求返回空链，这会关闭该请求的前缀缓存，同时保持分配不变。不存在基于 `input_toks` 的更粗略回退键：索引以块哈希为键，没有哈希的请求永远不会匹配、永远不会被插入。因此一次运行可能开启了 `--enable-prefix-caching`，却因为工作负载没有 token id 而报告 0% 命中率。

### `output_tok_ids` 不是装饰性的

链构建在 `input_hash_ids + output_hash_ids` 之上，因此生成的 token 也成为可缓存的块。这正是让会话的第 N+1 轮命中第 N 轮输出的机制，而这是 agentic 或多轮工作负载中大部分复用所在。省略它们，你保留了 prompt 侧的复用，却失去了跨轮复用。

模拟器可以预先构建整条链，因为它提前知道完整序列，这与 vLLM 不同——vLLM 是每个发出的 token 扩展一次链。这并不意味着未来信息到达了调度器：对链的每次读取都由 `num_computed_tokens` 把关，因此一个块只有在它的 token 真正被计算之后才能被插入。

**使用模拟器所运行的同一个模型进行分词。** 用 Llama tokenizer 生成的工作负载在 Qwen3 模拟中不会产生有用的前缀命中，token 流完全不同。

## 加载器检查什么、不检查什么

`router.load_requests()` 刻意保持精简。它用 `json.loads` 读取每一行，根据是否存在 `sub_requests` 分发，并直接索引它需要的字段。**没有校验流程**，也没有带行号的错误报告。

这在实践中意味着：

| 畸形输入 | 会发生什么 |
| --- | --- |
| 缺少 `input_toks` / `output_toks` / `arrival_time_ns` | 对该字段抛 `KeyError`，只有裸 traceback，没有行号 |
| 非整数 token 计数 | 能转就静默地 `int()` 强转（`"133"` 可以，`13.7` 截断），否则抛 `ValueError` |
| `len(input_tok_ids) != input_toks` | 接受。只改变 prompt 中可哈希的部分 |
| 负的 `arrival_time_ns` | 接受。请求排到最前面，并在第一次迭代时被路由 |
| 空的 `sub_requests` | 该行被静默跳过，不贡献任何请求 |
| 重复的 `session_id` | 后面的会话在 `_deferred_sessions` 中**覆盖**前面的。*任一*会话的完成都会释放后面会话的子请求，因此前面的链永远不会推进，而后面的链被驱动两次 |

文件中的到达顺序无关紧要：加载器读完所有内容后按 `arrival_time_ns` 对 `_pending_requests` 排序，这也是 flat 与 agentic 行能够正确交错的原因。

如果你是程序化生成工作负载，在写入侧做校验。内置生成器就是这么做的。

## 注意事项

1. **`arrival_time_ns` 是模拟器时钟**，不是墙上时钟。以 10 sessions/s 生成的工作负载，300 个会话的到达时间跨度为 30 秒，那是 30 个模拟秒，不是 30 个真实秒。
2. **Token ID 是整数，不是字符串。** 你的 tokenizer 输出的任何内容（`tokenizer.encode(...).ids`）都直接放进去。
3. **输出 token ID 在运行时使用。** 解码*计时*不需要它们（计时来自 token 计数），但它们扩展前缀缓存哈希链。丢弃它们会损失跨轮命中。
4. **跨工作负载混合 tokenizer 没问题，但在一个文件内混合不行。** 所有 `input_tok_ids` 应该来自同一个 tokenizer。

## 下一步

- **[ShareGPT 生成器](./sharegpt-generators)**：从真实 ShareGPT 轨迹生成带正确分词结果的 flat 工作负载。
- **[智能体会话](./agentic-sessions)**：深入探讨 agentic 格式以及如何构建你自己的链。
