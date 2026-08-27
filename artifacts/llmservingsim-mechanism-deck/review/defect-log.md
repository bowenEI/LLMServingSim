# Diagram Defect Log

The diagrams are generated from `generate_diagrams.py`; each PNG is a canvas-only 1600×900 render of the matching SVG layout. The `.drawio` files use the same semantic model and 10px geometry grid. The diagrams.net iframe returned a uniform loading surface in this environment, so those invalid screenshots are retained as `*-cycle1-full.png` but were not counted as review evidence.

## Screenshot Review Cycle 1

Evidence: `system-cycle1.png`, `latency-cycle1.png`.

### Inventory

| id | zone | element | finding | severity | resolution |
|---|---|---|---|---|---|
| C1-01 | text | all body labels | 13–14px body text became too small when embedded in a Beamer content frame | P1 | raised default body to 18px and moved overview diagrams to full-slide frames |
| C1-02 | text | edge labels | 12px edge labels were weak at projector scale | P1 | raised to 14px and widened white label backplates |
| C1-03 | arrows | `e16` | completion feedback used a default center route through `backend` | P0 | added explicit bottom route points |
| C1-04 | arrows | `e17` | state feedback crossed `memory` on its path back to scheduler | P0 | routed left of the memory row |
| C1-05 | arrows | latency shape fanout | default center paths crossed the middle model panel | P0 | added explicit vertical routes per column |
| C1-06 | boxes | `loop` | long feedback sentence was cramped | P1 | shortened the sentence and raised title size |
| C1-07 | boxes | compute/memory/comm | 300px panels looked hollow around small text | P1 | reduced panel height and increased typography |
| C1-08 | spacing | latency lower half | sparse composition between model panels and DAG | P1 | added semantically meaningful Chakra node-type boxes |
| C1-09 | color | all panels | colors were coherent but body hierarchy relied mostly on fill | P2 | increased heading/body contrast through font size and weight |
| C1-10 | typography | formula panels | title and formula text were too close in scale | P1 | 24px panel headings, 18px bodies |
| C1-11 | layout | Beamer overview page | title bar duplicated the diagram's own title | P1 | changed to `frame[plain]` full-page image |
| C1-12 | icons | whole diagram | no icons were used | accepted | deliberate: all elements are technical entities; no decorative icon needed |
| C1-13 | semantics | latency DAG | node types were only implied by edge labels | P1 | added COMP/MEM/COMM node-type boxes |
| C1-14 | semantics | global time | an early slide draft described total time as an iteration sum | P0 | corrected to the latest absolute sink completion time |
| C1-15 | formulas | MoE AG | an early slide draft used ceil(T/EP), unlike source floor division | P0 | corrected to `max(1,floor(T/EP))` |
| C1-16 | style | system graph | 17 edges created a dense lower-right area | P1 | separated ET DAG, analytical backends, and metrics vertically |
| C1-17 | spacing | system lower row | metrics sat on the same static row with a large apparent gap | P2 | moved metrics upward to its own band |
| C1-18 | boxes | `chakra` | preflight estimated vertical text overflow at larger font | P1 | raised box height to 120px |
| C1-19 | boxes | `kv` | preflight estimated vertical text overflow at larger font | P1 | raised box height to 150px |
| C1-20 | arrows | SVG explicit routes | explicit waypoint routes began at source centers in the SVG export | P0 | added boundary intersection calculation for explicit routes |
| C1-21 | typography | diagram title | title hierarchy was acceptable but subtitle too small | P2 | kept subtitle concise and used full-slide scaling |
| C1-22 | composition | system top band | profiler/perf DB read as a separate offline path, but relation to config was weak | P2 | retained dashed config→profiler link and explicit `time_us` link |
| C1-23 | composition | system feedback | loop appeared detached from `metrics` | P1 | added labeled completion notification edge |
| C1-24 | arrow labels | several short edges | 110px white backplate could clip mixed CJK/English labels | P1 | widened to 130px |
| C1-25 | typography | node type pills | two-line 50px pills risked clipping | P1 | converted each to one-line labels |
| C1-26 | layout | latency model | edges to DAG passed through the new node-type pills | P0 | changed semantics to panel→node type→DAG |
| C1-27 | spacing | system main flow | middle row has variable box widths | P2 | accepted: widths encode responsibility/content density |
| C1-28 | color | feedback loop | dark feedback path could be confused with data flow | P1 | dashed the feedback/control loop |
| C1-29 | style coherence | both diagrams | initial deck figures were scaled below paper-figure readability | P1 | full-canvas, full-slide presentation |
| C1-30 | requirement | PIM | PIM latency was absent from the slide sequence | P1 | added a dedicated PIM formula slide |

### Fix Verification

All P0/P1 entries above were fixed in the generator or `main.tex`. Static preflight subsequently reported zero FAILs for both diagrams.

## Screenshot Review Cycle 2

Evidence: `system-cycle2.png`, `latency-cycle2.png`.

