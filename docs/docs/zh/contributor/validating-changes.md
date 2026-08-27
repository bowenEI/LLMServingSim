---
sidebar_position: 5
title: 验证你的改动
---

# 验证你的改动

项目不附带单元测试套件。模拟器是**确定性的**——相同的集群配置、工作负载和标志会精确重现相同的完工时间——所以验证是与记录结果的相等比较，而不是对着图肉眼判断。`serving/validate.sh` 替你运行这个比较。

## 1. 运行验证脚本（每个 PR 都要做）

```bash
./serving/validate.sh
```

两个阶段，总共约八分钟：

1. **行为（Behaviour）** —— `serving/validate-baselines.txt` 中的每个场景，与记录的 `Total clocks (ns)` 比较。覆盖每个集群配置、每种并行形状（TP、PP、DP 及其组合、EP）、前缀缓存及其下层层级、调度器标志、两种路由策略、PIM、CXL、P/D 解耦、智能体会话和两套硬件剖析包。
2. **准确性（Accuracy）** —— 重新生成每个 `bench/examples` 条目的 `outputs/sim.csv` 和 `validation/summary.txt`，并检查两者的 md5。`sim.csv` 是与记录的真实 vLLM 运行对比的每请求 TTFT / TPOT / 延迟；`summary.txt` 是本网站引用的误差表。对两者做摘要可以捕捉到总时钟可能掩盖的漂移，以及一份不再描述其自身 `sim.csv` 的 summary。三张图会重新生成，但**不**做摘要——matplotlib 输出在不同版本间不稳定，一个因错误原因失败的检查会被忽略掉。

一次干净的运行以如下结尾：

```
Behaviour: 58/58 scenarios match their baselines.
Accuracy: all 8 sim.csv + summary.txt files are byte-identical.
```

这就是声称"行为保持不变"的改动所要达到的标准。任何移动了这些数字的重构都不算行为保持不变。

有用的变体：

```bash
./serving/validate.sh --clocks-only     # skip the slow accuracy stage
./serving/validate.sh dp moe_dp_pp      # just these scenarios, while iterating
./serving/validate.sh --list            # scenario names
./serving/validate.sh --help            # all options
```

在模拟器容器内、仓库根目录下运行它。

## 2. 如果有变化，报告它

脚本会打印一张列出所有变动的 markdown 表格，并把同样的内容写进其日志目录下的 `report.md`：

```
## Validation report

Behaviour -- 1/58 scenarios changed:

| scenario | baseline | now | delta |
| --- | --- | --- | --- |
| `moe_dp_pp` | 1435561517 | 1435559904 | -0.0001% |
```

**差异不一定是 bug——但它从来不会不言自明。** 把表格贴进 PR，并针对每一行说明你的改动中是什么导致了这个变化、为什么新数字是对的。评审者无法只看 diff 就区分有意的修复和意外的回退。

如果变化是有意的，在同一 PR 中落地新的事实：

1. 运行 `./serving/validate.sh --update`，然后提交 `serving/validate-baselines.txt`。
2. 如果某个 `sim.csv` 变了，还要运行 `./bench/examples/validate.sh`，并提交每个受影响示例重新生成的 `outputs/sim.csv`、`validation/summary.txt` 和三张图。`sim.csv` 一变，那些图和 summary 就过时了——把它们留在原地，等于为一个已不存在的模拟器发布准确性数字。

:::caution[场景通过并不能证明你的场景被覆盖]
`workloads/example_trace.jsonl` 的 prompt 只有 2-22 个 token，所以大多数场景永远不会填满 KV 缓存，它们的 DP 成员也总是同时排空。这就是 issue #65 能在全绿的 `moe_dp_pp` 下存活的原因：那个 bug 需要一个 DP 成员在另一个成员仍忙时进入空闲。`*_uneven` 和 `saturated_*` 场景正是为这些情形而存在的。如果你的改动针对的是没有场景覆盖的情形，参见[最后一节](#when-the-existing-scenarios-dont-cover-what-you-changed)。
:::

## 3. Bench 验证（影响端到端准确性的改动）

第 1 步的准确性阶段告诉你 `sim.csv` *是否*移动了。这一步告诉你*移动了多少*——当摘要检查失败时运行它，或者当你的改动可能让模拟器输出相对真实 vLLM 发生变化（`scheduler.py`、`trace_generator.py`、`memory_model.py`、剖析查找、MoE 记账中的任何内容）而你想在开 PR 前拿到误差数字时运行它。

