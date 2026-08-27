---
sidebar_position: 3
title: vLLM 设置（可选）
---

# vLLM 设置

这一步是 **可选的**。只有在你计划以下事项时才需要 vLLM 环境：

- **剖析** 新的 GPU 或模型（`python -m profiler`）
- **基准测试** 真实 vLLM 端到端（`python -m bench run`）
- **验证** 模拟器与 vLLM 的一致性（`python -m bench validate`）
- **生成** ShareGPT 风格的工作负载数据集（`python -m workloads.generators`）

如果你只想在附带硬件（RTXPRO6000 或 RTX 4090）上运行预剖析的模拟，跳过本页。

## 选择安装方式

### Docker（推荐）

Docker 路径使用官方 `vllm/vllm-openai:v0.19.0` 镜像，它已包含 vLLM、PyTorch 和所有 CUDA 依赖。

该标签针对 **CUDA 12.x** 构建。在 CUDA 13.x 主机上，将 `scripts/docker-vllm.sh` 中的镜像行改为 `vllm/vllm-openai:v0.19.0-cu130`。版本锁定不仅关乎驱动：性能剖析器的 MoE 钩子会 patch `FusedMoE.forward_native`，其方法名随版本变化，因此不同的 vLLM 版本可能会静默破坏剖析。

#### 1.（可选）设置 HF_TOKEN

一些模型配置（Llama 3.x、受限 Qwen 变体）需要 Hugging Face token 来自动获取：

```bash
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxx"
```

如果你只剖析开放模型或使用本地存储的配置，可以跳过。

#### 2. 启动 vLLM 容器

在仓库根目录：

```bash
./scripts/docker-vllm.sh
```

这会：

- 通过 `--gpus all` 请求所有 GPU
- 从你的 shell 转发 `HF_TOKEN`
- 将仓库根目录挂载到 `/workspace`（因此 `python -m profiler`、`python -m bench`、`python -m workloads.generators` 都能工作）
- 挂载 `~/.cache/huggingface` 与主机共享模型缓存
- 设置 `--shm-size=16g`（vLLM 处理进程间张量需要）
- 预安装 `datasets` 和 `matplotlib`（性能剖析器和基准测试绘图需要的额外依赖）
- 将你放入 `/workspace` 的 `bash`

容器名为 `vllm_docker`。之后重新附加：

```bash
docker start -ai vllm_docker
```

#### 3. 验证安装

在容器内：

```bash
python -c "import vllm; print(vllm.__version__)"
nvidia-smi
```

你应该看到 vLLM `0.19.0` 和你的 GPU 列出。

### 裸机（uv venv）

对于没有 Docker 的环境，将 vLLM 安装到本地 `uv` venv。

#### 1. 安装 `uv`

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. 运行安装脚本

在仓库根目录：

```bash
./scripts/install-vllm.sh
```

这会：

- 创建带 Python 3.12 的本地 `uv` venv
- 安装 `vllm==0.19.0`（使用 `VLLM_USE_PRECOMPILED=1` 获取预构建的 CUDA wheels）
- 为工作负载生成器和基准测试绘图添加 `datasets` 和 `matplotlib`

运行性能剖析器 / 基准测试前激活 venv：

```bash
source .venv/bin/activate
```

#### 3. 验证安装

```bash
python -c "import vllm; print(vllm.__version__)"
nvidia-smi
```

你应该看到 vLLM `0.19.0` 和你的 GPU。

**裸机注意事项**

**CUDA 驱动不匹配** 是最常见的失败模式。`vllm==0.19.0` wheel 在 `VLLM_USE_PRECOMPILED=1` 下获取的是针对 CUDA 12.x 构建的——在假设预构建 wheel 适用之前，先用 `nvidia-smi` 检查你的驱动。

`VLLM_USE_PRECOMPILED=1` 标志告诉 `uv` 跳过从源码构建 vLLM。如果你的 CUDA 版本与预构建 wheel 不匹配，去掉该标志并接受更长的构建。

在 Docker 之外，你需要自己负责 `HF_TOKEN`、`~/.cache/huggingface` 和 shm 大小。

## 接下来

- **[性能剖析器指南](../../profiler/overview)**：捕获逐层 CUDA 内核时序，形成模拟器消费的按类别 CSV 数据包。
- **[Bench CLI](../../reference/bench-cli)**：端到端运行 vLLM 并对照真实数据验证模拟器，包含两个子命令的所有 flag。
- **[验证](../../validation)**：这些运行产生的精度数字。
