---
sidebar_position: 3
title: 代码库导览
---

# 代码库导览

本页回答的问题是"我想新增或修改 X，该动哪里？"。它是一张目录地图，不是行为参考手册。至于每个部分*做*什么，请看 **[模拟器（Simulator）](../simulator/architecture)** 和 **[剖析器（Profiler）](../profiler/overview)** 两节。

## 五大领域

```
LLMServingSim/
├── serving/      Simulator       Python, the core loop
├── profiler/     Profiler        Python, vLLM-based latency capture
├── bench/        Bench           Python, real vLLM run + sim validation
├── workloads/    Workloads       JSONL traces + generators
├── configs/      Configs         JSON: cluster / model / PIM
├── scripts/      Env scripts     Docker launchers + builders
└── astra-sim/    Backend         C++ analytical network simulator
```

每个领域都有清晰的边界。**一个典型的 PR 只碰其中一两个领域，而不是全部。** 如果你发现为一次改动要编辑四个领域，停下来重新考虑范围。

## 模拟器（`serving/`）

大多数贡献工作发生在这里。

```
serving/
├── __main__.py              CLI + main loop
└── core/
    ├── scheduler.py         vLLM-style continuous batching
    ├── trace_generator.py   Profile lookup -> text trace
    ├── memory_model.py      KV / weight / CXL byte accounting
    ├── graph_generator.py   Text trace -> Chakra protobuf
    ├── controller.py        ASTRA-Sim subprocess IPC
    ├── router.py            Request routing across instances
    ├── gate_function.py     MoE expert routing
    ├── config_builder.py    Cluster config -> ASTRA-Sim inputs
    ├── power_model.py       Power / energy estimation
    ├── pim_model.py         PIM device model
    ├── request.py           Request / Batch dataclasses
    ├── block_pool.py        Per-tier KV block pool + prefix-cache index
    ├── kv_cache_manager.py  Tiered KV cache manager (block hashing, allocation)
    ├── logger.py            Rich-based logging + stdio capture
    └── utils.py             Model config loading, formatters
```

**按意图找改动位置：**

| 意图 | 改哪里 |
| --- | --- |
| 修改调度策略 | `scheduler.py` |
| 修改延迟查找方式 | `trace_generator.py`（`_lookup_*`） |
| 修改字节记账（KV、权重、前缀缓存） | `memory_model.py` |
| 修改实例间路由 | `router.py` |
| 新增 CLI 标志 | `__main__.py`（argparse），然后逐层传递 |
| 修改 MoE 专家分配 | `gate_function.py` |
| 修改 ASTRA-Sim 输入生成 | `config_builder.py` |
| 新增功耗组件 | `power_model.py` |

## 剖析器（`profiler/`）

```
profiler/
├── __main__.py              CLI dispatch (profile / slice)
├── core/                    internals (runner, engine, categories, fit_alpha)
├── models/<model_type>.yaml Architecture catalogs (one per HF model_type)
├── perf/<hw>/<model>/...    Output bundles (CSV per category)
└── profile.sh               Editable user template
```

**按意图找改动位置：**

| 意图 | 改哪里 |
| --- | --- |
| 新增硬件目标 | 设置 `HARDWARE=` 运行剖析器；输出落在 `profiler/perf/<hw>/`。参见 **[剖析器 / 添加硬件](../profiler/adding-hardware)** |
| 新增模型架构 | 在 `profiler/models/<model_type>.yaml` 放一份 YAML。参见 **[剖析器 / 添加模型架构](../profiler/adding-model-architecture)** |
| 修改 skew alpha 拟合 | `profiler/core/fit_alpha.py` |
| 修改剖析哪些类别 | `profiler/core/categories.py` + `profiler/core/runner.py` |
| 修改输出 CSV 列 | `core/writer.py`（以及 `serving/core/trace_generator.py` 中的 `_load_perf_db()` 来消费它们） |

## Bench（`bench/`）

```
bench/
├── __main__.py              CLI (run / validate)
├── core/                    AsyncLLM driver, recorder, validator
├── examples/<model>/        Committed end-to-end runs
└── results/<run_id>/        Output for ad-hoc runs
```

只有当你修改验证方法论本身（如何驱动 vLLM、比较哪些指标、生成哪些图）时才会碰这里。日常的"我的改动有没有回退？"用途，参见 **[验证你的改动](./validating-changes)**。

