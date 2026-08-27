---
title: CXL 扩展内存
sidebar_position: 2
---

# CXL 扩展内存

> **本示例演示：** 将 CXL 内存设备建模为介于 NPU 与 CPU 内存之间的第三层，并支持逐层 / 逐块的权重放置规则。

Compute Express Link（CXL）内存扩展允许你通过源自 PCIe 的 CXL.mem 协议为主机挂接额外 DRAM。带宽低于 HBM（甚至低于 DDR5 DIMM），延迟更高，但容量可以做到 **TB 级**，这使它对于在超大模型上扩展内存预算很有吸引力。

LLMServingSim 将 CXL 建模为一个独立内存层，带显式的**放置规则**：由你决定哪些层的权重、哪些 KV 块放在哪个 CXL 设备上。

## 前置条件

- 已配置模拟器容器
- 为 `meta-llama/Llama-3.1-8B` 打包的 RTXPRO6000 剖析数据

## 集群配置

`configs/cluster/single_node_cxl_instance.json`：注意新的顶层 `cxl_mem` 块以及实例上的 `placement` 块：

```json title="configs/cluster/single_node_cxl_instance.json（节选）"
{
  "num_nodes": 1,
  "link_bw": 16,
  "link_latency": 20000,
  "nodes": [
    {
      "num_instances": 1,
      "cpu_mem": {"mem_size": 512, "mem_bw": 256, "mem_latency": 0},
      "instances": [
        {
          "model_name": "meta-llama/Llama-3.1-8B",
          "hardware": "RTXPRO6000",
          "npu_mem": {"mem_size": 96, "mem_bw": 1597, "mem_latency": 0},
          "pd_type": null,
          "tp_size": 1,
          "placement": {
            "default": {
              "weights": "cxl:0",
              "kv_loc": "npu",
              "kv_evict_loc": "cpu"
            },
            "blocks": [
              { "blocks": "0-3",   "weights": "cxl:0" },
              { "blocks": "4-7",   "weights": "cxl:1" },
              { "blocks": "8,9,10","weights": "cxl:2" },
              { "blocks": "11-23", "weights": "cxl:3" },
              { "blocks": "24-31", "weights": "cxl:0" }
            ],
            "layers": {
              "embedding":       {"weights": "cxl:1"},
              "final_layernorm": {"weights": "cxl:2"},
              "lm_head":         {"weights": "cxl:3"}
            }
          }
        }
      ]
    }
  ],
  "cxl_mem": {
    "mem_size": 1024,
    "mem_latency": 250,
    "mem_bw": 60,
    "num_devices": 4
  }
}
```

两个新部分：

### `cxl_mem`（顶层）

| 字段 | 含义 |
| --- | --- |
| `mem_size` | 每设备容量，单位 **GB** |
| `mem_bw` | 每设备带宽，单位 **GB/s** |
| `mem_latency` | 访问延迟，单位 **ns** |
| `num_devices` | CXL 设备数量（`cxl:0` 到 `cxl:N-1`） |

### `placement`（每实例）

告诉模拟器每个权重和每个 KV 块位于何处。

- `default` 适用于未显式提及的层 / 块。
- `blocks` 按解码器块范围列出规则（例如 `"0-3"`、`"4-7"`、`"8,9,10"`、`"11-23"`：逗号和短横线分隔）。
- `layers` 按*命名*层列出规则（例如 `embedding`、`final_layernorm`、`lm_head`：规范层名）。

每条规则设置：

- `weights`：`npu`、`cpu` 或 `cxl:<id>`。层权重所在位置。
- `kv_loc`：活跃 KV 块所在位置。
- `kv_evict_loc`：被逐出的 KV 块溢出到何处。

上面的配置把 32 个解码器块的权重以大致相等的份额分布到 4 个 CXL 设备上，同时把 KV 缓存留在 NPU。

## 运行

```bash
python -m serving \
  --cluster-config 'configs/cluster/single_node_cxl_instance.json' \
  --dtype bfloat16 --block-size 16 \
  --dataset 'workloads/example_trace.jsonl' \
  --output 'outputs/cxl_run.csv' \
  --log-interval 1.0
```

## 预期输出

```text
[10.0s] Avg prompt throughput: 624.0 tokens/s, Avg generation throughput: 180.0 tokens/s
        ├─Running Instance[0]: 4 reqs, Waiting: 1 reqs, Total # 1 NPUs, Each NPU Memory Usage 12412.51 MB (12.622 % Used), Prefix Cache Hit ratio 12.40 %, (3712 / 29944)
        ├─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
        └─CXL[0]/Instance[0]: Total CXL Device Memory Usage 3276.80 MB, 3.200 % Used
[11.0s] Avg prompt throughput: 641.0 tokens/s, Avg generation throughput: 190.0 tokens/s
        ├─Running Instance[0]: 4 reqs, Waiting: 0 reqs, Total # 1 NPUs, Each NPU Memory Usage 12486.51 MB (12.697 % Used), Prefix Cache Hit ratio 12.88 %, (4096 / 31801)
        ├─Node[0]: Total CPU Memory Usage 0.00 MB, 0.000 % Used
        └─CXL[0]/Instance[0]: Total CXL Device Memory Usage 3379.20 MB, 3.300 % Used
```

`CXL[0]/Instance[0]` 这种形式是**不开启** `--enable-prefix-sharing` 时看到的：每个前缀缓存实例一个分支。开启共享后，分支变成 `CXL[i]`，每设备一个。

`npu_mem` 比仅 NPU 的基线低得多，因为权重位于 CXL 上。`cxl_mem` 按设备报告。

## 值得关注的点

- **权重内存变得有弹性。** Llama-3.1-8B 的权重（bf16 下约 16 GB）不再与 KV 缓存争夺 NPU 的 96 GB。代价是解码 TPOT：每次权重加载现在都要付出 CXL 往返（`mem_latency: 250 ns`）加上带宽差距（60 GB/s 对比 HBM 的 1597 GB/s）。
- **多个 CXL 设备 = 带宽条带化。** 4 设备示例近似 `4 × 60 = 240 GB/s` 的聚合权重带宽，仍远低于 HBM，但更大的权重现在放得下了。
- **逐层放置是一个真正的旋钮。** embedding 和 `lm_head` 在每一步都是带宽密集的；把它们卸载到 CXL 比卸载中段解码器权重伤害更大。提供的配置在这方面故意不是最优的，以展示规则长什么样；请为你的工作负载重新平衡。
- **这里 KV 缓存留在 NPU 上**，但你也可以建模 `kv_loc: "cxl:0"` 把 KV 缓存放进 CXL，这对超长上下文解码工作负载有用，代价是 TPOT。

## 相关示例

- **[前缀缓存](./prefix-caching)**：前缀池也可以位于 CXL 中（`--prefix-storage CXL`）。

## 了解更多

- 内存位置枚举（`LOCAL`、`REMOTE`、`CXL`、`STORAGE`）位于 `astra-sim/astra-sim/system/AstraMemoryAPI.hh`，必须与 `serving/core/memory_model.py` 中的 Python 侧一致。
- 轨迹生成器在每个层的 `weight_loc` 字段上发出 `CXL:{id}` 位置标签。参见[轨迹文件格式](../../reference/trace-format)。
