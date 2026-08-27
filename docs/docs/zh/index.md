---
slug: /
title: LLMServingSim 中文文档
sidebar_label: 文档首页
---

# LLMServingSim 2.0 中文文档

本文档与英文文档一起部署在 [https://llmservingsim.ai](https://llmservingsim.ai)：英文位于 `/en`，中文位于 `/zh`。导航栏中的语言菜单会在中英文对应页面之间切换。

内容覆盖模拟器、性能剖析器（Profiler）、基准验证（Bench）、工作负载、配置参考与贡献指南。数值、命令与行为以代码和官方站点为准。

- **初次使用：** 从[快速开始概述](/zh/getting-started/overview)开始。
- **运行模拟器：** 阅读[快速入门](/zh/getting-started/quickstart)。
- **理解内部实现：** 阅读[模拟器架构](/zh/simulator/architecture)。
- **查询配置：** 浏览 [CLI 参数参考](/zh/reference/cli-flags)。
- **参与贡献：** 阅读[贡献者指南](/zh/contributor/welcome)。

## 目录结构

```
docs/docs/
├── getting-started/          # 快速开始：概述、前置条件、安装（模拟器 / vLLM）、快速入门、故障排查
├── simulator/                # 模拟器：架构、请求生命周期、调度（连续批处理 / 前缀缓存 / KV 缓存与内存）、
│   │                         #   轨迹生成、并行机制、MoE 专家路由、专项主题（PIM 卸载 / 功耗模型）、输出解读
├── profiler/                 # 性能剖析器：概述、运行、输出包、skew 与 alpha 拟合、新增硬件、新增模型架构
├── workloads/                # 工作负载：概述、JSONL 格式、ShareGPT 生成器、Agentic 会话
├── reference/                # 参考：CLI 参数、集群配置、模型配置、PIM 配置、轨迹文件格式、bench CLI
├── examples/                 # 示例：集群配置解析、并行（TP / PP / EP / DP+EP）、分离式服务、
│   │                         #   内存层级（前缀缓存 / CXL / FP8 KV）、高级（功耗建模 / 子批交错）
├── validation.md             # 验证结果（模拟器 vs 真实 vLLM）
├── artifact-evaluation.md    # 论文复现（ISPASS 2026 / IISWC 2024 artifact 分支）
└── contributor/              # 贡献者：欢迎、上手、代码库导览、约定、验证变更、PR 流程
```

## 推荐阅读顺序

1. 第一次使用：`getting-started/overview.md` → `getting-started/installation/prerequisites.md` → `getting-started/quickstart.md`
2. 理解模拟器内部：`simulator/architecture.md` → `simulator/request-lifecycle.md` → `simulator/scheduling/continuous-batching.md`
3. 自定义配置：`reference/cluster-config.md` → `reference/model-config.md` → `reference/cli-flags.md`
4. 添加新硬件 / 模型：`profiler/adding-hardware.md` → `profiler/adding-model-architecture.md`
5. 端到端验证：`bench` 相关 → `validation.md`

## 与英文原版的关系

- 目录与文件名与 `docs/docs/en/` 保持一致；源为 `.mdx` 的页面在中文树中也保留 `.mdx` 扩展名。
- 页面内相对链接指向镜像内的同名文件，可直接跳转。
- 英文原版更新后，本镜像可能滞后；以代码行为和英文文档为准。
