---
title: PIM 注意力卸载
sidebar_position: 3
---

# PIM 注意力卸载

> **本示例演示：** 将注意力计算从 GPU 卸载到 PIM（processing-in-memory，存内计算）设备上，同时让层的其余部分留在 GPU 上。

注意力的内存带宽瓶颈使它天然适合 PIM——PIM 把计算单元放在 DRAM 内部。LLMServingSim 将注意力建模为一个独立的设备绑定块；打开 `--enable-attn-offloading` 会把轨迹中的 GPU 注意力内核替换为 PIM 注意力内核。

这是**计算拆分**：注意力在 PIM 上运行，层的其余部分在 NPU 上运行，模拟器协调两者之间的交接。

## 前置条件

- 已配置模拟器容器
- 为 `meta-llama/Llama-3.1-8B` 打包的 RTXPRO6000 剖析数据
- 来自 `configs/pim/` 的 PIM 设备配置（例如 `DDR4_8GB_3200_pim`）：每个都是一个描述 PIM 底层的 DRAMSim3 INI 文件。

## 集群配置

`configs/cluster/single_node_pim_instance.json`：注意节点 `cpu_mem` 上的 `pim_config` 字段：

```json title="configs/cluster/single_node_pim_instance.json（节选）"
{
  "num_nodes": 1,
  "link_bw": 16,
  "link_latency": 20000,
  "nodes": [
    {
      "num_instances": 1,
      "cpu_mem": {
        "mem_size": 512,
        "mem_bw": 256,
        "mem_latency": 0,
        "pim_config": "DDR4_8GB_3200_pim"
      },
      "instances": [
        {
          "model_name": "meta-llama/Llama-3.1-8B",
          "hardware": "RTXPRO6000",
          "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
          "pd_type": null,
          "tp_size": 1
        }
      ],
      "power": { "...": "see provided config for full power model" }
    }
  ]
}
```

PIM 的接法：

- `cpu_mem.pim_config: "DDR4_8GB_3200_pim"`：指向 `configs/pim/DDR4_8GB_3200_pim.ini`（描述 PIM 侧计算与内存的 DRAMSim3 INI 文件）。
- GPU 实例其余部分不变。PIM 注意力通过 CLI flag 在运行时选择，而不是通过配置。

## 运行

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_pim_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --enable-attn-offloading \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/pim_offload_run.csv' \
  --log-level WARNING
```

`--enable-attn-offloading` 就是把轨迹中的注意力内核从 NPU 剖析数据切换到 PIM 剖析数据的开关。其余部分（qkv_proj、o_proj、mlp）仍在 GPU 上运行。

## 预期输出

```text
[10.0s] Avg prompt throughput: 1104.0 tokens/s, Avg generation throughput: 520.0 tokens/s
        ├─Running Instance[0]: 8 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 63412.51 MB (64.499 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 11040)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
[11.0s] Avg prompt throughput: 1138.0 tokens/s, Avg generation throughput: 540.0 tokens/s
        ├─Running Instance[0]: 8 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 63486.51 MB (64.574 % Used), Prefix Cache Hit ratio 0.00 %, (0 / 12178)
        └─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
```

**心跳输出中没有 PIM 字段。** 卸载改变的是轨迹中注意力的 `comp_time`，因此它的效果体现在生成吞吐量和 TPOT 上，而不是利用率计数器。要判断 PIM 是否成为瓶颈，可以把 TPOT 与不带 `--enable-attn-offloading` 的同一工作负载对比，或者用 `--save-trace-text` 检查轨迹并查看 `PIM` 标记块。

## 值得关注的点

- **解码 TPOT 通常会改善**，因为长 KV 缓存上的注意力受内存带宽限制。PIM 的带宽特性与 GPU HBM 截然不同，在长上下文、解码密集型工作负载下，即使单次操作吞吐更慢，PIM 路径也可能胜出。
- **预填充 TTFT 可能回退**，因为预填充期间的注意力更受计算限制，PIM 每通道更窄的算力在这里帮不上忙。可以与子批交错（参见 Advanced）配合，用 GPU 上的预填充计算重叠 PIM 上的解码注意力。
- **NPU 内存下降**：KV 缓存现在位于 PIM 内存中，为权重或更大的批次释放约 10–30 GB 的 NPU 内存。

## 相关示例

- **[子批交错](../advanced/sub-batch-interleaving)** —— 自然的后续步骤。重叠 GPU 与 PIM 的工作以弥补预填充回退。
- **[预填充/解码拆分](./prefill-decode-split)**：在解码密集型工作负载上做专业化的另一种方式，但是整实例粒度而非逐层粒度。

## 了解更多

- PIM 设备模型位于 `serving/core/pim_model.py`；轨迹生成器在卸载的注意力块周围发出 `PIM {channel}` / `PIM END` 标记（参见[轨迹文件格式](../../reference/trace-format)）。
- `configs/pim/<name>/` 中的 DRAMSim3 INI 文件配置 PIM 底层。要添加新的底层，就在那里新建一个目录，并把 `pim_config` 指向它。
