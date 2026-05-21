from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in {"n/a", "none", "-"}:
        return None
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _maybe_import_matplotlib() -> tuple[Any, Any] | tuple[None, None]:
    try:
        import matplotlib.pyplot as plt  # type: ignore[import-not-found]

        return plt, plt  # keep signature stable; we only need plt
    except Exception:
        return None, None


def _canonical_key(dataset: str) -> str:
    for suffix in ("_embed_t025", "_embed_t045", "_embed", "_tfidf_t005", "_tfidf_t020", "_tfidf", "_lex_k6", "_lex_k10"):
        if dataset.endswith(suffix):
            return dataset[: -len(suffix)]
    return dataset


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def _apply_stopwords(text: str, stopwords: list[str]) -> str:
    cleaned = _normalize_text(text)
    for word in stopwords:
        cleaned = re.sub(rf"\\b{re.escape(word)}\\b", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _prepare_keyword_matchers(
    taxonomy: dict[str, list[str]],
) -> dict[str, tuple[list[str], list[re.Pattern[str]]]]:
    matchers: dict[str, tuple[list[str], list[re.Pattern[str]]]] = {}
    for category, keywords in taxonomy.items():
        token_keywords: list[str] = []
        phrase_patterns: list[re.Pattern[str]] = []
        for keyword in keywords:
            keyword = str(keyword).lower().strip()
            if not keyword:
                continue
            if " " in keyword:
                parts = [re.escape(part) for part in keyword.split()]
                pattern = r"\\b" + r"\\s+".join(parts) + r"\\b"
                phrase_patterns.append(re.compile(pattern))
            else:
                token_keywords.append(keyword)
        matchers[category] = (token_keywords, phrase_patterns)
    return matchers


def _tokenize_normalized(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", text)


def _count_frictions_lexical(
    texts: list[str],
    taxonomy: dict[str, list[str]],
    weights: dict[str, float],
    stopwords: list[str],
) -> dict[str, float]:
    counts = {key: 0.0 for key in taxonomy}
    matchers = _prepare_keyword_matchers(taxonomy)
    for text in texts:
        cleaned = _apply_stopwords(text, stopwords)
        if not cleaned:
            continue
        tokens = set(_tokenize_normalized(cleaned))
        for category, (token_keywords, phrase_patterns) in matchers.items():
            matched = any(token in tokens for token in token_keywords)
            if not matched and phrase_patterns:
                matched = any(pattern.search(cleaned) for pattern in phrase_patterns)
            if matched:
                counts[category] += weights.get(category, 1.0)
    return counts


def _load_taxonomy(
    path: Path,
    domain: str,
) -> tuple[dict[str, list[str]], dict[str, float], list[str]]:
    payload = _read_json(path)
    categories = payload.get("categories", {})
    if not isinstance(categories, dict):
        categories = {}
    default_weights = payload.get("default_weights", {})
    domain_weights = payload.get("domain_weights", {})
    domain_stopwords = payload.get("domain_stopwords", {})

    if not isinstance(default_weights, dict):
        default_weights = {}
    if not isinstance(domain_weights, dict):
        domain_weights = {}
    if not isinstance(domain_stopwords, dict):
        domain_stopwords = {}

    domain_override = domain_weights.get(domain, {})
    if not isinstance(domain_override, dict):
        domain_override = {}
    stopwords = domain_stopwords.get(domain, [])
    if not isinstance(stopwords, list):
        stopwords = []

    cleaned: dict[str, list[str]] = {}
    weights: dict[str, float] = {}
    for key, values in categories.items():
        if not isinstance(values, list):
            continue
        cleaned[key] = [str(item).lower().strip() for item in values if str(item).strip()]
        weight = float(default_weights.get(key, 1.0))
        if key in domain_override:
            weight = float(domain_override[key])
        weights[key] = weight
    stopwords_clean = [str(item).lower().strip() for item in stopwords if str(item).strip()]
    return cleaned, weights, stopwords_clean


def _load_simulated_frictions(path: Path) -> list[str]:
    frictions: list[str] = []
    if not path.exists():
        return frictions
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            for item in record.get("friction_points", []):
                text = str(item).strip()
                if text:
                    frictions.append(text)
            for step in record.get("walkthrough", []):
                text = str(step.get("friction", "")).strip()
                if text:
                    frictions.append(text)
    return frictions


def _read_friction_counts_csv(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    rows = _read_csv(path)
    out: dict[str, float] = {}
    for row in rows:
        key = (row.get("category") or "").strip()
        value = _to_float(row.get("count"))
        if key and value is not None:
            out[key] = float(value)
    return out


def _normalize_distribution(counts: dict[str, float]) -> dict[str, float]:
    total = sum(float(value) for value in counts.values() if value)
    if total <= 0:
        return {key: 0.0 for key in counts}
    return {key: float(value) / total for key, value in counts.items()}


def _select_top_categories(
    left: dict[str, float],
    right: dict[str, float],
    limit: int,
) -> list[str]:
    scored: dict[str, float] = {}
    for key, value in left.items():
        scored[key] = max(scored.get(key, 0.0), float(value))
    for key, value in right.items():
        scored[key] = max(scored.get(key, 0.0), float(value))
    ordered = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))
    return [key for key, _ in ordered[:limit]]


def _write_distribution_example(
    paper_fig_dir: Path,
    taxonomy_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sim_path = repo_root / "reports" / "ux" / "simulations.jsonl"
    proxy_counts_path = (
        repo_root
        / "reports"
        / "ux"
        / "proxy_validation_amazon_low_rated_annotated"
        / "friction_counts.csv"
    )
    if not sim_path.exists() or not proxy_counts_path.exists():
        return

    taxonomy, weights, stopwords = _load_taxonomy(taxonomy_path, domain="app_reviews")
    simulated_frictions = _load_simulated_frictions(sim_path)
    sim_counts = _count_frictions_lexical(simulated_frictions, taxonomy, weights, stopwords)
    proxy_counts = _read_friction_counts_csv(proxy_counts_path)

    sim_dist = _normalize_distribution(sim_counts)
    proxy_dist = _normalize_distribution({key: proxy_counts.get(key, 0.0) for key in taxonomy})

    categories = _select_top_categories(sim_dist, proxy_dist, limit=8)
    if not categories:
        return

    ymax = max([sim_dist.get(cat, 0.0) for cat in categories] + [proxy_dist.get(cat, 0.0) for cat in categories])
    ymax = max(0.15, ymax * 1.2) if ymax > 0 else 0.15
    ymax = round(ymax + 1e-9, 2)

    coords_sim = " ".join(f"({cat},{sim_dist.get(cat, 0.0):.4f})" for cat in categories)
    coords_proxy = " ".join(f"({cat},{proxy_dist.get(cat, 0.0):.4f})" for cat in categories)
    xcoords = ",".join(categories)
    xticklabels = ",".join(cat.replace("_", " ") for cat in categories)

    lines = [
        r"\begin{tikzpicture}",
        r"\begin{axis}[",
        r"ybar,",
        r"bar width=7pt,",
        r"width=0.98\linewidth,",
        r"height=0.42\linewidth,",
        r"ylabel={Proportion of friction mass},",
        rf"symbolic x coords={{{xcoords}}},",
        r"xtick=data,",
        rf"xticklabels={{{xticklabels}}},",
        r"xticklabel style={font=\scriptsize, rotate=25, anchor=east},",
        r"tick label style={font=\small},",
        r"label style={font=\small},",
        r"ymin=0,",
        rf"ymax={ymax},",
        r"grid=major,",
        r"legend style={font=\small, at={(0.02,0.98)}, anchor=north west},",
        r"]",
        rf"\addplot[fill=teal!55, draw=teal!80] coordinates {{{coords_sim}}};",
        r"\addlegendentry{Simulations (lexical map)}",
        rf"\addplot[fill=gray!35, draw=gray!60] coordinates {{{coords_proxy}}};",
        r"\addlegendentry{Proxy (Amazon ann.; lexical map)}",
        r"\end{axis}",
        r"\end{tikzpicture}",
    ]
    (paper_fig_dir / "distribution_amazon_ann.tex").write_text("\n".join(lines) + "\n", encoding="ascii")


def _write_bootstrap_ci_plot(paper_fig_dir: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    payload = _read_json(repo_root / "reports" / "ux" / "alignment_bootstrap.json")
    if not payload:
        return
    mean = _to_float(payload.get("weighted_mean"))
    low = _to_float(payload.get("weighted_ci_low"))
    high = _to_float(payload.get("weighted_ci_high"))
    if mean is None or low is None or high is None:
        return

    lines = [
        r"\begin{tikzpicture}",
        r"\begin{axis}[",
        r"width=0.62\linewidth,",
        r"height=0.32\linewidth,",
        r"ylabel={Weighted-Jaccard ($W$)},",
        r"xtick=\empty,",
        r"xmin=-0.5, xmax=0.5,",
        r"grid=major,",
        r"tick label style={font=\small},",
        r"label style={font=\small},",
        r"]",
        rf"\addplot[black, thick] coordinates {{(0,{low:.5f}) (0,{high:.5f})}};",
        rf"\addplot[only marks, mark=*, mark size=1.8pt] coordinates {{(0,{mean:.5f})}};",
        r"\end{axis}",
        r"\end{tikzpicture}",
    ]
    (paper_fig_dir / "bootstrap_ci_plot.tex").write_text("\n".join(lines) + "\n", encoding="ascii")


def _write_alignment_plot_pdf(paper_fig_dir: Path, points: dict[str, dict[str, float]]) -> None:
    plt, _ = _maybe_import_matplotlib()
    if plt is None:
        return

    x_order = [
        "proxy_validation_tinder",
        "proxy_validation_gojek",
        "proxy_validation_twitter",
        "proxy_validation_amazon_low_rated",
        "proxy_validation_amazon_low_rated_annotated",
    ]
    xticklabels = ["Tinder", "Gojek", "Twitter", "Amazon", "Amazon (ann.)"]

    method_order = ["lexical", "tfidf", "embedding"]
    method_labels = {"lexical": "Lexical", "tfidf": "TF-IDF", "embedding": "Embedding"}
    method_colors = {"lexical": "#3b82f6", "tfidf": "#f59e0b", "embedding": "#14b8a6"}

    max_value = 0.0
    for dataset in points.values():
        for value in dataset.values():
            max_value = max(max_value, float(value))
    ymax = max(0.12, (max_value * 1.15) if max_value > 0 else 0.12)
    ymax = round(ymax + 1e-9, 2)

    fig, (ax, axins) = plt.subplots(
        1, 2, figsize=(9.0, 3.7), constrained_layout=True,
        gridspec_kw={"width_ratios": [3.0, 1.1]},
    )
    x = list(range(len(x_order)))
    width = 0.22
    offsets = {"lexical": -width, "tfidf": 0.0, "embedding": width}

    for method in method_order:
        xs: list[float] = []
        ys: list[float] = []
        for i, ds in enumerate(x_order):
            val = points.get(ds, {}).get(method)
            if val is None:
                continue
            xs.append(x[i] + offsets[method])
            ys.append(float(val))
        if not ys:
            continue
        ax.bar(
            xs,
            ys,
            width=width,
            label=method_labels.get(method, method),
            color=method_colors.get(method, "#999999"),
            edgecolor="black",
            linewidth=0.3,
        )

    ax.set_ylabel("Weighted-Jaccard (W)")
    ax.set_xticks(x, xticklabels)
    ax.set_ylim(0, ymax)
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.5)
    ax.legend(loc="upper left", frameon=True, fontsize=9)

    # Side panel: zoom on lexical/TF-IDF, which are invisible at the embedding scale.
    # A separate panel (rather than an overlay inset) avoids any overlap with the
    # tall embedding bars of the main plot.
    low_vals: list[float] = []
    for ds in x_order:
        for method in ("lexical", "tfidf"):
            val = points.get(ds, {}).get(method)
            if val is not None:
                low_vals.append(float(val))
    zoom_max = min(0.03, max(0.02, max(low_vals) * 1.4)) if low_vals else 0.03
    axins.set_title("Lexical/TF-IDF (zoom)", fontsize=8)
    axins.set_ylim(0, zoom_max)
    axins.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.5)
    for method in ("lexical", "tfidf"):
        xs: list[float] = []
        ys: list[float] = []
        for i, ds in enumerate(x_order):
            val = points.get(ds, {}).get(method)
            if val is None:
                continue
            xs.append(i + offsets[method])
            ys.append(float(val))
        if not ys:
            continue
        zoom_container = axins.bar(
            xs,
            ys,
            width=width,
            color=method_colors.get(method, "#999999"),
            edgecolor="black",
            linewidth=0.25,
            alpha=0.95,
        )
        try:
            labels = [f"{v:.3f}" if v >= 0.001 else f"{v:.4f}" for v in ys]
            axins.bar_label(zoom_container, labels=labels, fontsize=6, padding=1)
        except Exception:
            pass
    axins.set_xticks(x, xticklabels, rotation=40, ha="right", fontsize=7)

    out_pdf = paper_fig_dir / "alignment_plot.pdf"
    out_png = paper_fig_dir / "alignment_plot.png"
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _write_bootstrap_ci_plot_pdf(paper_fig_dir: Path) -> None:
    plt, _ = _maybe_import_matplotlib()
    if plt is None:
        return

    repo_root = Path(__file__).resolve().parents[1]
    payload = _read_json(repo_root / "reports" / "ux" / "alignment_bootstrap.json")
    if not payload:
        return
    mean = _to_float(payload.get("weighted_mean"))
    low = _to_float(payload.get("weighted_ci_low"))
    high = _to_float(payload.get("weighted_ci_high"))
    if mean is None or low is None or high is None:
        return

    # Single-row forest plot style (more informative than a floating interval).
    fig, ax = plt.subplots(figsize=(5.6, 2.1), constrained_layout=True)
    ax.errorbar(
        [mean],
        [0],
        xerr=[[mean - low], [high - mean]],
        fmt="o",
        color="black",
        elinewidth=1.6,
        capsize=6,
        markersize=5,
        zorder=3,
    )
    pad = max(0.0002, (high - low) * 0.35)
    ax.set_xlim(low - pad, high + pad)
    ax.set_ylim(-0.7, 0.7)
    ax.set_yticks([0], ["Overall"])
    ax.set_xlabel("Weighted-Jaccard (W)")
    ax.grid(axis="x", linestyle="--", linewidth=0.5, alpha=0.5)
    ax.text(
        0.01,
        0.92,
        f"mean={mean:.4f}  CI=[{low:.4f}, {high:.4f}]",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#374151",
    )

    out_pdf = paper_fig_dir / "bootstrap_ci_plot.pdf"
    out_png = paper_fig_dir / "bootstrap_ci_plot.png"
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _write_distribution_amazon_ann_pdf(paper_fig_dir: Path, taxonomy_path: Path) -> None:
    plt, _ = _maybe_import_matplotlib()
    if plt is None:
        return

    repo_root = Path(__file__).resolve().parents[1]
    sim_path = repo_root / "reports" / "ux" / "simulations.jsonl"
    proxy_counts_path = (
        repo_root
        / "reports"
        / "ux"
        / "proxy_validation_amazon_low_rated_annotated"
        / "friction_counts.csv"
    )
    if not sim_path.exists() or not proxy_counts_path.exists():
        return

    taxonomy, weights, stopwords = _load_taxonomy(taxonomy_path, domain="app_reviews")
    simulated_frictions = _load_simulated_frictions(sim_path)
    sim_counts = _count_frictions_lexical(simulated_frictions, taxonomy, weights, stopwords)
    proxy_counts = _read_friction_counts_csv(proxy_counts_path)

    sim_dist = _normalize_distribution(sim_counts)
    proxy_dist = _normalize_distribution({key: proxy_counts.get(key, 0.0) for key in taxonomy})
    categories = _select_top_categories(sim_dist, proxy_dist, limit=8)
    if not categories:
        return

    # Dumbbell chart: clearer differences even when one side is ~0.
    labels = [cat.replace("_", " ") for cat in categories]
    sim_vals = [float(sim_dist.get(cat, 0.0)) for cat in categories]
    proxy_vals = [float(proxy_dist.get(cat, 0.0)) for cat in categories]
    deltas = [sim_vals[i] - proxy_vals[i] for i in range(len(categories))]

    # Order by proxy prominence (paper's "reference" distribution), then by divergence magnitude.
    order = sorted(
        range(len(categories)),
        key=lambda i: (proxy_vals[i], abs(deltas[i])),
        reverse=True,
    )
    labels = [labels[i] for i in order]
    sim_vals = [sim_vals[i] for i in order]
    proxy_vals = [proxy_vals[i] for i in order]
    deltas = [deltas[i] for i in order]

    y = list(range(len(labels)))
    fig, ax = plt.subplots(figsize=(7.8, 3.6), constrained_layout=True)
    for yi, a, b, d in zip(y, sim_vals, proxy_vals, deltas):
        ax.hlines(yi, xmin=min(a, b), xmax=max(a, b), color="#d1d5db", linewidth=2.0, zorder=1)
        # Delta label at the midpoint avoids pushing beyond x-limits.
        mid = (a + b) / 2.0
        sign = "+" if d >= 0 else ""
        ax.text(
            mid,
            yi - 0.15,
            f"{sign}{d:.2f}",
            ha="center",
            va="center",
            fontsize=8,
            color="#374151",
            bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none", alpha=0.75),
            zorder=2,
        )
    ax.scatter(sim_vals, y, s=46, color="#14b8a6", edgecolor="black", linewidth=0.3, label="Simulations (lexical map)", zorder=3)
    ax.scatter(proxy_vals, y, s=46, color="#9ca3af", edgecolor="black", linewidth=0.3, label="Proxy (Amazon ann.; lexical map)", zorder=3)

    ax.set_xlabel("Proportion of friction mass")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    # Fixed axis keeps the paper comparable across regenerations/runs.
    ax.set_xlim(0, 0.45)
    ax.grid(axis="x", linestyle="--", linewidth=0.5, alpha=0.5)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=2,
        frameon=True,
        fontsize=9,
        borderaxespad=0.0,
    )

    out_pdf = paper_fig_dir / "distribution_amazon_ann.pdf"
    out_png = paper_fig_dir / "distribution_amazon_ann.png"
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _pareto_front(points: list[tuple[float, float]]) -> set[int]:
    # Maximize y (quality), minimize x (cost).
    keep: set[int] = set()
    for i, (x_i, y_i) in enumerate(points):
        dominated = False
        for j, (x_j, y_j) in enumerate(points):
            if i == j:
                continue
            if (x_j <= x_i and y_j >= y_i) and (x_j < x_i or y_j > y_i):
                dominated = True
                break
        if not dominated:
            keep.add(i)
    return keep


