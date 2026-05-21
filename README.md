# ux-microsim-replication 🧪

[![License: MIT](https://img.shields.io/badge/Code%20License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Paper: Preprint](https://img.shields.io/badge/Paper-Preprint-blue)](https://github.com/alemaiorano/ux-microsim-replication)

> **Artifact-first proxy validation for LLM UX micro-simulations.**

This repository provides the artifacts and scripts needed to independently verify every reported result. It serves as the **public replication repository** for the research paper:

**"Proxy-Validated LLM UX Micro-Simulations: An Artifact-First Protocol for Early-Stage Decision Support"**.

---

## 🎯 Core Contributions

Early-stage teams lack the users and budget for repeated UX studies, yet still need decision-oriented signals. The paper studies an LLM-driven UX micro-simulation pipeline and validates it against public proxy corpora along three lines:

1. **UX micro-simulation pipeline**: structured, role-conditioned customer-experience feedback generated from versioned prompts, personas, journeys, and UI snapshots.
2. **Proxy-validation protocol**: two alignment metrics — top-k Jaccard and weighted-Jaccard (W) — comparing simulated friction themes against app reviews, support tweets, and open-source issues.
3. **Artifact-first evaluation**: bootstrap confidence intervals, a four-strategy agent ablation, and a grounding/fabrication failure-mode analysis, all regenerated from versioned run artifacts.

---

## 🚀 Quick Start

Every table and figure in the paper regenerates from the versioned artifacts in `reports/ux/`. No API keys or paid models are required.

### Prerequisites
- A LaTeX distribution with `pdflatex` and `bibtex` (TeX Live or MiKTeX)
- Python >= 3.11

### Rebuild the paper
```bash
git clone https://github.com/alemaiorano/ux-microsim-replication.git
cd ux-microsim-replication
pip install -r requirements-paper-ux.txt

# re-derive the paper tables and figures from the result artifacts
python scripts/export_paper_ux_tables.py
python scripts/export_paper_ux_figures.py

# compile the paper PDF
pdflatex -interaction=nonstopmode -output-directory paper_ux paper_ux/main.tex
bibtex   paper_ux/main
pdflatex -interaction=nonstopmode -output-directory paper_ux paper_ux/main.tex
pdflatex -interaction=nonstopmode -output-directory paper_ux paper_ux/main.tex
```

Output: `paper_ux/main.pdf`. See `SCOPE.md` for exactly what is and is not included in this package.

---

## 📊 Empirical Evidence

The package reproduces the paper's headline results, mapping each hypothesis to artifact-backed evidence:

| Finding | Result |
| :--- | :--- |
| **Embedding alignment beats lexical (H1)** | W = 0.128 vs 0.000 (Gojek); 0.119 vs 0.009 (Amazon) |
| **Top-k Jaccard overstates alignment (H2)** | J_k rises 0.33 → 1.0 at k=10 while W stays flat at 0.017 |
| **Embedding W unstable under resampling (H3)** | bootstrap W collapses to 0 across all three proxies |
| **Best agent strategy** | `gpt-4.1` hybrid — quality 0.707 (HQ) / 0.726 (CQ) |

---

## 🔬 Research & Replication

This repository is a **verification-grade** artifact package:

- **`paper_ux/`**: LaTeX manuscript sources with auto-generated tables and figures.
- **`scripts/`**: export and build scripts that turn artifacts into paper assets.
- **`reports/ux/`**: versioned result artifacts (alignment, bootstrap, agent ablation, evaluation).
- **`SCOPE.md`**: artifact scope — what is included, what is excluded, and why.
- **`CLAIMS_TO_ARTIFACTS.csv`**: claim-by-claim map from the paper to the backing artifact files.
- **`DATA_SOURCES.md`**: retrieval pointers for the public proxy datasets.

The proprietary simulation engine and its prompt and configuration files are not redistributed; the paper text and its appendix excerpts are the public specification of the method (see `SCOPE.md`).

### Basic reproduction command
```bash
python scripts/export_paper_ux_tables.py && python scripts/export_paper_ux_figures.py
```

---

## 📄 Citation

If you use this protocol or the proxy-validation methodology, please cite our work:

```text
Maiorano, A. C. (2026). Proxy-Validated LLM UX Micro-Simulations: An Artifact-First
Protocol for Early-Stage Decision Support. Preprint.
```

## 📄 License

- Code and documentation: MIT License (see `LICENSE`).
- The proxy datasets are third-party and retain their original licenses; they are not redistributed here — see `DATA_SOURCES.md`.
