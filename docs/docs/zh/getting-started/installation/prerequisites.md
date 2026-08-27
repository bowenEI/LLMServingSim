---
sidebar_position: 1
title: 先决条件
---

# 先决条件

LLMServingSim 运行在带 Docker 的 Linux 上。模拟器一侧运行在 CPU 上，但性能剖析器和 vLLM 基准测试需要 NVIDIA GPU。

## 系统

| | 模拟器所需 | 性能剖析器 / 基准测试所需 |
| --- | --- | --- |
| **OS** | Linux（Ubuntu 22.04+ 已测试） | Linux（Ubuntu 22.04+ 已测试） |
| **Docker** | ✓ | ✓（或裸机安装） |
| **NVIDIA GPU** |  | ✓ |
| **NVIDIA Container Toolkit** |  | ✓（用于 GPU 透传到 Docker） |
| **CUDA 驱动** |  | 默认 `vllm/vllm-openai:v0.19.0` 镜像需要 12.x；13.x 需要使用 `v0.19.0-cu130` 标签 |
| **磁盘** | 约 3 GB | 额外约 10 GB（vLLM 镜像 + HF 模型缓存） |
| **内存** | 16 GB | 建议 32 GB+ |

如果你只打算运行预剖析的模拟（例如附带的 RTXPRO6000 剖析数据），**不需要** GPU。

## 安装 Docker

如果你还没有 Docker：

```bash
# Ubuntu，官方快速安装脚本
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

验证：

```bash
docker run --rm hello-world
```

## 安装 NVIDIA Container Toolkit

仅 GPU 容器（性能剖析器 / 基准测试）需要。在 Ubuntu 上：

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

验证：

```bash
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

你应该能看到你的 GPU 列出。如果没有，参见 [故障排查 → 未检测到 GPU](../troubleshooting#gpu-not-detected)。

## Hugging Face token（可选）

一些模型配置（例如 Llama 3.x、受限的 Qwen 变体）位于 HF 认证之后。如果你设置以下内容，性能剖析器可以自动获取它们：

```bash
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxx"
```

运行预剖析的模拟永远不需要 token。但任何涉及 Hub 的操作都需要：

- **剖析** 受限模型，性能剖析器会在首次运行时自动获取其 `config.json`。
- **`bench run`**，会加载真实权重——下载量远大于配置文件。
- **`workloads.generators`**，会拉取源数据集（配合 `--use-vllm` 时还会拉取模型）。

`scripts/docker-vllm.sh` 会把 `HF_TOKEN` 从你的 shell 转发到容器内，并挂载 `~/.cache/huggingface`，因此下载与主机共享、只发生一次。

从 [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) 获取 token。

## 下一步

你已经准备好安装了。继续 **[模拟器设置](./simulator)**——这是每个人都需要的主要安装路径。
