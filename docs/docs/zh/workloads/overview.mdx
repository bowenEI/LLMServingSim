---
sidebar_position: 1
title: 概览
---

# 工作负载

**工作负载（workload）** 是驱动模拟器请求队列的 JSONL 文件。每一行要么是一个独立请求（flat 格式），要么是一个带链式子请求的会话（agentic 格式）。`python -m serving --dataset` 和 `python -m bench run --dataset` 都消费同一个文件。

工作负载文件位于仓库根目录的 `workloads/` 下。模拟器在启动时读取一次，路由器（router）在模拟时钟到达每个请求的 `arrival_time_ns` 时调度该请求。

## 选择你的路径

- **真实流量（Real-world traffic）**：从 ShareGPT（或任意 Hugging Face 文本数据集）生成 JSONL。真实的 prompt/输出长度分布，可配置到达率。[ShareGPT 生成器](./sharegpt-generators)
- **智能体 / 闭环（Agentic / closed-loop）**：带工具等待时间的多步 LLM 调用（SWE-bench、ReAct、浏览器智能体）。依赖链由模拟器建模。[智能体会话](./agentic-sessions)
- **合成 / 自定义（Synthetic / custom）**：手工编写自己的 JSONL、定长压力测试、回放自己的生产日志，或介于两者之间的任意内容。[JSONL 格式](./jsonl-format)

## 内置工作负载文件

仓库为受支持的硬件 × 模型组合附带了一些开箱即用的工作负载文件。直接把它们放进 `--dataset workloads/<file>.jsonl`：

| 文件 | 格式 | 模型假设 | 用途 |
| --- | --- | --- | --- |
| `example_trace.jsonl` | flat | 任意 | 用于快速入门的微型冒烟测试工作负载 |
| `sharegpt-llama-3.1-8b-300-sps10.jsonl` | flat | `meta-llama/Llama-3.1-8B` | ShareGPT，300 个请求，10 sessions/s |
| `sharegpt-qwen3-32b-300-sps10.jsonl` | flat | `Qwen/Qwen3-32B` | ShareGPT，dense Qwen3 |
| `sharegpt-qwen3-30b-a3b-300-sps10.jsonl` | flat | `Qwen/Qwen3-30B-A3B-Instruct-2507` | ShareGPT，MoE Qwen3 |
| `swe-bench-qwen3-30b-a3b-50-sps0.2.jsonl` | agentic | `Qwen/Qwen3-30B-A3B-Instruct-2507` | 50 个 SWE-bench 会话，低到达率。**此文件没有配套生成器**——`workloads.generators` 只有 `sharegpt` 子命令，因此要生成自己的 agentic 工作负载意味着直接输出 JSONL（见 [智能体会话](./agentic-sessions)） |

这些文件中的 token ID 已经用匹配模型的 tokenizer 预先分词，因此前缀缓存在开箱即用时就能正常工作。在模拟器中对 ShareGPT JSONL 使用*不同*的模型，对长度/到达行为没有问题，但前缀缓存命中率不会与实际情况一致。

## 工作负载如何连接到模拟器

```
workloads/foo.jsonl
        │
        ▼
   Router.load_requests()
        │
        ▼
   _pending_requests (sorted by arrival_time_ns)
        │  (clock advances, arrivals fire)
        ▼
   route_arrived_requests() → Scheduler queue
        │
        ▼
   scheduler.schedule() → Batch → trace → ASTRA-Sim
```

要了解请求的完整旅程，见 **[模拟器 → 请求生命周期](../simulator/request-lifecycle)**。

## 下一步

- **[JSONL 格式](./jsonl-format)**：两种格式的 schema 参考，逐字段说明。
- **[ShareGPT 生成器](./sharegpt-generators)**：从 ShareGPT 或任意 HF 数据集生成真实的工作负载。
- **[智能体会话](./agentic-sessions)**：闭环会话格式和 SWE-bench 示例。
