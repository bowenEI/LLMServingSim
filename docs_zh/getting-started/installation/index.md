---
title: 安装
---

# 安装

从一台干净机器到可用的 LLMServingSim 安装。三个短页面，前两个覆盖大多数用户需要的全部内容，第三个可选。

1. **先决条件** — 开始前的快速检查：OS、Docker、NVIDIA Container Toolkit、可选的 Hugging Face token。[先决条件](./installation/prerequisites)
2. **模拟器设置** — 每个人都需要的路径。克隆仓库、启动模拟器容器、构建 ASTRA-Sim、用冒烟测试验证。[模拟器设置](./installation/simulator)
3. **vLLM 设置（可选）** — 仅在你想要剖析新硬件、运行 vLLM 基准测试或验证模拟器时需要。Docker 或裸机。[vLLM 设置](./installation/vllm)

如果你只打算在附带的硬件（RTXPRO6000 或 RTX 4090）上运行预剖析的模拟，可以完全跳过 vLLM 设置。