bench 模块先捕获一次真实的 vLLM 执行，然后把模拟器对同一数据集的输出与之对比：

```bash
# 1. Rerun the sim side of an existing example
./bench/examples/run.sh RTXPRO6000/Llama-3.1-8B

# 2. Compare against the committed vLLM reference
./bench/examples/validate.sh RTXPRO6000/Llama-3.1-8B
```

输出落在 `bench/examples/RTXPRO6000/Llama-3.1-8B/validation/`：

- `summary.txt`：TTFT / TPOT / 吞吐量的聚合误差。
- 三张 PNG：`latency.png`（每请求延迟 CDF）、`throughput.png`（吞吐量时间线）、`requests.png`（运行中 / 等待曲线）。

已提交的参照基线落在 TPOT 均值 1.7% 以内、端到端延迟均值 2.2% 以内；TTFT 均值在 +1.3% 到 -13.6% 之间——每种配置的表格参见 **[验证（Validation）](../validation)**。
**相对这些基线回退超过约 5% 是阻塞项。** 更小的变动需要在 PR 描述中给出解释（例如："这修复了一个少计 bug；新误差比旧误差更接近真实值"）。

与 `bench/examples/<hardware>/<model>/validation/summary.txt` 中的数字比较，而不是与摘要里约 5% 的数字比较：TTFT 在 MoE 配置上已经是 -13.6%，所以"5% 以内"并不是它目前能达到的标准。

关于验证方法论的更多细节，参见 [`bench/README.md`](https://github.com/casys-kaist/LLMServingSim/blob/main/bench/README.md)。

## 4. 剖析器侧改动（如果你碰了 `profiler/`）

剖析器改动在重新生成 perf 包之前不会反映到模拟器里。跑一次小剖析，确认你的编辑没有破坏流水线：

```bash
# Inside the vLLM container
MODEL=meta-llama/Llama-3.1-8B HARDWARE=RTXPRO6000 \
    ./profiler/profile.sh
```

然后验证模拟器仍能干净地加载它：
`./serving/validate.sh --clocks-only single`。

如果你只改了 alpha 拟合（`fit_alpha.py`），可以用 `SKIP_DENSE=1 SKIP_PER_SEQUENCE=1 SKIP_ATTENTION=1 SKIP_MOE=1 ONLY_SKEW=1 ./profiler/profile.sh` 只刷新 `skew_fit.csv`，而不用重跑其余部分。

## PR 中"这应该能复现"长什么样

在 PR 描述中，写明你运行的确切命令以及输出中的关键数字。示例：

> Validation: `./bench/examples/validate.sh RTXPRO6000/Llama-3.1-8B` →
> TTFT MAPE 2.1% (was 2.3%), TPOT MAPE 1.7% (unchanged), throughput
> 1.2% (was 1.4%).

> Validation: `./serving/validate.sh` → all 58 scenarios match their
> baselines, all 4 `sim.csv` byte-identical.

这给评审者提供了可以重跑的东西，也给你（以及未来阅读 git 日志的人）留下了已检查内容的记录。

## 当现有场景没有覆盖你的改动时

如果你的贡献新增了一个没有捆绑场景覆盖的功能，**把场景作为 PR 的一部分加进去。** 在 `serving/validate.sh` 的 `SCENARIOS` 列表中加一行（如果没有合适的捆绑配置，再加一份 `configs/cluster/<your_scenario>.json`），然后用 `./serving/validate.sh --update <name>` 记录它的基线，并一起提交。这让下一个贡献者可以复现该功能，而不是指望他们自己想出来。

优先选择一个没有你的改动就会*失败*的场景。一个时钟与现有场景一致的用例只验证了标志的解析，仅此而已——检查新数字与最接近的现有数字不同，如果相同，就找一个标志真正起作用的配置（用 `--npu-memory-utilization` 把 KV 缓存压到饱和通常就够了）。

`serving/run.sh` 是每个功能一个示例的菜单，不是测试套件——往里面加东西不会让你的用例得到验证。

对于需要自定义工作负载的功能（新的智能体数据集、特定的 prompt 分布），在 `workloads/` 下提交一份小 JSONL，并在集群配置示例中引用它。不要提交超过几 MB 的任何东西。

## 接下来

- **[PR 工作流（PR workflow）](./pr-workflow)**：如何打包这次改动。
- **[阅读输出（Reading the output）](../simulator/reading-output)**：每请求 CSV 各列的含义（验证时很有用）。
