---
sidebar_position: 4
title: 故障排查
---

# 故障排查

安装与首次运行期间的常见错误，以及最快的修复方法。

如果你的问题不在此列，请携带完整命令、错误输出以及你的 OS / Docker / GPU 版本，到 [github.com/casys-kaist/LLMServingSim/issues](https://github.com/casys-kaist/LLMServingSim/issues) 提交 bug。

## 子模块缺失

**症状：** 构建失败，报错缺少 `astra-sim/extern/graph_frontend/chakra/` 或 `astra-sim/build/` 下的文件。

**原因：** 克隆时未使用 `--recurse-submodules`。

**修复：**

```bash
git submodule update --init --recursive
```

然后重新运行 `./scripts/compile.sh`。

## `docker: permission denied`

**症状：**

```text
docker: Got permission denied while trying to connect to the
Docker daemon socket
```

**原因：** 你的用户不在 `docker` 组中。

**修复：**

```bash
sudo usermod -aG docker $USER
newgrp docker
# 或注销后重新登录
```

## 未检测到 GPU

**症状：** 在 vLLM 容器内，`nvidia-smi` 提示 `command not found` 或 `no devices found`。

**原因：** NVIDIA Container Toolkit 未安装，或 Docker 未配置使用它。

**修复：** 安装 / 重新配置 toolkit（参见 [先决条件](./installation/prerequisites#install-nvidia-container-toolkit)），并重启 Docker：

```bash
sudo systemctl restart docker
```

然后验证：

```bash
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

如果主机的 `nvidia-smi` 正常但容器内的不行，问题出在 toolkit。如果主机的 `nvidia-smi` 也失败，请先安装 NVIDIA 驱动。

## Hugging Face：受限模型 / 401 / 403

**症状：** 剖析 Llama 3.x 或受限 Qwen 变体时：

```text
huggingface_hub.utils._errors.GatedRepoError: Access to model
meta-llama/Llama-3.1-8B is restricted...
```

**修复：**

1. 在模型页面上接受许可（一次性操作，在 huggingface.co 上）。
2. 在启动 vLLM 容器 **之前** 在 shell 中设置 `HF_TOKEN`：

   ```bash
   export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxxxxxxxx"
   ./scripts/docker-vllm.sh
   ```

token 会自动转发到容器内。在容器内用 `echo $HF_TOKEN` 确认。

## ASTRA-Sim 构建失败

**症状：** `./scripts/compile.sh` 中途报错，通常带有 CMake 或编译器消息。

**常见原因与修复：**

- **容器内缺少构建依赖。** 官方 `astrasim/tutorial-micro2024` 镜像默认包含它们。如果你自定义了镜像，请确保安装了 `cmake`、`g++`、`protobuf-compiler`、`libprotobuf-dev` 和 `libboost-dev`。
- **过期的构建状态。** 清空构建目录后重试：

  ```bash
  rm -rf astra-sim/build/astra_analytical/build/
  ./scripts/compile.sh
  ```
- **在容器外运行。** `compile.sh` 设计为在模拟器容器内运行，而非宿主机。请先使用 `./scripts/docker-sim.sh`。

## `model_parallel_NPU_group <= 0` 或 Chakra `VersionError`

**症状：** Chakra 转换步骤以 `ValueError: model_parallel_NPU_group <= 0` 中止运行，或报 `google.protobuf.runtime_version.VersionError: Detected incompatible Protobuf Gencode/Runtime versions`。

**原因：** Chakra 由 `scripts/compile.sh` 安装到容器的 site-packages，因此已存在的容器会保留首次构建时安装的版本。在拉取转换器或轨迹格式的变更后，这份过期的副本无法再读取模拟器写入的轨迹。

**修复：** 在模拟器容器内重新安装 Chakra：

```bash
cd astra-sim/extern/graph_frontend/chakra && pip3 install .
```

重新运行 `./scripts/compile.sh` 会做同样的事，并附带 C++ 重新构建。

## 容器名已被占用

**症状：**

```text
docker: Error response from daemon: Conflict. The container name
"/servingsim_docker" is already in use by container "abc123..."
```

**原因：** 之前的运行遗留了容器。

**修复：** 重新附加，或删除后重建。

```bash
# 重新附加到现有容器
docker start -ai servingsim_docker

# 或清空并重建
docker rm -f servingsim_docker
./scripts/docker-sim.sh
```

`vllm_docker` 同理。

## 缺少剖析数据

**症状：** 使用没有剖析数据的硬件 / 模型组合运行模拟器：

```text
FileNotFoundError: Profile variant folder not found:
../profiler/perf/RTXPRO6000/meta-llama/Llama-3.1-8B/bf16-kvfp8. Run the
profiler with matching --dtype / --kv-cache-dtype, or pick an existing
variant under ../profiler/perf/RTXPRO6000/meta-llama/Llama-3.1-8B
```

**原因：** `(hardware, model, dtype, kv_cache_dtype)` 元组没有对应的剖析数据包。检查针对的是 **variant 文件夹**，所以消息指向目录而非某个具体 CSV。用 `ls` 查看它打印的父路径，看看你有哪些 variant。

注意 variant 是 *派生* 的，而非选择的：`--kv-cache-dtype fp8` 会追加 `-kvfp8`，`--dtype`（或省略时模型配置的 `torch_dtype`）提供前缀。因此这个错误在你切换精度 flag 而没有对应的剖析运行时会触发，而不仅仅是硬件是新的时。

两个相邻但修复不同的错误：

```text
FileNotFoundError: meta.yaml missing at <variant>/meta.yaml. Re-run the
profiler to produce it.
```

文件夹存在但数据包不完整——通常是剖析运行被中断。

```text
FileNotFoundError: Architecture yaml not found for model_type='gemma2'
at profiler/models/gemma2.yaml. Add profiler/models/gemma2.yaml
describing the architecture.
```

该模型家族还没有目录。参见 **[添加模型架构](../profiler/adding-model-architecture)**。

**修复：** 要么

- 选择已经剖析过的硬件 / 模型 / 精度组合（`ls profiler/perf/`），或者
- 自行运行 **[性能剖析器](../profiler/overview)** 生成缺失的数据包。

## 启动时 `--max-num-batched-tokens` 警告

**症状：**

```text
max-num-batched-tokens=4096 exceeds profiled 2048 for
RTXPRO6000/meta-llama/Llama-3.1-8B/bf16; attention/dense lookups will
extrapolate
```

序列上限也有对应的警告：

```text
max-num-seqs=256 exceeds profiled 128 for
RTXPRO6000/meta-llama/Llama-3.1-8B/bf16; per-sequence lookups will
extrapolate
```

**原因：** 你运行的模拟器超出了性能剖析器扫描的范围（取自 `meta.yaml::engine_effective`）。延迟查找会在测量范围之外线性外推。

两者每个 `(hardware, model, variant)` 只打印 **一次**，而非每个迭代一次，所以只看到一次并不意味着只发生了一次。并且当 `meta.yaml` 中该字段没有 `engine_effective` 条目时它们会静默，因此手工编写的包不会收到任何警告。

**修复：**

- 为获得最佳精度，请在更高的 `--max-num-batched-tokens` 下重新剖析（`MAX_NUM_BATCHED_TOKENS=4096 ./profiler/profile.sh`）。
- 或者保持在剖析的边界内。小幅超界时外推通常没问题；大幅超界可能会漂移。

## 模拟器在大工作负载上卡住 / 极慢

**症状：** 模拟运行但耗时远超预期，尤其是 MoE + EP 或大型前缀缓存时。

**常见原因与修复：**

- **禁用了块复制（block-copy）。** 对于 MoE，请保持 `--enable-block-copy` 开启（默认）。它用一个 transformer 块的轨迹回放所有层，而不是逐层重新计算路由。与 `--expert-routing-policy BALANCED`（默认，确定性）搭配安全；`RR`/`RAND` 会平均掉逐层方差。
- **冗余日志。** `--log-level DEBUG` 会写入大量内容。降到 `--log-level INFO` 或 `WARNING`。
- **`--log-interval` 太小。** 设为 `0.1` 会让 logger 每 100 ms 运行一次；提高到 `1.0`（默认）或更高。

## vLLM 容器内内存不足

**症状：** 性能剖析器在 attention 扫描中途因 CUDA OOM 崩溃。

**修复：** 调低 `profiler/profile.sh` 中的 `MAX_NUM_BATCHED_TOKENS`，或用环境变量跳过重型类别（参见 [性能剖析器 → 运行](../profiler/running)）。

## 仍然卡住？

- **GitHub Issues：** [casys-kaist/LLMServingSim/issues](https://github.com/casys-kaist/LLMServingSim/issues)
- **讨论：** [casys-kaist/LLMServingSim/discussions](https://github.com/casys-kaist/LLMServingSim/discussions)

提交 bug 时，请包含：

1. 你运行的确切命令
2. 完整的错误输出
3. 你的 OS、Docker 版本、NVIDIA 驱动、GPU 型号
4. 你是在模拟器容器内、vLLM 容器内，还是裸机
