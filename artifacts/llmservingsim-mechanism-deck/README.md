# LLMServingSim Mechanism Deck

A source-grounded Chinese academic slide deck for LLMServingSim 2.0.

## Deliverables

- `main.pdf`: compiled 16:9 SEU SimplePlus Beamer deck, 31 pages including backup slides.
- `main.tex`: XeLaTeX source.
- `diagrams/system-mechanism.drawio`: editable closed-loop simulator mechanism diagram.
- `diagrams/latency-model.drawio`: editable compute/memory/communication model diagram.
- `figures/*.svg`: matching vector exports generated from the same layout model.
- `figures/*.png`: 1600×900 slide-ready renders.
- `source-evidence.md`: source citation and formula evidence ledger.
- `diagram-brief.md`: semantic and visual design contract.
- `review/defect-log.md`: three review cycles, red-team audit, and self-score.
- `review/slides-contact-sheet.png`: all pages rendered for visual review.

## Assumed Talk

- Duration: approximately 25–30 minutes plus Q&A.
- Audience: graduate students and systems/architecture researchers familiar with LLM inference.
- Language: Chinese, with source identifiers and standard systems terms in English.

## Build

```bash
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex
```

Regenerate diagrams before rebuilding the deck when diagram content changes:

```bash
python3 generate_diagrams.py
```

The checked-in PNGs are browser renders of the generated SVG files. The `.drawio` files remain the editable handoff artifacts.

## Verification Summary

- Analyzed revision: `725ef79d6961` (`main`).
- Draw.io visual preflight: passed, zero FAILs.
- Draw.io strict structure validation: passed for both diagrams.
- XeLaTeX: passed twice, zero errors, undefined references, or overfull boxes.
- PDF: 31 pages, 16:9, all extractable text blocks within page bounds.
- Full simulator baseline and GPU profiler runs were not executed because this task changes documentation artifacts only and GPU profiling requires the vLLM/NVIDIA environment.
