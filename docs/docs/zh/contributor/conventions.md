---
sidebar_position: 4
title: 编码规范
---

# 编码规范

一份简短的清单。开 PR 前浏览一遍。其中没有一条是随意的；每一条都至少让项目吃过一次亏。

## Python 风格

- **4 空格缩进，函数 / 变量用 snake_case，类用 PascalCase。** 与你在编辑的文件中的周边代码保持一致。
- **不强制使用格式化工具。** 除非你在重写整个文件，否则不要在整份文件上跑 black / ruff format。风格噪音会掩盖真正的 diff。
- **导入**：保持最小且一致。`serving/` 模块使用相对导入（`from .scheduler import …`）。
- 代码、注释、日志消息和 docstring **只用英文**。韩文 / 其他语言的标识符和注释会在评审中被标记出来。
- **Docstring**：可选。如果要写，写成一行，解释函数*为什么*存在，而不是*做什么*。签名已经说明了做什么。
- **不要顶层 print。** 使用 `serving/core/logger.py`（大多数文件里已经以 `logger` 导入）：
  ```python
  logger.info(...)
  logger.warning(...)
  logger.success(...)   # Rich-styled green check
  ```

## CLI 标志规范

- **CLI 标志用连字符**：`--cluster-config`、`--max-num-seqs`、`--enable-prefix-caching`。
- **内部 Python 用下划线**：`cluster_config`、`max_num_seqs`、`enable_prefix_caching`。
- **布尔标志使用 `BooleanOptionalAction`**，这样 `--enable-X` 和 `--no-enable-X` 都能用：
  ```python
  parser.add_argument('--enable-prefix-caching',
                      action=argparse.BooleanOptionalAction,
                      default=True)
  ```
- **适用时沿用 vLLM 的命名**（`--max-num-batched-tokens`、`--block-size`、`--kv-cache-dtype`）。从 vLLM 过来的用户不应该需要重新学习。

## 文件与配置命名

- **JSON 配置文件名**：描述性的 snake_case（`single_node_pim_instance.json`，而不是 `singleNodePimInstance.json`）。
- **一个配置 = 一个场景。** 不要在不同示例之间复用同一个集群 JSON；复制它。
- **不要提交机器相关的路径。** 代码和配置中的所有路径都必须相对于仓库根目录。

## 永远不要做的事

下面每一条都对应一次真实的事故或强烈的项目偏好：

1. **不要给 `Request` 属性加 `getattr(request, 'attr', default)` 回退。** 在 `Request.__init__` 里初始化所有属性并直接访问。回退会掩盖初始化 bug。

2. **不要假设 `hidden_size == num_heads * head_dim`。** 有些模型（Qwen3）不满足这个等式。始终：
   ```python
   head_dim = config.get('head_dim', n_embd // n_head)
   q_dim   = n_head * head_dim         # NOT n_embd
   kv_dim  = kv_head * head_dim        # NOT n_embd // group
   ```

3. **不要发明层名。** 模拟器发出的每个名字都必须出现在架构 YAML 的目录中。规范集合：`qkv_proj`、`o_proj`、`gate_up_proj`、`act_fn`、`down_proj`、`rotary_emb`、`qk_norm`、`attention`、`layernorm`、`final_layernorm`、`embedding`、`lm_head`、`sampler`、`moe`。

4. **除非改动目标是模拟器集成**（Chakra 转换器、`Workload.cc`、输入配置），否则**不要编辑 `astra-sim/`**。大多数贡献永远不会碰这个目录。

5. **不要手动编辑 `astra-sim/inputs/*.json`。** 这些文件每次运行都由 `config_builder.py` 重新生成；你的编辑会被静默覆盖。

6. **不要提交大型生成文件。** 轨迹文件、本地运行产生的 `outputs/*.csv`、`.et` protobuf、以及超出 gitignore 模式的剖析器包 CSV 都应该留在本地。gitignore 已经配置好了；只是不要 `git add -A`。

7. **不要指望自动化替你兜底。** 没有 pre-commit 钩子，也没有测试 CI：唯一的 GitHub workflow 是 `deploy-docs.yml`，它只在 `main` 上推送且改动触及 `docs/**` 时构建文档站点。[验证你的改动](./validating-changes) 中的每一项检查都是手动的。
8. **不要为不可能发生的情况添加错误处理。** 相信内部不变量；只在边界处验证（CLI 参数、JSON 配置加载、数据集解析）。在 `scheduler.py` 内部做防御式编程会让文件没法读。

9. **不要超出手头任务添加功能。** 修 bug 不需要顺带清理。三行相似代码好过一个过早的抽象。

10. **不要添加解释代码在做什么的注释。** 标识符名字已经说明了。注释保留给*为什么*某处不显而易见的东西会是这样（一个隐藏的不变量、一个 bug 的绕行方案、一篇论文的引用）。

## 层名与单位提醒

这两点最容易绊倒新贡献者：