_FIG_RUN_TS_RE = re.compile(r"_(\d{8})_(\d{6})$")
_FIG_RUN_CANONICAL_RE = re.compile(r"(?P<label>v\d+_[A-Za-z0-9_]+?)_\d{8}_\d{6}$", flags=re.IGNORECASE)


def _read_agent_ablation_rows_deduped(reports_dir: Path, stem: str) -> list[dict[str, str]]:
    """Glob all `<stem>*.csv` summaries (main + per-model + reruns) and keep the latest
    run per (model, canonical condition label). Mirrors the logic in
    `export_paper_ux_tables.py` so the Pareto figure sees the same rows as the
    ablation tables.
    """
    best: dict[tuple[str, str], dict[str, str]] = {}
    best_ts: dict[tuple[str, str], tuple[str, str]] = {}
    for path in sorted(reports_dir.glob(f"{stem}*.csv")):
        if path.name.endswith(".bak.csv"):
            continue
        for row in _read_csv(path):
            run_id = (row.get("run_id") or "").strip()
            model = (row.get("model") or "").strip()
            if not run_id:
                continue
            m_canon = _FIG_RUN_CANONICAL_RE.search(run_id)
            label = m_canon.group("label") if m_canon else run_id
            key = (model, label)
            m_ts = _FIG_RUN_TS_RE.search(run_id)
            ts = (m_ts.group(1), m_ts.group(2)) if m_ts else ("", "")
            if key not in best or ts > best_ts[key]:
                best[key] = row
                best_ts[key] = ts
    return sorted(best.values(), key=lambda r: ((r.get("model") or ""), (r.get("run_id") or "")))


