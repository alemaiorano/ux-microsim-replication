# Artifact Scope — Proxy-Validated LLM UX Micro-Simulations

Replication package for the paper *"Proxy-Validated LLM UX Micro-Simulations:
An Artifact-First Protocol for Early-Stage Decision Support."*

This package is **verification-grade**: every table, figure and number in the
paper can be regenerated and checked from the artifacts and scripts included
here. It deliberately **does not** ship the simulation method's reusable
components (prompts, personas, journeys, taxonomy configs) or the simulation
engine, because those overlap with a commercial product built on the same
method. The paper itself — including the appendix prompt excerpts — is the
public specification of the method.

## Reproducibility tier

- Every reported number, table and figure regenerates from the shipped result
  artifacts via the included export/build scripts.
- The method is documented by the paper (text + appendix excerpts).
- The simulation engine and its reusable inputs (prompts, personas, journeys,
  UI snapshots, product context, taxonomy files) are **not** included.

## IP boundary

The UX micro-simulation method underpins a commercial product. To avoid
exposing product IP, the boundary is:

- **Public / verifiable:** the paper, the result artifacts (aggregated numbers),
  and the scripts that turn artifacts into paper tables/figures. → included.
- **Method-as-product:** the simulation prompts, persona/journey/task
  definitions, UI snapshots, product context, taxonomy configuration files, and
  the simulation engine itself. → excluded.

## Included

| Path | Contents | Why it is safe |
|---|---|---|
| `paper_ux/` | LaTeX sources, sections, auto-generated tables/figures, `references.bib` | The paper itself; public on publication |
| `tex/preamble.tex` | Shared LaTeX preamble | Formatting only |
| `reports/ux/` | Aggregated result artifacts: alignment tables, bootstrap CIs, proxy-validation summaries, agent-ablation summaries, fabrication examples, annotation eval outputs (CSV/JSON/MD) | Result numbers, not method; back the paper's claims |
| `scripts/` | `export_paper_ux_tables.py`, `export_paper_ux_figures.py`, `build_paper_ux.ps1` | Paper-asset generation only; transforms artifacts into tables/figures |
| root | `LICENSE` (MIT), `requirements-paper-ux.txt`, `README.md`, `SCOPE.md`, `DATA_SOURCES.md`, `CLAIMS_TO_ARTIFACTS.csv` | Documentation and metadata |

## Excluded — method-as-product (protects IP)

| Item | Reason |
|---|---|
| `configs/prompts/ux_*.md` | Simulation, judge and annotation prompt templates — core method of the product. The paper appendix publishes the intended excerpts; full templates are not redistributed. |
| `configs/ux/personas, journeys, tasks, ui_snapshot, product_context` | Persona/journey simulation inputs — the product's method content. |
| `configs/ux/friction_taxonomy, appstore_taxonomy, locales, oss_repos` | Taxonomy/config files. The taxonomies are already published in the paper (Tables 13 and 15); the JSON files are not redistributed, keeping a single simple rule (no method configs in the package). |
| `scripts/ux_simulation_pipeline.py` | Core simulation engine — proprietary. |
| `scripts/ux_proxy_validation*.py`, `ux_alignment_bootstrap.py`, `ux_*_eval.py`, `ux_*_summary.py` | Metric/evaluation scripts. Excluded to keep the package purely verification-grade and avoid fine-grained coupling judgments; the metrics are fully specified in the paper. |
| `scripts/run_ux_*.ps1`, `run_azure_*.ps1`, `pipeline/`, `apps/`, `evals/` | Run orchestration and the broader LLM-readiness harness. |

## Excluded — secrets / bulk / not redistributable

| Item | Reason |
|---|---|
| `.env` | API keys / secrets. |
| `data/raw/`, raw proxy corpora | Third-party licensed datasets — see `DATA_SOURCES.md`. |
| `reports/ux/runs/`, logs, debug, tmp | Per-run raw outputs; bulky and not needed for verification. |

## Consequence for re-derivation

- The PDF rebuilds fully from the shipped sources (`build_paper_ux.ps1 -SkipAssets`).
- `export_paper_ux_tables.py` and `export_paper_ux_figures.py` regenerate every
  table and figure from `reports/ux/`, **except** two that ship pre-generated:
  the friction-taxonomy table (needs the taxonomy config, not shipped — its
  content is in the paper as Table 15) and the agent-output examples table
  (needs per-run outputs, not shipped).

## Data sources (not redistributed)

The proxy corpora are public third-party datasets and are not redistributed
here; see `DATA_SOURCES.md` for each source and retrieval instructions.

## Structure

```
ux-microsim-replication/
├── README.md
├── SCOPE.md                 (this file)
├── LICENSE
├── DATA_SOURCES.md
├── CLAIMS_TO_ARTIFACTS.csv
├── requirements-paper-ux.txt
├── paper_ux/                paper sources + auto-generated tables/figures
├── tex/preamble.tex
├── scripts/                 export + build scripts
└── reports/ux/              result artifacts
```
