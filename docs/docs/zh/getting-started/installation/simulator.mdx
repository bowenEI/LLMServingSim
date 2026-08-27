---
sidebar_position: 2
title: 模拟器设置
---

# 模拟器设置

模拟器运行在基于 [`astrasim/tutorial-micro2024`](https://hub.docker.com/r/astrasim/tutorial-micro2024) 的 Docker 容器中。该镜像提供 Python 3.10 和 ASTRA-Sim 的 **构建** 依赖——它 **不** 附带本仓库子模块的预构建后端，因此下面的步骤 3 是必需的，而非可选。它也不附带模拟器导入的任何 Python 包；`docker-sim.sh` 会在启动时 pip 安装它们。

这是 **每个人都需要** 的安装路径。如果你还想剖析新硬件或运行端到端 vLLM 验证，请之后继续 **[vLLM 设置](./vllm)**。

## 1. 克隆仓库

仓库以 git 子模块形式包含 ASTRA-Sim 和 Chakra，因此必须使用 `--recurse-submodules` 克隆：

```bash
git clone --recurse-submodules https://github.com/casys-kaist/LLMServingSim.git
cd LLMServingSim
```

如果你已经克隆但没有 `--recurse-submodules`，用下面命令修复：

```bash
git submodule update --init --recursive
```

## 2. 启动模拟器容器

```bash
./scripts/docker-sim.sh
```

这会：

- 将仓库根目录挂载到容器内的 `/app/LLMServingSim`
- 安装模拟器所需的 Python 依赖，其中三个针对镜像的 Python 3.10 **锁定版本**：

  ```
  pyyaml pyinstrument rich pandas==1.5.3 numpy==1.23.5 matplotlib==3.5.3
  ```

  每个都由在此容器内运行的代码导入：`pyyaml` 用于性能剖析器的 `meta.yaml` 和架构目录，`pyinstrument` 由 `serving/__main__.py` 使用，`rich` 供 logger 使用，`pandas` 供调度器 / 轨迹生成器 / PIM 模型使用，`numpy` 供调度器使用，`matplotlib` 供 `bench/core/plots.py` 使用。如果手动安装，请保留这些版本锁定。
- 将你放入 `/app/LLMServingSim` 的 `bash` shell

容器名为 `servingsim_docker`。之后重新附加（例如重启后）：

```bash
docker start -ai servingsim_docker
```

删除并重新创建：

```bash
docker rm -f servingsim_docker
./scripts/docker-sim.sh
```

## 3. 构建 ASTRA-Sim 并安装 Chakra

在模拟器容器内编译分析后端并安装 Chakra：

```bash
./scripts/compile.sh
```

具体做什么：

- 从 `astra-sim/extern/graph_frontend/chakra` 执行 `pip install` Chakra（ASTRA-Sim 消费的 C++ → protobuf 转换器）。
- 编译 ASTRA-Sim 的 **分析后端**（`astra-sim/build/astra_analytical/build.sh`）。

它会（一次）对 Chakra 的 `et_def.proto` 运行 `protoc`，然后运行 `cmake` 和最多 16 线程的 `cmake --build`。在典型机器上构建需要 2–5 分钟，并打印普通的 cmake / make 输出——没有成功横幅可找。改为检查产物：

```bash
ls -l astra-sim/build/astra_analytical/build/AnalyticalAstra/bin/AnalyticalAstra
```

这正是 `serving/__main__.py` 以子进程启动的确切路径，所以只要它存在且可执行，构建就成功了。

:::tip[ns3 后端]
`compile.sh` 中有一个注释掉的 ns3 后端（数据包级网络模拟）块。大多数用户不需要它。只有在你打算传 `--network-backend ns3`（它会启动另一个二进制：`astra-sim/extern/network_backend/ns-3/build/scratch/ns3.42-AstraSimNetwork-default`）时才取消注释。
:::

## 4. 验证安装

在模拟器容器内运行附带的冒烟测试：

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_single_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/example_single_run.csv' \
  --log-interval 1.0
```

你应该看到启动横幅、一行 **KV Cache Initialization**、每模拟秒一个心跳块，以及最终在 `outputs/example_single_run.csv` 的每请求 CSV。如果相反得到 `FileNotFoundError: Profile variant folder not found: ...`，请查看 [故障排查 → 缺少剖析数据](../troubleshooting#missing-profile-data)。

## 大功告成

模拟器已安装。继续以下任一项：

- **[快速入门](../quickstart)**：走一遍示例运行、理解 flag、读取输出。
- **[vLLM 设置](./vllm)**：安装 vLLM 环境，用于剖析新硬件或运行基准测试套件。（可选。）