def _write_agent_ablation_pareto_pdf(paper_fig_dir: Path, reports_dir: Path) -> None:
    plt, _ = _maybe_import_matplotlib()
    if plt is None:
        return

    hq = _read_agent_ablation_rows_deduped(reports_dir, "agent_ablation_hallucination_quality_summary")
    cq = _read_agent_ablation_rows_deduped(reports_dir, "agent_ablation_cost_quality_summary")
    if not hq and not cq:
        return

    agent_style = {
        "single_pass": {"color": "#3b82f6", "label": "Single-pass"},
        "hybrid": {"color": "#14b8a6", "label": "Hybrid"},
        "write_then_score": {"color": "#f59e0b", "label": "Best-of-$N$"},
        "anchoring_aware": {"color": "#a855f7", "label": "Score-then-select"},
    }
    judge_marker = {"llm": "o", "auto": "s"}

    def plot_suite(ax, rows: list[dict[str, str]], title: str) -> None:
        if not rows:
            ax.set_title(title)
            ax.axis("off")
            return

        xs: list[float] = []
        ys: list[float] = []
        metas: list[tuple[str, str]] = []
        for row in rows:
            x = _to_float(row.get("cost_units_per_sim"))
            y = _to_float(row.get("quality_score"))
            if x is None or y is None:
                continue
            agent = str(row.get("agent", "") or "").strip()
            judge_mode = str(row.get("judge_mode", "llm") or "llm").strip().lower()
            xs.append(float(x))
            ys.append(float(y))
            metas.append((agent, judge_mode))

        if not xs:
            ax.set_title(title)
            ax.axis("off")
            return

        pareto_idx = _pareto_front(list(zip(xs, ys)))
        for i, (x, y) in enumerate(zip(xs, ys)):
            agent, judge_mode = metas[i]
            style = agent_style.get(agent, {"color": "#6b7280", "label": agent or "other"})
            marker = judge_marker.get(judge_mode, "o")
            ax.scatter(
                [x],
                [y],
                s=54 if i in pareto_idx else 44,
                marker=marker,
                color=style["color"],
                edgecolor="black" if i in pareto_idx else "#111827",
                linewidth=1.0 if i in pareto_idx else 0.3,
                alpha=0.95,
                zorder=3,
            )

        # Pareto curve (sorted by cost).
        pareto_points = sorted([(xs[i], ys[i]) for i in pareto_idx], key=lambda p: p[0])
        if len(pareto_points) >= 2:
            ax.plot([p[0] for p in pareto_points], [p[1] for p in pareto_points], color="#111827", linewidth=1.0, alpha=0.6)

        ax.set_title(title)
        ax.set_xlabel("Calls per simulation (cost proxy)")
        ax.grid(axis="both", linestyle="--", linewidth=0.5, alpha=0.5)

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.5), constrained_layout=True, sharey=True)
    plot_suite(axes[0], hq, "HQ (hallucination/quality)")
    plot_suite(axes[1], cq, "CQ (cost/quality)")
    axes[0].set_ylabel("Quality (composite proxy)")

    # Single combined legend below both panels: agent colours + judge-mode markers.
    # (N is fixed at 2 for all multi-candidate runs, so per-point N labels are omitted;
    # score-then-select selection is encoded by the Auto-judge marker, not a colour.)
    from matplotlib.lines import Line2D

    present_agents = {
        str(row.get("agent", "") or "").strip()
        for row in (hq + cq)
        if str(row.get("agent", "") or "").strip()
    }
    legend_handles = [
        Line2D([], [], marker="o", linestyle="", color=agent_style[a]["color"],
               markeredgecolor="black", markersize=7, label=agent_style[a]["label"])
        for a in ("single_pass", "hybrid", "write_then_score", "anchoring_aware")
        if a in present_agents and a in agent_style
    ] + [
        Line2D([], [], marker="o", linestyle="", color="#111827", markersize=7, label="Judge: LLM"),
        Line2D([], [], marker="s", linestyle="", color="#111827", markersize=7, label="Judge: Auto"),
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.0),
        ncol=6,
        fontsize=8,
        frameon=False,
    )

    out_pdf = paper_fig_dir / "agent_ablation_pareto.pdf"
    out_png = paper_fig_dir / "agent_ablation_pareto.png"
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    reports_dir = repo_root / "reports" / "ux"
    paper_fig_dir = repo_root / "paper_ux" / "figures"
    paper_fig_dir.mkdir(parents=True, exist_ok=True)

    rows = _read_csv(reports_dir / "alignment_table.csv")
    if not rows:
        return

    wanted = {
        ("proxy_validation_tinder", "lexical"): "proxy_validation_tinder",
        ("proxy_validation_tinder", "embedding"): "proxy_validation_tinder_embed",
        ("proxy_validation_gojek", "lexical"): "proxy_validation_gojek",
        ("proxy_validation_gojek", "embedding"): "proxy_validation_gojek_embed",
        ("proxy_validation_twitter", "lexical"): "proxy_validation_twitter",
        ("proxy_validation_twitter", "embedding"): "proxy_validation_twitter_embed",
        ("proxy_validation_amazon_low_rated", "lexical"): "proxy_validation_amazon_low_rated",
        ("proxy_validation_amazon_low_rated", "tfidf"): "proxy_validation_amazon_low_rated_tfidf",
        ("proxy_validation_amazon_low_rated", "embedding"): "proxy_validation_amazon_low_rated_embed",
        ("proxy_validation_amazon_low_rated_annotated", "lexical"): "proxy_validation_amazon_low_rated_annotated",
        ("proxy_validation_amazon_low_rated_annotated", "tfidf"): "proxy_validation_amazon_low_rated_annotated_tfidf_t005",
        ("proxy_validation_amazon_low_rated_annotated", "embedding"): "proxy_validation_amazon_low_rated_annotated_embed_t025",
    }

    by_dataset = {row["dataset"]: row for row in rows if row.get("dataset")}

    points: dict[str, dict[str, float]] = {}
    for (_, method), dataset_name in wanted.items():
        row = by_dataset.get(dataset_name)
        if not row:
            continue
        canonical = _canonical_key(dataset_name)
        weighted = _to_float(row.get("weighted_jaccard"))
        if weighted is None:
            continue
        points.setdefault(canonical, {})[method] = weighted

    if not points:
        return

    x_order = [
        "proxy_validation_tinder",
        "proxy_validation_gojek",
        "proxy_validation_twitter",
        "proxy_validation_amazon_low_rated",
        "proxy_validation_amazon_low_rated_annotated",
    ]

    method_styles = {
        "lexical": ("blue", r"\MethodLex"),
        "tfidf": ("orange", r"\MethodTFIDF"),
        "embedding": ("teal", r"\MethodEmbed"),
    }

    max_value = 0.0
    for dataset in points.values():
        for value in dataset.values():
            max_value = max(max_value, float(value))
    # Give plots some headroom; keep a stable lower bound for readability.
    ymax = max(0.12, (max_value * 1.15) if max_value > 0 else 0.12)
    ymax = round(ymax + 1e-9, 2)

    lines = [
        r"\begin{tikzpicture}",
        r"\begin{axis}[",
        r"width=0.98\linewidth,",
        r"height=0.52\linewidth,",
        r"ybar,",
        r"bar width=8pt,",
        r"ylabel={Weighted-Jaccard ($W$)},",
        r"symbolic x coords={tinder,gojek,twitter,amazon,amazon-ann},",
        r"xtick=data,",
        r"xticklabels={Tinder,Gojek,Twitter,Amazon,Amazon (ann.)},",
        r"ymin=0,",
        rf"ymax={ymax},",
        r"grid=major,",
        r"legend style={font=\small, at={(0.02,0.98)}, anchor=north west},",
        r"tick label style={font=\small},",
        r"label style={font=\small},",
        r"]",
    ]

    key_to_x = {
        "proxy_validation_tinder": "tinder",
        "proxy_validation_gojek": "gojek",
        "proxy_validation_twitter": "twitter",
        "proxy_validation_amazon_low_rated": "amazon",
        "proxy_validation_amazon_low_rated_annotated": "amazon-ann",
    }

    for method in ("lexical", "tfidf", "embedding"):
        color, legend = method_styles[method]
        coords = []
        for dataset in x_order:
            val = points.get(dataset, {}).get(method)
            if val is None:
                continue
            coords.append(f"({key_to_x[dataset]},{val:.4f})")
        if not coords:
            continue
        lines.append(rf"\addplot[fill={color}!60, draw={color}!80] coordinates {{{' '.join(coords)}}};")
        lines.append(rf"\addlegendentry{{{legend}}}")

    lines += [r"\end{axis}", r"\end{tikzpicture}"]
    (paper_fig_dir / "alignment_plot.tex").write_text("\n".join(lines) + "\n", encoding="ascii")

    taxonomy_path = repo_root / "configs" / "ux" / "friction_taxonomy_v1.json"

    # Always keep the legacy .tex figures for compatibility (no extra deps).
    _write_distribution_example(paper_fig_dir, taxonomy_path)
    _write_bootstrap_ci_plot(paper_fig_dir)

    # Preferred outputs: Python-generated images (requires matplotlib).
    _write_alignment_plot_pdf(paper_fig_dir, points)
    _write_distribution_amazon_ann_pdf(paper_fig_dir, taxonomy_path)
    _write_bootstrap_ci_plot_pdf(paper_fig_dir)
    _write_agent_ablation_pareto_pdf(paper_fig_dir, reports_dir)

    # Help users understand why images might be missing.
    if not (paper_fig_dir / "alignment_plot.pdf").exists():
        print(
            "Note: matplotlib not available; generated legacy TikZ figures (.tex) only. "
            "Install matplotlib to generate PDF/PNG figures.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
