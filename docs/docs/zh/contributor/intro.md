---
sidebar_position: 2
title: 上手
---

# 上手

本页带你从全新克隆一步步走到可运行的模拟器。目标：读完本文后，你应该能修改 `serving/` 里的一个 Python 文件、重新运行一次模拟，并在输出的 CSV 中看到你的改动。

如果你只打算读代码（不运行），请直接跳到 **[代码库导览（Codebase tour）](./codebase-tour)**。

## 前置条件

- Linux（已在 Ubuntu 22.04+ 上测试）。macOS 可以编辑代码，但不能运行剖析器 / bench（它们需要 NVIDIA GPU）。
- Docker（最简单的路径），或无法使用 Docker 时的裸机 vLLM 安装器。
- 模拟器容器需要约 5 GB 可用磁盘；如果你还要做剖析或 bench，再额外准备约 10 GB。
- 一个 GitHub 账号（最终 PR 需要）。

运行模拟器本身**不需要** GPU。捆绑的 RTXPRO6000 / H100 剖析包让你无需硬件即可模拟。

## 1. 带子模块克隆

ASTRA-Sim 以 git 子模块形式存在。克隆时务必加上 `--recurse-submodules`：

```bash
git clone --recurse-submodules https://github.com/casys-kaist/LLMServingSim.git
cd LLMServingSim
```

如果你已经克隆了但没有子模块：

```bash
git submodule update --init --recursive
```

## 2. 选择你的容器

两个容器，各司其职：

| 容器 | 镜像 | 何时需要 |
| --- | --- | --- |
| `scripts/docker-sim.sh` | `astrasim/tutorial-micro2024` + Python 依赖 | 运行模拟器。**始终需要。** |
| `scripts/docker-vllm.sh` | `vllm/vllm-openai:v0.19.0` | 剖析新硬件、运行 bench、从 ShareGPT 生成工作负载。**只有当你碰这些时才需要。** |

对大多数贡献工作（调度器、内存模型、轨迹生成器、配置）来说，sim 容器就够了：

```bash
./scripts/docker-sim.sh
```

这会把你带进 `/app/LLMServingSim` 的一个 shell，所有 Python 依赖已装好。仓库根目录是绑定挂载的，所以你在宿主机上的编辑会立即在容器内生效。

## 3. 构建 ASTRA-Sim 和 Chakra

在 sim 容器内，首次运行时：

```bash
./scripts/compile.sh
```

这会编译 ASTRA-Sim 的分析后端（模拟器使用它），并安装 Chakra 轨迹转换器。第一次需要几分钟，增量重建约 30 秒。每当你改动 `astra-sim/` 下的 C++ 源码时都要重跑。

如果编译因缺少依赖而失败，最常见的原因是子模块没有检出。在宿主机上重跑 `git submodule update --init --recursive` 再试一次。

## 4. 冒烟运行

最快的"一切正常吗？"检查是捆绑的单实例轨迹：

```bash
python -m serving \
    --cluster-config configs/cluster/single_node_single_instance.json \
    --dataset workloads/example_trace.jsonl \
    --output outputs/onboarding_smoke.csv \
    --num-reqs 10
```

你应该会看到：

- 启动横幅，随后一行 **KV Cache Initialization**，报告每个实例推导出的容量。
- 每秒一次心跳：`[N.0s] Avg prompt throughput: … tokens/s, Avg generation throughput: … tokens/s`，后面跟着一个缩进的 `├─Running Instance[0]: … reqs, Waiting: … reqs, …` 分支。
- 结尾处带分隔线的 **Throughput Results** / **Prefix Caching Results** / **Instance [0]** 小节，包含 `Total requests`、`Total clocks (ns)`，以及每实例的 TTFT、TPOT、ITL 的均值 / 中位数 / P99，单位毫秒。
- `outputs/onboarding_smoke.csv`，每个请求一行。

如果以上都有了，说明模拟器工作正常。如果报错，参见 **[故障排查（Troubleshooting）](../getting-started/troubleshooting)**。

## 5. 做一处真实改动

是时候真正改点东西了。一个安全的首改：调大默认日志间隔，这样你能更频繁地看到吞吐量更新。

打开 `serving/__main__.py`，找到 `--log-interval` 参数（默认值是 `1.0`）。把默认值改成 `0.5`，保存，然后重跑第 4 步的冒烟命令。你应该会看到两倍多的吞吐量日志行。

玩够了就还原改动（`git checkout serving/__main__.py`）。

## 6. 阅读后续页面

现在你已经准备好了。在开 PR 之前，请浏览：

- **[代码库导览（Codebase tour）](./codebase-tour)**：每类改动所在的位置。
- **[编码规范（Coding conventions）](./conventions)**：让代码库保持可读性的那几条小规则。
- **[验证你的改动（Validating your changes）](./validating-changes)**：如何确认你的改动没有破坏任何东西（我们没有单元测试套件，所以这一点很重要）。
- **[PR 工作流（PR workflow）](./pr-workflow)**：分支、提交信息风格、PR 模板。

## 常见安装坑

1. **忘了 `--recurse-submodules`** → ASTRA-Sim 缺失，`compile.sh` 立即失败。重跑 `git submodule update --init --recursive`。
2. **任务用错了容器** → 剖析器 / bench 脚本会报缺少 CUDA 或 vLLM。换到 `scripts/docker-vllm.sh`。
3. **容器里看不到你的编辑** → 检查你的编辑是否落在克隆的仓库目录下（容器挂载的是仓库根目录，不是你整个 home 目录）。
4. **Python 版本不匹配** → 两个容器都自带正确的 Python；不要自己安装。如果必须裸机运行，`scripts/install-vllm.sh` 负责 vLLM 那边。
5. **`docker-sim.sh` 说容器已存在** → 要么重新附加（`docker exec -it servingsim_docker bash`），要么先删除（`docker rm -f servingsim_docker`）再重跑。

## 去哪里求助

- **GitHub Discussions**：[casys-kaist/LLMServingSim/discussions](https://github.com/casys-kaist/LLMServingSim/discussions)。"怎么做……"类问题的第一站。
- **GitHub Issues**：在 [casys-kaist/LLMServingSim/issues](https://github.com/casys-kaist/LLMServingSim/issues) 下提交，标题带 `[contributor]`，用于环境搭建受阻的情况。
- **给主要贡献者发邮件**：[jhcho@casys.kaist.ac.kr](mailto:jhcho@casys.kaist.ac.kr?cc=hmchoi@casys.kaist.ac.kr) 和 [hmchoi@casys.kaist.ac.kr](mailto:hmchoi@casys.kaist.ac.kr?cc=jhcho@casys.kaist.ac.kr)（尽量同时抄送两人）。
