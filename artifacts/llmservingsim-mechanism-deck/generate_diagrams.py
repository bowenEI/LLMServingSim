#!/usr/bin/env python3
"""Generate editable draw.io diagrams and matching SVGs for the slide deck."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
DIAGRAM_DIR = ROOT / "diagrams"
FIGURE_DIR = ROOT / "figures"

FONT = "Noto Sans CJK SC"
INK = "#17324D"
MUTED = "#60758A"
BLUE = "#2F6B9A"
BLUE_FILL = "#E8F2FA"
TEAL = "#2A7F72"
TEAL_FILL = "#E7F4F1"
ORANGE = "#C86F2D"
ORANGE_FILL = "#FFF0E3"
GRAY = "#AAB7C4"
GRAY_FILL = "#F4F7F9"
GREEN = "#4D7C5D"
GREEN_FILL = "#EAF3EC"
WHITE = "#FFFFFF"


@dataclass
class Box:
    id: str
    x: int
    y: int
    w: int
    h: int
    title: str
    lines: list[str] = field(default_factory=list)
    fill: str = WHITE
    stroke: str = INK
    dashed: bool = False
    title_size: int = 22
    body_size: int = 18


@dataclass
class Edge:
    id: str
    source: str
    target: str
    label: str
    color: str = INK
    dashed: bool = False
    waypoints: list[tuple[int, int]] = field(default_factory=list)


def box_style(box: Box) -> tuple[str, str]:
    dashed = "dashed=1;dashPattern=8 8;" if box.dashed else ""
    value = "<b>" + escape(box.title) + "</b>"
    if box.lines:
        value += f"<br><font style=\"font-size:{box.body_size}px\">" + "<br>".join(escape(s) for s in box.lines) + "</font>"
    style = (
        f"rounded=1;arcSize=8;whiteSpace=wrap;html=1;{dashed}"
        f"fillColor={box.fill};strokeColor={box.stroke};strokeWidth=2;"
        f"fontColor={INK};fontFamily={FONT};fontSize={box.title_size};"
        "align=center;verticalAlign=middle;spacing=8;"
    )
    return style, value


def make_drawio(path: Path, title: str, subtitle: str, boxes: list[Box], edges: list[Edge]) -> None:
    mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="Codex", version="26.0.9", pages="1")
    diagram = ET.SubElement(mxfile, "diagram", id=path.stem, name=title)
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        page="1",
        pageWidth="1600",
        pageHeight="900",
        grid="1",
        gridSize="10",
        guides="1",
        tooltips="1",
        connect="1",
        arrows="1",
        fold="1",
        pageScale="1",
        pageBackgroundColor="#FFFFFF",
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    for cid, value, x, y, w, h, size, color in [
        ("title", f"<b>{escape(title)}</b>", 40, 20, 1520, 50, 28, INK),
        ("subtitle", escape(subtitle), 40, 70, 1520, 30, 14, MUTED),
    ]:
        cell = ET.SubElement(
            root,
            "mxCell",
            id=cid,
            value=value,
            style=(
                "text;html=1;strokeColor=none;fillColor=none;whiteSpace=wrap;"
                f"fontFamily={FONT};fontSize={size};fontColor={color};align=center;verticalAlign=middle;"
            ),
            vertex="1",
            parent="1",
        )
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), **{"as": "geometry"})

    for box in boxes:
        style, value = box_style(box)
        cell = ET.SubElement(root, "mxCell", id=box.id, value=value, style=style, vertex="1", parent="1")
        ET.SubElement(
            cell,
            "mxGeometry",
            x=str(box.x), y=str(box.y), width=str(box.w), height=str(box.h),
            **{"as": "geometry"},
        )

    for edge in edges:
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
            f"endArrow=block;endFill=1;strokeWidth=3;strokeColor={edge.color};"
            f"fontColor={edge.color};fontFamily={FONT};fontSize=14;labelBackgroundColor=#FFFFFF;"
        )
        if edge.dashed:
            style += "dashed=1;dashPattern=8 8;"
        cell = ET.SubElement(
            root,
            "mxCell",
            id=edge.id,
            value=escape(edge.label),
            style=style,
            edge="1",
            parent="1",
            source=edge.source,
            target=edge.target,
        )
        geometry = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        if edge.waypoints:
            points = ET.SubElement(geometry, "Array", **{"as": "points"})
            for x, y in edge.waypoints:
                ET.SubElement(points, "mxPoint", x=str(x), y=str(y))

    ET.indent(mxfile, space="  ")
    path.write_text(ET.tostring(mxfile, encoding="unicode", xml_declaration=True), encoding="utf-8")


def svg_text(x: int, y: int, text: str, size: int, color: str = INK, weight: int = 400, anchor: str = "middle") -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{FONT}" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}">{escape(text)}</text>'
    )


def make_svg(path: Path, title: str, subtitle: str, boxes: list[Box], edges: list[Edge]) -> None:
    by_id = {b.id: b for b in boxes}
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">',
        '<rect width="1600" height="900" fill="#FFFFFF"/>',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="context-stroke"/></marker></defs>',
        svg_text(800, 55, title, 30, INK, 700),
        svg_text(800, 88, subtitle, 15, MUTED),
    ]

    for edge in edges:
        a, b = by_id[edge.source], by_id[edge.target]
        ax, ay = a.x + a.w / 2, a.y + a.h / 2
        bx, by = b.x + b.w / 2, b.y + b.h / 2
        if edge.waypoints:
            def boundary_point(box: Box, toward_x: float, toward_y: float) -> tuple[float, float]:
                cx, cy = box.x + box.w / 2, box.y + box.h / 2
                dx, dy = toward_x - cx, toward_y - cy
                scales = []
                if dx:
                    scales.append((box.w / 2) / abs(dx))
                if dy:
                    scales.append((box.h / 2) / abs(dy))
                scale = min(scales) if scales else 0.0
                return cx + dx * scale, cy + dy * scale

            sx, sy = boundary_point(a, *edge.waypoints[0])
            tx, ty = boundary_point(b, *edge.waypoints[-1])
            points = " ".join([f"{sx},{sy}"] + [f"{x},{y}" for x, y in edge.waypoints] + [f"{tx},{ty}"])
            lx, ly = edge.waypoints[len(edge.waypoints) // 2]
        elif abs(bx - ax) >= abs(by - ay):
            x1 = a.x + a.w if bx > ax else a.x
            y1 = ay
            x2 = b.x if bx > ax else b.x + b.w
            y2 = by
            midx = (x1 + x2) / 2
            points = f"{x1},{y1} {midx},{y1} {midx},{y2} {x2},{y2}"
            lx, ly = midx, min(y1, y2) - 8
        else:
            x1 = ax
            y1 = a.y + a.h if by > ay else a.y
            x2 = bx
            y2 = b.y if by > ay else b.y + b.h
            midy = (y1 + y2) / 2
            points = f"{x1},{y1} {x1},{midy} {x2},{midy} {x2},{y2}"
            lx, ly = max(x1, x2) + 8, midy - 6
        dash = ' stroke-dasharray="10 8"' if edge.dashed else ""
        out.append(f'<polyline points="{points}" fill="none" stroke="{edge.color}" stroke-width="3" marker-end="url(#arrow)"{dash}/>' )
        if edge.label:
            out.append(f'<rect x="{lx-65}" y="{ly-18}" width="130" height="25" rx="3" fill="#FFFFFF" opacity="0.94"/>')
            out.append(svg_text(int(lx), int(ly), edge.label, 14, edge.color, 500))

    for box in boxes:
        dash = ' stroke-dasharray="10 8"' if box.dashed else ""
        out.append(f'<rect x="{box.x}" y="{box.y}" width="{box.w}" height="{box.h}" rx="8" fill="{box.fill}" stroke="{box.stroke}" stroke-width="2"{dash}/>' )
        cx = box.x + box.w // 2
        title_y = box.y + 28 if box.lines else box.y + box.h // 2 + 6
        out.append(svg_text(cx, title_y, box.title, box.title_size, INK, 700))
        line_step = max(22, box.body_size + 4)
        for i, line in enumerate(box.lines):
            out.append(svg_text(cx, box.y + 55 + i * line_step, line, box.body_size, INK, 400))

    out.append('</svg>')
    path.write_text("\n".join(out), encoding="utf-8")


def build_mechanism() -> tuple[list[Box], list[Edge]]:
    boxes = [
        Box("config", 50, 130, 210, 90, "配置与工作负载", ["cluster/model JSON", "workload JSONL"], GRAY_FILL, GRAY),
        Box("profiler", 320, 130, 240, 90, "vLLM Layerwise Profiler", ["真实 kernel 路径", "TP 单卡形状仿真"], BLUE_FILL, BLUE),
        Box("perfdb", 620, 130, 230, 90, "性能数据库", ["dense / attention", "per-seq / MoE CSV"], BLUE_FILL, BLUE),
        Box("router", 50, 330, 180, 100, "Router", ["到达时间", "实例路由"], GRAY_FILL, GRAY),
        Box("scheduler", 280, 310, 220, 140, "Scheduler", ["continuous batching", "token/seq/KV 预算", "running → waiting"], GREEN_FILL, GREEN),
        Box("batch", 550, 330, 200, 100, "Batch 快照", ["scheduled_tokens", "Q/K 列表与命中"], GREEN_FILL, GREEN),
        Box("trace", 800, 300, 250, 160, "Trace Generator", ["遍历架构 sequence", "查表/插值 comp_time", "tensor bytes + comm_size"], BLUE_FILL, BLUE),
        Box("chakra", 1100, 320, 190, 120, "Chakra Converter", ["trace rows → ET DAG", "COMP/MEM/COMM"], GRAY_FILL, GRAY),
        Box("astra", 1340, 300, 210, 160, "ASTRA-Sim", ["依赖就绪发射", "解析网络 + 内存", "返回全局 cycle"], ORANGE_FILL, ORANGE),
        Box("kv", 280, 550, 220, 150, "Tiered KV Manager", ["block hash / refcount", "NPU 命中 + 下层召回", "preemption/recompute"], TEAL_FILL, TEAL),
        Box("memory", 550, 570, 210, 110, "NPU / CPU / CXL", ["容量与块池", "召回进入关键路径"], TEAL_FILL, TEAL),
        Box("dag", 840, 570, 190, 110, "Chakra ET DAG", ["数据依赖", "关键路径决定完成时刻"], GRAY_FILL, GRAY),
        Box("backend", 1100, 550, 220, 150, "Analytical Backends", ["Compute: replay ns", "Memory: L + S/B", "Network: collective events"], ORANGE_FILL, ORANGE),
        Box("metrics", 1360, 520, 180, 120, "输出指标", ["TTFT / TPOT / ITL", "throughput / clocks"], GREEN_FILL, GREEN),
        Box("loop", 560, 770, 520, 70, "完成事件更新状态 → 新一轮调度；空闲时跳到下一到达时刻", [], WHITE, INK, True, 22),
    ]
    edges = [
        Edge("e1", "config", "router", "请求到达", GRAY),
        Edge("e2", "config", "profiler", "模型/硬件", GRAY, True),
        Edge("e3", "profiler", "perfdb", "time_us", BLUE),
        Edge("e4", "perfdb", "trace", "按维查表", BLUE),
        Edge("e5", "router", "scheduler", "入队", GREEN),
        Edge("e6", "scheduler", "batch", "调度快照", GREEN),
        Edge("e7", "batch", "trace", "形状参数", BLUE),
        Edge("e8", "trace", "chakra", "11 字段 rows", BLUE),
        Edge("e9", "chakra", "astra", ".et 工作负载", ORANGE),
        Edge("e10", "scheduler", "kv", "分配/回收", TEAL),
        Edge("e11", "kv", "memory", "块驻留/召回", TEAL),
        Edge("e12", "trace", "dag", "节点属性", GRAY),
        Edge("e13", "dag", "backend", "就绪节点", ORANGE),
        Edge("e14", "backend", "astra", "完成事件", ORANGE),
        Edge("e15", "astra", "metrics", "cycle", GREEN),
        Edge("e16", "metrics", "loop", "完成通知", INK, True, [(1450, 750), (1080, 750)]),
        Edge("e17", "loop", "scheduler", "状态反馈", INK, True, [(520, 800), (520, 500), (390, 500)]),
    ]
    return boxes, edges


def build_latency() -> tuple[list[Box], list[Edge]]:
    boxes = [
        Box("shape", 50, 130, 1500, 70, "一次迭代的输入形状", ["x = (T, Nseq, prefill_chunk, kv_prefill, n_decode, kv_decode, TP, PP, EP, placement)"], GRAY_FILL, GRAY, False, 19, 14),
        Box("comp", 60, 250, 440, 240, "计算时延：测量驱动", ["CSV: time_us → round(1000·time_us) ns", "1D: t(x)=t0+(x−x0)(t1−t0)/(x1−x0)", "Attention: 4D 多线性插值", "Skew: t=tmean+α(tmax−tmean)", "MoE: max_r lookup(tokens_r, experts_r)"], BLUE_FILL, BLUE, False, 24, 18),
        Box("mem", 580, 250, 440, 240, "访存时延：容量 + 排队", ["KV/token/rank = 2·Hkv·Dhead·L·bkv / Nnpu", "Nblock=floor((u·MNPU−W)/Bblock)", "tmem(S)=Lmem+floor(S/Bmem)", "PER_NODE / POOL：同设备 FIFO 串行", "write-through 只计能耗；recall 在关键路径"], TEAL_FILL, TEAL, False, 24, 18),
        Box("comm", 1100, 250, 440, 240, "通信时延：消息 + collective", ["TP: S_AR = T·H·b", "P/D: S_KV = 2·Hkv·Dhead·T·bkv / TP", "EP: AG[(H+E)b], RS[Hb]", "单跳: t=h·Llink+S/Blink", "Ring 近似: AR≈2(N−1)(L+S/(N·B))"], ORANGE_FILL, ORANGE, False, 24, 18),
        Box("dag", 180, 620, 1240, 180, "统一为 Chakra DAG 的关键路径", ["start(v)=max_{u∈pred(v)} finish(u)", "finish(v)=start(v)+d(v),  d(v)∈{tcomp,tmem,tcomm}", "Titer=max_{v∈sink} finish(v)；重叠由依赖与资源队列自然产生，而不是简单求和"], WHITE, INK, False, 22, 16),
        Box("legend_comp", 60, 530, 440, 50, "COMP_NODE · profile replay", [], BLUE_FILL, BLUE, False, 18),
        Box("legend_mem", 580, 530, 440, 50, "MEM_NODE · analytical memory", [], TEAL_FILL, TEAL, False, 18),
        Box("legend_comm", 1100, 530, 440, 50, "COMM_NODE · analytical network", [], ORANGE_FILL, ORANGE, False, 18),
    ]
    edges = [
        Edge("s1", "shape", "comp", "kernel shape", BLUE, False, [(280, 220), (280, 240)]),
        Edge("s2", "shape", "mem", "bytes / tier", TEAL, False, [(800, 220), (800, 240)]),
        Edge("s3", "shape", "comm", "group / size", ORANGE, False, [(1320, 220), (1320, 240)]),
        Edge("c1", "comp", "legend_comp", "映射", BLUE),
        Edge("c2", "legend_comp", "dag", "COMP_NODE", BLUE, False, [(280, 600), (800, 600)]),
        Edge("m1", "mem", "legend_mem", "映射", TEAL),
        Edge("m2", "legend_mem", "dag", "MEM_NODE", TEAL, False, [(800, 600)]),
        Edge("n1", "comm", "legend_comm", "映射", ORANGE),
        Edge("n2", "legend_comm", "dag", "COMM_NODE", ORANGE, False, [(1320, 600), (800, 600)]),
    ]
    return boxes, edges


def main() -> None:
    DIAGRAM_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    specs = [
        ("system-mechanism", "LLMServingSim 2.0：周期级协同仿真的闭环机制", "Python 前端复现服务语义，Chakra 表达依赖，ASTRA-Sim 推进硬件事件", build_mechanism()),
        ("latency-model", "计算、访存与通信时延如何汇聚为一次迭代", "测量驱动的计算节点 + 解析内存/网络节点 + DAG 关键路径", build_latency()),
    ]
    for stem, title, subtitle, (boxes, edges) in specs:
        make_drawio(DIAGRAM_DIR / f"{stem}.drawio", title, subtitle, boxes, edges)
        make_svg(FIGURE_DIR / f"{stem}.svg", title, subtitle, boxes, edges)


if __name__ == "__main__":
    main()