## 配置（`configs/`）

```
configs/
├── cluster/<name>.json      Cluster topology (the main thing)
├── model/<org>/<name>.json  Model architecture (subset of HF config.json)
└── pim/<name>.ini           PIM device specs (DRAMSim3 format)
```

集群配置是 `serving/` 之外被编辑最多的文件。新增一个场景几乎总是意味着放一份新的 `configs/cluster/<scenario>.json`，而完全不动模拟器代码。逐字段的 schema 参见 **[参考 / 集群配置](../reference/cluster-config)**。

## 工作负载（`workloads/`）

```
workloads/
├── *.jsonl                  Datasets (one request or session per line)
├── generators/              JSONL builders. One subcommand today: `sharegpt`
└── README.md                JSONL format reference
```

新增一个工作负载生成器是一个范围受限的改动：在 `generators/` 下加一个新模块，以 `python -m workloads.generators.<your_module>` 运行。参见 **[工作负载 / ShareGPT 生成器](../workloads/sharegpt-generators)** 了解现有模式。

## ASTRA-Sim（`astra-sim/`）

C++ 网络模拟器，以子模块形式存在。**除非改动目标是模拟器集成，否则不要编辑。** 大多数模拟器侧的改动永远不会碰它。

你可能编辑的少数几个文件：

| 文件 | 原因 |
| --- | --- |
| `astra-sim/extern/graph_frontend/chakra/src/converter/llm_converter.py` | 新的轨迹 `comm_type` 语法、新的轨迹头字段、新的内存位置枚举 |
| `astra-sim/astra-sim/workload/Workload.cc` | 自定义集合通信发起、`involved_dim` 处理 |
| `astra-sim/astra-sim/system/AstraMemoryAPI.hh` | 新的内存层级枚举（与 `llm_converter.py` 配对） |
| `astra-sim/inputs/...` | 不要编辑。每次运行都由 `config_builder.py` 生成 |

如果你确实改了 ASTRA-Sim，测试前重跑 `./scripts/compile.sh`。Chakra 是*安装*到容器 site-packages 里的，所以单独编辑 `llm_converter.py` 不会有任何效果，直到你重新安装它（`cd astra-sim/extern/graph_frontend/chakra && pip3 install .`，`compile.sh` 会替你完成）。

## 脚本（`scripts/`）

```
scripts/
├── docker-sim.sh            Sim container launcher
├── docker-vllm.sh           vLLM container launcher (profiler / bench)
├── install-vllm.sh          Bare-metal vLLM install (uv venv)
└── compile.sh               ASTRA-Sim + Chakra build
```

你很少会碰这些。如果你要新增入口点，优先用 `python -m <module>`（在现有容器内处理），而不是再加 shell 脚本。

## 测试与夹具

**没有单元测试套件。** 模拟器是确定性的，所以验证方式是与记录结果的精确相等：

```bash
./serving/validate.sh
```

每个场景与记录的 `Total clocks (ns)` 比较，然后每个 `bench/examples` 条目的 `sim.csv` 和 `validation/summary.txt` 按 md5 检查。当有差异时该怎么做，以及当没有场景覆盖你的改动时该怎么做，参见 **[验证你的改动](./validating-changes)**。

当你要加的功能有干净的输入输出（新的 `_lookup_*` 函数、新的内存记账辅助函数）时，在 `serving/validate.sh` 里加一个场景通常是最便宜的固定方式。正式的单元测试框架仍然是一个开放的贡献机会。

## 文档都在哪里

| 受众 | 位置 |
| --- | --- |
| 面向用户的文档（本站） | `docs/` |
| 各模块的开发笔记 | `<module>/README.md`（每个顶层 Python 模块都有一个） |
| 顶层项目 README | `README.md` |
| 给 AI 智能体的项目上下文 | `CLAUDE.md`（与 `AGENTS.md` 对应） |

当你修改行为时，更新 `docs/` 下相关页面。当你新增功能时，如果模块自带的 `README.md` 覆盖了网站没有的内容，也要更新它。

## 接下来

- **[编码规范（Coding conventions）](./conventions)**：每个 PR 都要遵守的规则。
- **[验证你的改动（Validating your changes）](./validating-changes)**：如何证明你的改动有效。
