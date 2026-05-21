# UX paper (`paper_ux/`)

This folder contains the standalone paper draft for the **UX micro-simulation + proxy validation** track.

## Title
**Proxy-Validated LLM UX Micro-Simulations: An Artifact-First Protocol for Early-Stage Decision Support**

## Status (2026-02-21)
**Revision complete** — All critical improvements and consistency fixes implemented:
- ✅ Hypotheses H1-H3 explicitly mapped to results in Section 6
- ✅ Abstract rewritten with specific numerical findings (W=0.128 vs 0.000 on Gojek)
- ✅ Conclusion expanded with structured findings summary and future work
- ✅ Stop list issue documented in Section 7 (Grounding heuristic calibration)
- ✅ Words check scope clarified in Section 5 (validation vs quality scoring)
- ✅ Fabrication examples table completed (2 fabricated + 2 non-fabricated)
- ✅ Related Work positioning paragraph added
- ✅ Pipeline default `--candidate-n` aligned to paper (2 instead of 3)
- ✅ Distribution figure caption explains all-zeros as lexical method diagnostic

## Key Findings
- **H1 (supported):** Embedding-based alignment (BGE-M3) yields higher weighted-Jaccard (W) than lexical baselines on app-review and support-tweet proxies (e.g., Gojek: W=0.128 vs 0.000 lexical)
- **H2 (supported):** Top-k Jaccard saturates at large k (J_k=1.0 at k=10) while W remains low (0.017), confirming J_k overstates alignment
- **H3 (partially supported):** Bootstrap CIs are tight for lexical baseline on Amazon low-rated proxy (W: [0.010, 0.011]), but broader evidence across methods is left for future work
- **Agent ablation:** gpt-4.1 with hybrid strategy and LLM judge achieved highest quality (HQ: 0.707; CQ: 0.753 with auto-selection)

## Build

From the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_paper_ux.ps1
```

This will:
- Export paper tables/figures from `reports/ux/*`
- Compile `paper_ux/main.tex` with `pdflatex` + `bibtex`

Outputs are written into `paper_ux/` (including `paper_ux/main.pdf`).

## Reproducibility
All results are artifact-first:
- Versioned prompts: `configs/prompts/ux_simulation_v2.md`
- Agent strategies: `single_pass`, `write_then_score` (Best-of-N), `hybrid`, `anchoring_aware`
- Alignment methods: lexical, TF-IDF, embedding (BGE-M3)
- Export scripts: `scripts/export_paper_ux_tables.py`, `scripts/export_paper_ux_figures.py`
- UX pipeline: `scripts/ux_simulation_pipeline.py`

## Documentation
- Paper plan: `docs/28-ux-simulation-paper-plan.md`
- Paper outline: `docs/30-ux-simulation-paper-outline.md`
- Pipeline guide: `docs/25-llm-simulation-pipeline.md`

