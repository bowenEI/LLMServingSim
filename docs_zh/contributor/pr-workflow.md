---
sidebar_position: 6
title: PR 工作流
---

# PR 工作流

一份贡献如何从你的 fork 进入 `main`。只读一遍；之后每个 PR 除了实际工作外，大约只需十分钟的流程开销。

## 分支模型

- **`main`**：活跃的开发分支。所有 PR 都落在这里。
- **工件分支（Artifact branches）**：按论文组织的可复现性分支，以会议名称命名（例如 `ispass26-artifact`）。**不要对这些分支开 PR。** 它们冻结在工件提交时的状态。
- **你的工作**：从 `main` 拉出的功能分支，命名要有描述性（`add-deepseek-v3`、`fix-evict-accumulation`、`docs-cluster-config`）。即使你有权限也不要直接推 `main`。

```bash
git checkout main
git pull
git checkout -b add-deepseek-v3
```

## 提交卫生

- **简短祈使句单行。** 与现有日志风格一致：`Fix incorrect evict_size accumulation`、`Add Qwen3 model support`、`Document MoE expert routing`。
- **每次提交只做一个逻辑改动。** 一次提交里既重构又加功能，是评审者的噩梦。
- **不要 amend 已发布的提交。** 如果已经推上去了，用新提交跟进。评审开始*之前*强推你的分支没问题，之后通常不行。
- **这个仓库没有 pre-commit 钩子**，所以提交时不会自动运行任何东西，`--no-verify` 也没有可绕过的。下面的检查都得你自己跑。
- **不要加 `Co-authored-by`**，除非真的有人和你结对编程了这个提交。

一份好的提交信息：

```
Fix evict_size accumulation when prefix cache spills to CPU

Spilling counted the block twice: once in the NPU eviction and
again when the second-tier pool inserted it. Drop the second
increment; the test in single_node_memory_instance.json now
matches the bench reference.
```

一份差的：

```
fixes
```

## 推送之前

过一遍检查清单：

1. **冒烟运行通过。** 参见 **[验证你的改动（Validating your changes）](./validating-changes)** 第 1 步。
2. **与你改动相关的目标场景通过。** 第 2 步。
3. **如果你的改动影响端到端准确性，bench 验证没有回退。** 第 3 步。
4. **规范检查清单**：`getattr` 回退、`head_dim` 处理、只用英文、层名、不改 `astra-sim/inputs/`。参见 **[编码规范（Coding conventions）](./conventions)**。
5. **行为变了就更新文档。** `docs/` 下相关页面，以及适用的模块 `README.md`。
6. **diff 里没有机器相关路径或生成文件。** 用 `git diff --stat` 和 `git diff --check` 做 sanity check。

## 开 PR

推送到你的 fork（或有直接权限时的分支）：

```bash
git push -u origin add-deepseek-v3
```

然后对 `casys-kaist/LLMServingSim:main` 开 PR。描述应该包含：

```
## What this changes

A 1-3 sentence summary of the user-visible change.

## Why

The motivation: the bug it fixes, the feature it enables, the
research question it lets you ask.

## Validation

The exact command(s) you ran and the key result. For example:

  ./bench/examples/validate.sh RTXPRO6000/Llama-3.1-8B
  -> TTFT MAPE 2.1% (was 2.3%), TPOT 1.7% (unchanged)

## Notes

Anything subtle: known limitations, related issues, follow-ups
you intentionally did not include.
```

你不需要重型模板。验证部分是唯一不可协商的部分：它给评审者提供具体可重跑的东西，也给 git 日志留下已检查内容的记录。

## 评审是什么样子

- **初次回复**：第一轮通常在 2-3 天内。与 KAIST（UTC+9）的时区重叠有帮助，但不是必需。
- **评审者**：至少一位主要贡献者（[@JaehongCho](https://github.com/JaehongCho)、[@hmchoi](https://github.com/hmchoi)），加上所改领域的负责人。纯文档 PR 一个批准就够了。
- **什么会被阻塞 vs. 什么只会被挑刺**：
  - **阻塞项（Blockers）**：无法解释的 `./serving/validate.sh` 差异、超过约 5% 的 bench 回退、违反"永远不要做"清单的规范问题、新标志缺文档。
  - **挑刺（Nits）**：命名、代码风格偏好、文档措辞。评审者会说"nit:"或用 GitHub 标签。同意就改；不同意就用一句话说明理由。
- **对话风格**：简洁直接。"这对 MoE 行不通"不是人身攻击；它比礼貌版本更快。以同样方式回应。

## 压缩、变基，还是合并？

项目把大多数 PR 压缩成 `main` 上的单个提交，PR 标题成为提交信息。你不需要事先清理分支的中间提交。如果你的 PR 确实适合拆成多个提交（例如一个重构加上依赖它的功能），在描述里说明，维护者会变基而不是压缩。

## 署名

外部贡献者在两个地方获得署名：

1. **GitHub 提交历史**：你的作者身份在合并时得到保留。
2. **`CONTRIBUTORS.md`**：维护者会加一行，包含你的 GitHub 用户名和一个指向 PR 或 issue 的链接——合入的补丁放在"Code"下，定位到真实问题的 issue 放在"Reports and analysis"下。报告有自己的小节而不是脚注，修复的变更日志条目也会提到你。

你不需要在 PR 里把自己加进贡献者列表。维护者会在合并时添加。

## 合并之后

- **开始下一次改动前先拉取 `main`。** 你的本地分支不再具有权威性。
- **在本地和远端删除已合并的分支**（合并后 GitHub 会提供一个按钮；本地用 `git branch -d add-deepseek-v3`）。
- **合并后在 `main` 上重跑你的场景。** 没有测试 CI 盯着：唯一的 workflow 是 `deploy-docs.yml`，它只构建文档站点，对模拟器什么都不说。如果有什么被评审漏掉的坏了，你发现它的方式是自己在 `main` 上跑 `./serving/validate.sh`。
- **我的 PR 放了一周没人评审。** 用一句话 ping 一下 PR。维护者确实会漏看通知。
- **评审者要求了我不同意的改动。** 在评论里解释你的理由。如果评审者回复后你仍然不同意，可以标记另一位主要贡献者来裁决。我们宁愿讨论，也不愿落地错误的设计。
- **我的改动让 bench 回退超出了预期。** 不要合并它。把 PR 开成 draft，并在描述中标记回退；我们一起来判断是你的改动有 bug、现有基线有 bug，还是验证方法论有 bug。
- **我在 `main` 上搞坏了东西。** 这会发生。开一个带 `Fix ...` 提交的后续 PR；不要向 `main` 执行 `git push --force`。

## 接下来

现在你有了完整的图景。去挑一个入门 issue，或者开一个新 issue（标题带 `[contributor]`）讨论你想做什么。

欢迎上船。