- **剖析器 CSV 以微秒存储（`time_us` 列）。** 模拟器在加载时乘以 1000 并取整到纳秒。不要除两次。
- **给 ASTRA-Sim 的通信大小是*总量*（不是每 NPU）字节。** ASTRA-Sim 内部会除以环大小。如果你传的是每 NPU 大小，每个集合通信都会小 N 倍。

## 调度器不变量

这些是有历史渊源的。每一条都曾被破坏过，而且每一次都耗费了真实的调试时间。

- **没有 prefill 阶段，也没有 decode 阶段。** 一个请求只是追赶到 `num_tokens_reached`，所以 `num_new = num_tokens_reached - num_computed_tokens` —— 稳态 decode 时为 1，被恢复的请求为整个剩余部分。`Request.is_prefill()` 是被有意删除的：它读取 `original_input`，因此会把被恢复请求的重计算误读为解码。按**调度 token 数**为轨迹分类（`> 1` 是 prefill 块，`== 1` 是 decode），永远不要按阶段标志分类。
- **永远不要从 `num_computed_tokens` 推导序列长度。** 抢占会把它重置为 0。`num_tokens_reached` 才是独立的计数器，对应 vLLM 的 `len(_all_token_ids)`。
- **`num_computed_tokens` 在*调度*时推进**，与 vLLM 的 `_update_after_schedule` 一致，`Batch.scheduled_tokens` 是 `add_done` 所依据的快照。改在完成时推进会让 `pp_size > 1` 把同一批 token 调度两次。
- **不要添加"抢占时保留 decode 状态"的特殊情况。** `num_computed_tokens = 0` 是 vLLM 自己的行为，不是重新 prefill：`free_blocks` 保留块的哈希，所以重新准入时 `get_computed_blocks` 能找到仍然驻留的内容，更低的层级会返回已写下的内容。只有剩余部分会被重算。之前两次试图特殊处理这个问题的尝试，代价分别是 375 次抢占 / 293k 个重算 token，以及 41,569 次抢占 / 6 TB 的交换。
- **阶段 B 从不抢占，并且在任何发生过抢占的步骤上整体跳过。** 这条防抖动规则是承重的；没有它，运行集合会在 抢占 → 回填 → 抢占 之间震荡。
- **`schedule()` 只有一个，前缀缓存开与关都用它。** 池以 vLLM 的方式处理 `enable_caching=False` —— 走同一个空闲链表分配，从不索引 —— 所以不要再加第二个调度器。

## 轨迹格式不变量

如果你碰 `trace_generator.py` 或 `graph_generator.py`：

- **第一**层的 `input_loc` 和**最后**一层的 `output_loc` 必须是 `REMOTE:{node_id}`。Chakra 转换器会从第一层发出 `MEM_LOAD`、从最后一层发出 `MEM_STORE`；如果任一个是 `LOCAL` 而又没有配置本地内存，ASTRA-Sim 会崩溃。
- sampler 的 `output_loc` 和 `output_size` 才是喂给 `MEM_STORE` 的东西。不要把它们放在 `lm_head` 上：送回宿主的是采样出的 token id，而不是 logits。
- **一层的 `output_size` 不是下一层的 `input_size`**，也不应该是。`qkv_proj` 发出 Q+K+V，而 `rotary_emb` 只声明 Q+K，`attention` 从缓存读取 K/V 而不是激活。不存在可以"恢复"的链条。
- **永远不要按轨迹行数切分流水线阶段。** 阶段只能在 transformer 块边界处切割，那是上游 `output_size` 与下游 `input_size` 是同一个张量（隐藏状态）的唯一位置。ASTRA-Sim 的分析后端以 `(tag, src, dst, chunk_size, chunk_id)` 为键跟踪其 send/recv，所以大小不匹配会让接收 NPU **静默死锁**而不是报错。这正是轨迹头里 `pp_stage_boundaries` 存在的原因。
- **不要在 `_axis_bracket` 中"恢复"对数空间插值**，因为剖析器的扫描网格是几何的。网格间距决定内核在哪里采样；混合方式决定两个样本如何组合；内核在每个轴上是线性的。对数混合的估计偏差高出 11.6-14.4%，而线性只有 2.3-3.7%（对 `profiler/perf/` 中每个包的留一法实测）。

## 提交与 PR 风格

简版（完整流程在 **[PR 工作流（PR workflow）](./pr-workflow)**）：

- **提交信息**：简短祈使句单行。
  - 好的：`Fix incorrect evict_size accumulation`、`Add Qwen3 model support`。
  - 差的：`fixes`、`update scheduler.py`、`WIP`。
- **每次提交只做一个逻辑改动。** 不要把重构和功能绑在一起。
- **PR 描述包含你运行的验证命令**，这样评审者可以重跑 —— 通常是 `./serving/validate.sh`，如果有数字变动还要附上报告表。

## 接下来

- **[验证你的改动（Validating your changes）](./validating-changes)**：如何证明改动真的有效。
- **[PR 工作流（PR workflow）](./pr-workflow)**：分支模型、署名、评审预期。
