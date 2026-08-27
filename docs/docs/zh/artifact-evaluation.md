---
title: 工件评估
sidebar_position: 7
description: 复现已发表 LLMServingSim 论文中的图表与结果
---

# 工件评估

每篇随附工件的 LLMServingSim 论文都位于自己的分支上，冻结在提交给工件评估委员会时的状态。本页是希望端到端复现已发表图表的评审人与读者的入口。

> **注意：** 工件分支为可复现性而冻结。不要对它们开 PR；新开发请去 `main`。见 **[给贡献者 → PR 工作流](contributor/pr-workflow)**。

## 可用工件

| 论文 | 会议 | 分支 | 复现内容 |
| --- | --- | --- | --- |
| **LLMServingSim 2.0** | ISPASS 2026 | [`ispass26-artifact`](https://github.com/casys-kaist/LLMServingSim/tree/ispass26-artifact) | 图 5–10 |
| **LLMServingSim** | IISWC 2024 | [`iiswc24-artifact`](https://github.com/casys-kaist/LLMServingSim/tree/iiswc24-artifact)，也在 [Zenodo](https://doi.org/10.5281/zenodo.12803583) 发布 | 原论文图表 |

CAL 2025 条目共享 ISPASS 2026 代码库，没有自己的工件分支。

## ISPASS 2026 — `ispass26-artifact`

*Cho, Choi, Heo, Park. "LLMServingSim 2.0: A Unified Simulator for Heterogeneous and Disaggregated LLM Serving Infrastructure", ISPASS 2026. [Zenodo DOI](https://doi.org/10.5281/zenodo.18879965).*

该分支复现论文的**图 5 到图 10**，以及 `evaluation/` 下配套的吞吐量 / 功耗 / 内存 / 延迟解析器。

> 该工件早于 v1.1.0 目录重组和基于 vLLM 的性能剖析器重写，因此在 `ispass26-artifact` 上你会看到较旧的布局（`cluster_config/`、`dataset/`、`output/`、`inference_serving/`、`main.py`），而不是本网站其余部分记录的 `serving/` / `configs/` / `workloads/` / `outputs/` 路径。在工件内时，请遵循分支自己的 README，而不是本网站的 Getting Started。

### 1. 切换到工件分支

```bash
git clone --recurse-submodules https://github.com/casys-kaist/LLMServingSim.git
cd LLMServingSim
git checkout ispass26-artifact
```

如果你已经克隆过，只需 `git checkout ispass26-artifact` 并执行 `git submodule update --init --recursive` 以拉取固定的 ASTRA-Sim 子模块。

### 2. 设置环境

工件自带 Docker 启动器和构建脚本（而不是 `main` 上的双容器拆分）：

```bash
./docker.sh        # 启动工件的模拟器容器
./compile.sh       # 在容器内构建 ASTRA-Sim + Chakra
```

`docker.sh` 把仓库挂载到 `/app/LLMServingSim`。后续所有命令都在容器内的该工作目录中运行。

### 3. 复现单张图

每张图在 `evaluation/` 下都有自己的驱动脚本：

```bash
cd evaluation

bash figure_5.sh        # 硬件覆盖（A6000、H100）
bash figure_6.sh        # 多实例 + P/D 解耦
bash figure_7.sh        # MoE 专家并行 + 卸载
bash figure_8.sh        # 跨 CPU / CXL 池的前缀缓存
bash figure_9.sh        # CXL 内存扩展
bash figure_10.sh       # 功耗与能量建模
```

每个脚本把中间日志写到 `evaluation/figure_X/logs/`，解析出的数字写到 `evaluation/figure_X/parsed/`，最终 PDF 写到脚本旁边。

### 4. 复现全部

```bash
cd evaluation
bash run_all.sh
```

这等同于按顺序运行全部六个 `figure_*.sh` 脚本。在单台工作站上预计需要几个小时；每张图都要运行多次模拟器调用。

### 5. 对照保存的快照比较

冻结的参考输出位于 `evaluation/artifacts/`。要把你生成的解析输出与这些快照比较：

```bash
# 比较每张图
bash compare.sh

# 比较单张图
bash compare.sh 5

# 比较子集
bash compare.sh 5 7 9
```

要目视确认，把重新生成的 `figure_X.pdf` 与每个文件夹中已提交的 `figure_X_ref.pdf`（多面板图为 `figure_Xa_ref.pdf`）做 diff。

### 逐图细节

每个 `evaluation/figure_X/` 文件夹都有自己的 `README.md`，包含该图的目标、轴定义、参考输入、预期 TSV 文件以及 PDF 命名约定。如果某张图复现失败或数字漂移出比较容差之外，从那里开始。

伞形参考是 [`evaluation/README.md`](https://github.com/casys-kaist/LLMServingSim/blob/ispass26-artifact/evaluation/README.md)，它列出了所有图使用的解析器、字体和文件夹布局。

## 复现失败时

几个常见情况：

1. **`compile.sh` 在子模块上报错**：在宿主机上重跑 `git submodule update --init --recursive` 再试一次。子模块固定是工件的一部分。
2. **`figure_X.sh` 能跑但解析输出不匹配**：查看对应的 `evaluation/figure_X/README.md` 了解工件认证时的容差带；只要定性趋势与参考 PDF 一致，精确瓦数或延迟值的小幅漂移是预期的。
3. **某个具体的模拟器命令在分支上失败但在 `main` 上能用**：这是预期的。工件冻结在论文投稿时的状态；之后落在 `main` 上的 bug 修复和新功能不会回移植。
4. **你需要扩展工件**（例如给图 5 加一块新 GPU）：我们建议改在 `main` 上做，并单独引用新结果。工件分支应保持对论文可复现。

## 联系工件作者

工件相关问题（复现失败、环境设置、索取缺失的参考输出），请给主要贡献者发邮件：

- [jhcho@casys.kaist.ac.kr](mailto:jhcho@casys.kaist.ac.kr?cc=hmchoi@casys.kaist.ac.kr)
- [hmchoi@casys.kaist.ac.kr](mailto:hmchoi@casys.kaist.ac.kr?cc=jhcho@casys.kaist.ac.kr)

尽可能同时抄送两人。完整渠道列表见[联系页面](/contact)。