| id | zone | finding | severity | status |
|---|---|---|---|---|
| C2-01 | boxes | Chakra box still needed more vertical room at 22px heading | P1 | fixed: 120px height |
| C2-02 | boxes | Tiered KV box still needed more vertical room | P1 | fixed: 150px height |
| C2-03 | arrows | latency node-type pills collided with direct-to-DAG paths | P0 | fixed: split each relation into two edges |
| C2-04 | typography | panel title 20px in a 240px box triggered cavernous warning | P1 | fixed: 24px title, 18px body |
| C2-05 | typography | node-type pills were still two-line labels | P1 | fixed: single-line combined labels |
| C2-06 | spacing | system `memory`, `dag`, `metrics` static row looked uneven | P1 | fixed: metrics moved upward |
| C2-07 | arrows | completion edge approached metrics from below after move | P2 | verified clear in final route |
| C2-08 | text | loop sentence remained the longest system label | P2 | fixed: shortened wording |
| C2-09 | formula | memory and network GB/s conventions could be conflated | P1 | fixed: dedicated unit warning on memory slide |
| C2-10 | formula | ring approximation could be read as exact ASTRA-Sim runtime | P1 | fixed: explicitly labeled approximation; event phases described |
| C2-11 | layout | full-page figures intentionally omit SEU logo | accepted | plain overview pages; branded title/content slides retain logo |
| C2-12 | style | three semantic colors plus control green stay within palette contract | accepted | no change |
| C2-13 | icons | no icon inconsistency | verified | no change |
| C2-14 | arrows | all connector directions agree with the semantic brief | verified | no change |
| C2-15 | text | all panel text remains inside fixed boxes | verified | preflight zero text overflow FAILs |

## Screenshot Review Cycle 3

Evidence: `system-cycle3.png`, `latency-cycle3.png`; final copies: `system-final.png`, `latency-final.png`.

| id | zone | finding | severity | status |
|---|---|---|---|---|
| C3-01 | spacing | one system-row spacing WARN remained after resize | P1 | fixed by moving metrics to a separate band |
| C3-02 | arrows | SVG explicit paths needed box-boundary attachment | P0 | fixed with `boundary_point` |
| C3-03 | text | edge labels were readable but smaller than panel body | P2 | raised to 14px |
| C3-04 | boxes | edge label backplates were narrow for Chinese | P1 | widened to 130×25px |
| C3-05 | typography | overview slide source footers were redundant with diagram title | P2 | removed by using plain full-slide figures; evidence retained in later slides |
| C3-06 | layout | Beamer frame title duplicated diagram title | P1 | removed via plain frame |
| C3-07 | layout | PDF overview page text is rasterized and not text-extractable | accepted | 1600×900 source, validated nonblank and full-canvas; editable draw.io and SVG also supplied |
| C3-08 | formula | global time equation needed asynchronous absolute-time semantics | P0 | fixed to max sink completion |

Fix verification: final preflight has zero FAILs, strict draw.io validation passes, PDF element-boundary audit reports no out-of-page text.

## Red-Team Audit

Hostile review of final full-canvas screenshots and the 31-page PDF contact sheet:

| id | zone | finding | action |
|---|---|---|---|
| RT-01 | text | overview images are raster in PDF | accepted: 1600×900, full-slide, SVG and draw.io sources included |
| RT-02 | text | source citations are small supporting text | raised from tiny to scriptsize |
| RT-03 | arrows | draw.io automatic edge routing and SVG routing can differ | generator validates draw.io; SVG has explicit boundary routing |
| RT-04 | arrows | dense system graph has 17 edges | retained because every edge maps to a verified relationship |
| RT-05 | boxes | mixed box widths reduce strict grid rhythm | retained: width encodes content/responsibility |
| RT-06 | spacing | top profiler path and runtime path are vertically separated | retained: offline vs online separation is semantic |
| RT-07 | color | green represents control/output while gray is neutral | legend is implicit but consistent across both figures |
| RT-08 | typography | English code identifiers may be wider than CJK | boxes were preflighted and screenshot-rendered at final size |
| RT-09 | layout | two full-slide figures omit branded chrome | retained to maximize mechanism readability |
| RT-10 | icons | no icons reduce visual variety | retained: formulas and technical blocks are the substantive visual language |
| RT-11 | style | no shadows/gradients makes the figures restrained | accepted, matches academic style contract |
| RT-12 | formula | ring equation is an approximation | explicitly marked and separated from exact event model |
| RT-13 | formula | memory `mem-bw` convention differs from network conversion | called out explicitly on slide 16 |
| RT-14 | formula | PIM coefficients are empirical device baselines | slide labels coefficients as device-specific fits |
| RT-15 | PDF | page 10 has no extractable text | verified as nonblank full-slide PNG with 10,412 colors and 62.5% white fraction |

## Self-Score

| dimension | score | evidence |
|---|---:|---|
| Text readability | 9/10 | 18–24px diagram text; full-slide overview; supporting source text is scriptsize |
| Arrow accuracy | 9/10 | zero collision FAILs; explicit semantic labels and dimension/control distinctions |
| Color coherence | 9/10 | compute blue, memory teal, communication orange, control green, neutral gray |
| Layout consistency | 9/10 | 10px grid; strict validator passes; full-canvas content bounds verified |
| Style match | 9/10 | restrained flat vector, functional color, no decorative assets |
| **Total** | **45/50** | allowed for handoff |

## Remaining Gaps

- The diagrams.net iframe did not render in this headless environment; canvas review used the matching SVG/PNG generated from the same coordinate model. The `.drawio` files were independently preflighted and strictly validated.
- The overview figures are rasterized in the PDF for reliable XeLaTeX compilation. Editable `.drawio` and vector `.svg` sources are included.
