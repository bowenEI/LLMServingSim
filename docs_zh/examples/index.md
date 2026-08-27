---
title: 示例
---

# 示例

完整的端到端场景。每个场景都附带一份现成的集群配置、一条可以直接复制的运行命令，以及一小段关于其亮点的说明。把它们当作起点——大多数真实实验都是 80% 的某个示例加上 20% 你自己的调整。

## 从这里开始

- **[集群配置详解](./examples/cluster-config-explained)**：驱动每次模拟的单个文件。每个字段的含义、并行度背后的数学原理，以及如何阅读本部分其余示例所基于的配置。

## 按主题浏览

- **[并行度](./examples/parallelism/tensor-parallel)**：TP、PP、EP 与 DP+EP，每种并行在配置中长什么样、何时该选哪种，以及它们在 MoE 中如何组合。
- **[分离式服务](./examples/disaggregated/multi-instance)**：带路由器的多实例、预填充/解码分离，以及 PIM attention 卸载。对真实生产布局与计算分离（compute disaggregation）进行建模。
- **[内存层级](./examples/memory-tiers/prefix-caching)**：前缀缓存、CXL 扩展内存、FP8 KV 缓存。扩展内存相关特性。
- **[高级](./examples/advanced/power-modeling)**：功耗建模与子批交错，在特定场景下才划算的小众特性。

> **在找工作负载？** 构建或生成驱动这些示例的 JSONL 文件的内容在独立章节中：
> **[工作负载](./workloads/jsonl-format)**：扁平的 ShareGPT 轨迹、agentic 会话，以及生成它们的生成器。

## 每个示例的布局

每个示例页面都遵循同一套模板：

1. **演示内容**：一句话总结。
2. **前置条件**：你需要哪条安装路径（大多数只需要模拟器容器）。
3. **集群配置**：带注释的 JSON 文件。
4. **运行命令**：可复制的精确 CLI 调用。
5. **预期输出**：吞吐日志和 CSV 长什么样。
6. **亮点**：要点。
7. **相关示例**：指向类似或后续示例的链接。

新手快速上手流程：从 **[集群配置详解](./examples/cluster-config-explained)** 开始 → 然后看 **[张量并行](./examples/parallelism/tensor-parallel)**（最简单的非平凡示例）→ 再选择与你研究问题最匹配的主题。
