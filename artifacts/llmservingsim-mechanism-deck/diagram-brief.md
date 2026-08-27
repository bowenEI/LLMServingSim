# Diagram Brief

## User Goal
- Output: editable draw.io diagrams plus a Southeast University SimplePlus Beamer deck.
- Audience: systems/architecture researchers familiar with LLM inference.
- Must communicate: the simulator's closed-loop execution, and concrete compute, memory, and communication latency models.
- Must not do: invent a black-box formula; collapse ASTRA-Sim scheduling into a simple serial sum; use decorative shapes without meaning.

## Source Inventory
| id | source | type | role | priority | notes |
|---|---|---|---|---|---|
| S1 | `serving/__main__.py`, `serving/core/scheduler.py` | source | content/structure | high | frontend event loop and batch state |
| S2 | `serving/core/trace_generator.py` | source | content/formulas | high | perf DB lookup, tensor sizes, communication fields |
| S3 | `serving/core/memory_model.py`, `kv_cache_manager.py` | source | content/formulas | high | KV capacity, block hierarchy, traffic |
| S4 | `serving/core/config_builder.py` | source | structure/parameters | high | topology dimensions and network inputs |
| S5 | `astra-sim/extern/memory_backend/analytical/AnalyticalMemory.cc` | source | content/formulas | high | analytical memory runtime and queueing |
| S6 | `astra-sim/extern/network_backend/analytical/...` | source | content/formulas | high | link delay and serialization |
| S7 | `astra-sim/astra-sim/workload/Workload.cc` and Chakra converter | source | structure | high | ET node semantics and backend dispatch |
| S8 | bundled top-conference references | style reference | style | medium | flat vector, muted palette, explicit arrows |

## Requirement Traceability
| id | requirement | source evidence | must/should/may | planned visual encoding |
|---|---|---|---|---|
| R1 | bottom mechanism | S1, S7 | must | left-to-right + feedback loop diagram |
| R2 | compute formula | S2 | must | blue formula panel and dedicated slides |
| R3 | memory formula | S3, S5 | must | teal panel, capacity and access slides |
| R4 | communication formula | S2, S4, S6 | must | orange panel, topology and collective slides |
| R5 | end-to-end aggregation | S7, S1 | must | DAG critical-path equation |
| R6 | SEU slide output | SEU skill assets | must | local SimplePlus theme, XeLaTeX |

## Semantic Model
| id | entity or relationship | direction / hierarchy / cardinality | visual encoding | uncertainty |
|---|---|---|---|---|
| E1 | router to scheduler | control/data, one stream into per-instance queues | green arrow | verified |
| E2 | scheduler to batch | state snapshot | green arrow | verified |
| E3 | batch to trace generator | shape and KV state | blue arrow | verified |
| E4 | trace to Chakra | row fields to ET DAG | blue arrow | verified |
| E5 | Chakra to ASTRA-Sim | workload graph | orange arrow | verified |
| E6 | analytical backends to global clock | completion events | orange arrow | verified |
| E7 | completion to scheduler | feedback/update | dashed dark arrow | verified |
| E8 | compute/memory/communication to DAG | node-specific durations | color-coded arrows | verified |

## Style Contract
| id | font | palette | stroke | icon style | layout density | reference source |
|---|---|---|---|---|---|---|
| C1 | Noto Sans CJK SC | white background + pale blue/teal/orange/gray fills | 2px boxes, 3px arrows | no decorative icons; semantic labeled blocks | dense but regular 10px grid | top-conference fallback |
| C2 | Noto Sans CJK SC | blue=compute, teal=memory, orange=network, green=control | dashed feedback/config boundaries | flat 2D vector | wide landscape, generous gaps | top-conference fallback |
| C3 | SimplePlus Beamer | SEU local theme | no overlays | SVG/PNG vector-like exported figures | one substantive element per slide | `seu-academic-beamer` |

## Open Assumptions
| assumption | risk | how to verify |
|---|---|---|
| ASTRA-Sim's configured collective implementation is ring in the default generated system config | formula could differ for alternate collective config | label ring formula as default/approximation and cite `system.json`; explain general backend path |
| `mem-bw` numeric convention in AnalyticalMemory is used as B/ns after direct division | confusing GB/s vs B/ns | explicitly distinguish memory backend convention from network conversion |
| no full ASTRA-Sim binary run in this checkout | runtime behavior not end-to-end tested | state static source verification and run drawio/LaTeX validation |
