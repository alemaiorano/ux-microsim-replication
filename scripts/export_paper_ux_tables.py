from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os


def _escape_latex(text: str) -> str:
    if text is None:
        return ""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
        "$": r"\$",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in str(text))


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


def _format_float(value: Any, digits: int = 3) -> str:
    number = _to_float(value)
    if number is None:
        return "-"
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


_RUN_TS_RE = re.compile(r"_(\d{8})_(\d{6})$")


def _run_timestamp(run_id: str) -> tuple[str, str]:
    """Extract (YYYYMMDD, HHMMSS) from a run_id; ('', '') if not present."""
    m = _RUN_TS_RE.search(run_id or "")
    return (m.group(1), m.group(2)) if m else ("", "")


def _read_agent_ablation_rows(reports_dir: Path, stem: str) -> list[dict[str, str]]:
    """Read all matching summary CSVs and keep the latest run per (model, condition_label).

    Several reruns of the same condition may exist (e.g. when a batch had transient
    failures and was re-executed under a new RunIdPrefix). We deduplicate by
    (model, condition-label-without-timestamp) and keep the row with the highest
    timestamp suffix in `run_id`, so the table always reflects the most recent
    successful measurement without manual file movement.
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
            label = _infer_run_label(run_id)
            key = (model, label)
            ts = _run_timestamp(run_id)
            if key not in best or ts > best_ts[key]:
                best[key] = row
                best_ts[key] = ts
    # Stable order: model, then condition label.
    return sorted(best.values(), key=lambda r: ((r.get("model") or ""), _infer_run_label((r.get("run_id") or ""))))


DATASET_MACROS = {
    "proxy_validation_tinder": r"\DatasetTinder",
    "proxy_validation_gojek": r"\DatasetGojek",
    "proxy_validation_twitter": r"\DatasetTwitter",
    "proxy_validation_amazon_low_rated": r"\DatasetAmazon",
    "proxy_validation_amazon_low_rated_annotated": r"\DatasetAmazonAnn",
}

METHOD_MACROS = {
    "lexical": r"\MethodLex",
    "tfidf": r"\MethodTFIDF",
    "embedding": r"\MethodEmbed",
}


@dataclass(frozen=True)
class AlignmentRow:
    dataset: str
    records: int
    method: str
    jaccard: float | None
    weighted_jaccard: float | None
    top_k: int | None
    embedding_model: str | None
    embedding_threshold: float | None
    embedding_sample_n: int | None
    tfidf_threshold: float | None


def _canonical_key(dataset: str) -> str:
    for suffix in (
        "_embed_t025",
        "_embed_t045",
        "_embed",
        "_tfidf_t005",
        "_tfidf_t020",
        "_tfidf",
        "_lex_k6",
        "_lex_k10",
    ):
        if dataset.endswith(suffix):
            return dataset[: -len(suffix)]
    return dataset


def _select_alignment_rows(rows: list[AlignmentRow]) -> list[AlignmentRow]:
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
    by_dataset = {row.dataset: row for row in rows}
    selected: list[AlignmentRow] = []
    for (_, _), dataset_name in wanted.items():
        if dataset_name in by_dataset:
            selected.append(by_dataset[dataset_name])
    return selected


def _alignment_rows_from_csv(rows: list[dict[str, str]]) -> list[AlignmentRow]:
    parsed: list[AlignmentRow] = []
    for row in rows:
        dataset = (row.get("dataset") or "").strip()
        if not dataset:
            continue
        parsed.append(
            AlignmentRow(
                dataset=dataset,
                records=int(_to_float(row.get("records")) or 0),
                method=(row.get("method") or "").strip().lower(),
                jaccard=_to_float(row.get("jaccard")),
                weighted_jaccard=_to_float(row.get("weighted_jaccard")),
                top_k=int(_to_float(row.get("top_k")) or 0) or None,
                embedding_model=(row.get("embedding_model") or "").strip() or None,
                embedding_threshold=_to_float(row.get("embedding_threshold")),
                embedding_sample_n=int(_to_float(row.get("embedding_sample_n")) or 0) or None,
                tfidf_threshold=_to_float(row.get("tfidf_threshold")),
            )
        )
    return parsed


def _write_table_alignment_main(output_path: Path, selected: list[AlignmentRow]) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Proxy alignment summary (top-$k$ Jaccard and weighted-Jaccard). For embedding alignment, we embed a subsample of $n=200$ texts for local compute; on large app-review corpora, we additionally cap the proxy slice at $n=10{,}000$ texts.}",
        r"\label{tab:alignment-main}",
        r"\begin{tabular}{llrrr}",
        r"\toprule",
        r"Proxy & Method & $k$ & $J_k$ & $W$ \\",
        r"\midrule",
    ]

    def sort_key(item: AlignmentRow) -> tuple[int, int]:
        proxy_order = [
            "proxy_validation_tinder",
            "proxy_validation_gojek",
            "proxy_validation_twitter",
            "proxy_validation_amazon_low_rated",
            "proxy_validation_amazon_low_rated_annotated",
        ]
        method_order = ["lexical", "tfidf", "embedding"]
        key = _canonical_key(item.dataset)
        return (proxy_order.index(key) if key in proxy_order else 999, method_order.index(item.method))

    for row in sorted(selected, key=sort_key):
        canonical = _canonical_key(row.dataset)
        proxy = DATASET_MACROS.get(canonical, _escape_latex(canonical))
        method = METHOD_MACROS.get(row.method, _escape_latex(row.method))
        lines.append(
            f"{proxy} & {method} & "
            f"{row.top_k or '-'} & "
            f"{_format_float(row.jaccard, 3)} & "
            f"{_format_float(row.weighted_jaccard, 3)} \\\\"
        )

    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _write_table_run_contract(output_path: Path, alignment_rows: list[AlignmentRow], appstore_eval: dict[str, Any], appstore_eval_extras: list[dict[str, Any]] | None = None) -> None:
    # Keep this table simple and stable; it is intended as a reproducibility contract, not a full config dump.
    embed_rows = [row for row in alignment_rows if row.method == "embedding" and row.embedding_sample_n not in (None, 0)]

    # Prefer the main embedding setting when available.
    preferred = next((row for row in embed_rows if row.dataset == "proxy_validation_amazon_low_rated_embed"), None)
    if preferred is None:
        preferred = next((row for row in embed_rows if row.dataset.endswith("_embed_t025")), None)
    if preferred is None:
        preferred = next((row for row in embed_rows if _to_float(row.embedding_threshold) == 0.35), None)
    if preferred is None:
        preferred = next((row for row in embed_rows if _to_float(row.embedding_threshold) == 0.25), None)
    if preferred is None and embed_rows:
        # Fallback: pick the smallest threshold we observed (tends to match defaults).
        preferred = min(embed_rows, key=lambda r: (_to_float(r.embedding_threshold) or 999))

    embed_n = (preferred.embedding_model if preferred else None) or "bge-m3"
    # Normalize the model name to its canonical capitalization for the paper.
    if embed_n.lower() == "bge-m3":
        embed_n = "BGE-M3"
    embed_thr = _to_float(preferred.embedding_threshold) if preferred else 0.25
    embed_sample = int(_to_float(preferred.embedding_sample_n) or 0) if preferred else 200
    if embed_sample <= 0:
        embed_sample = 200

    model = _escape_latex(appstore_eval.get("model", "llama3.1:8b-instruct-q4_K_M"))
    n = int(_to_float(appstore_eval.get("sample_n")) or 0)

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Protocol summary (defaults).}",
        r"\label{tab:run-contract}",
        r"\begin{tabular}{ll}",
        r"\toprule",
        r"Setting & Value \\",
        r"\midrule",
        r"Taxonomy & friction\_taxonomy\_v1 (fixed) \\",
        r"Top-$k$ for $J_k$ & 8 \\",
        r"TF-IDF threshold & 0.05 \\",
        rf"Embedding model & {_escape_latex(embed_n)} \\",
        rf"Embedding threshold & {_format_float(embed_thr)} \\",
        rf"Embedding subsample per corpus & {embed_sample} \\",
    ]
    # Provider-only: prefer the Azure-hosted provider model when available.
    label_model = ""
    if appstore_eval_extras:
        label_model = _escape_latex(appstore_eval_extras[0].get("model", ""))
    if not label_model:
        label_model = model
    lines += [
        rf"LLM label eval model & {label_model} \\",
        rf"LLM label eval sample ($n$) & {n} \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        "",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _write_table_bootstrap(output_path: Path, payload: dict[str, Any]) -> None:
    if not payload:
        return
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Bootstrap confidence intervals for alignment metrics (Amazon low-rated; lexical).}",
        r"\label{tab:bootstrap-ci}",
        r"\begin{tabular}{lrr}",
        r"\toprule",
        r"Metric & Mean & 95\% CI \\",
        r"\midrule",
    ]
    j_mean = _format_float(payload.get("jaccard_mean"))
    j_low = _format_float(payload.get("jaccard_ci_low"))
    j_high = _format_float(payload.get("jaccard_ci_high"))
    w_mean = _format_float(payload.get("weighted_mean"))
    w_low = _format_float(payload.get("weighted_ci_low"))
    w_high = _format_float(payload.get("weighted_ci_high"))
    lines.append(rf"$J_k$ & {j_mean} & [{j_low}, {j_high}] \\")
    lines.append(rf"$W$ & {w_mean} & [{w_low}, {w_high}] \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


_BOOTSTRAP_SOURCES = [
    # (json filename, dataset label, method label)
    ("alignment_bootstrap.json", r"\DatasetAmazon", r"\MethodLex"),
    ("alignment_bootstrap_tfidf_amazon.json", r"\DatasetAmazon", r"\MethodTFIDF"),
    ("alignment_bootstrap_tfidf_amazon_ann.json", r"\DatasetAmazonAnn", r"\MethodTFIDF"),
    ("alignment_bootstrap_embed_amazon.json", r"\DatasetAmazon", r"\MethodEmbed"),
    ("alignment_bootstrap_lex_tinder.json", r"\DatasetTinder", r"\MethodLex"),
    ("alignment_bootstrap_embed_tinder.json", r"\DatasetTinder", r"\MethodEmbed"),
    ("alignment_bootstrap_lex_gojek.json", r"\DatasetGojek", r"\MethodLex"),
    ("alignment_bootstrap_embed_gojek.json", r"\DatasetGojek", r"\MethodEmbed"),
]


def _write_table_bootstrap_multi(output_path: Path, reports_dir: Path) -> None:
    rows: list[tuple[str, str, dict[str, Any]]] = []
    for filename, dataset_label, method_label in _BOOTSTRAP_SOURCES:
        payload = _read_json(reports_dir / filename)
        if not payload:
            continue
        rows.append((dataset_label, method_label, payload))
    if not rows:
        return

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Bootstrap confidence intervals for alignment metrics across method--dataset pairs (200 iterations for lexical/TF-IDF, 50 for embedding; bootstrap resample size noted as $n$).}",
        r"\label{tab:bootstrap-ci-multi}",
        r"\resizebox{0.98\linewidth}{!}{%",
        r"\begin{tabular}{llrrrrr}",
        r"\toprule",
        r"Dataset & Method & $n$ & $J_k$ mean & $J_k$ 95\% CI & $W$ mean & $W$ 95\% CI \\",
        r"\midrule",
    ]
    for dataset_label, method_label, payload in rows:
        n = int(_to_float(payload.get("sample_size")) or 0)
        j_mean = _format_float(payload.get("jaccard_mean"))
        j_low = _format_float(payload.get("jaccard_ci_low"))
        j_high = _format_float(payload.get("jaccard_ci_high"))
        w_mean = _format_float(payload.get("weighted_mean"), digits=4)
        w_low = _format_float(payload.get("weighted_ci_low"), digits=4)
        w_high = _format_float(payload.get("weighted_ci_high"), digits=4)
        lines.append(
            f"{dataset_label} & {method_label} & {n} & {j_mean} & [{j_low}, {j_high}] & "
            f"{w_mean} & [{w_low}, {w_high}] \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _write_table_appstore_eval(output_path: Path, primary_payload: dict[str, Any], extra_payloads: list[dict[str, Any]] | None = None) -> None:
    # Provider-only policy: when a provider (Azure) eval is available, it supersedes the
    # legacy local (Ollama) eval. The local artifact is kept on disk for reproducibility but
    # is not surfaced in the paper, matching the policy of the main UX simulator track.
    payloads: list[dict[str, Any]] = list(extra_payloads or [])
    if not payloads and primary_payload:
        payloads = [primary_payload]
    if not payloads:
        return
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{LLM label evaluation on the Amazon Appstore annotated subset, using the same provider model family as the main UX agent-ablation matrix to keep the local-vs-provider policy consistent across tracks.}",
        r"\label{tab:appstore-eval}",
        r"\begin{tabular}{lrr}",
        r"\toprule",
        r"Model & Accuracy & Macro-F1 \\",
        r"\midrule",
    ]
    for payload in payloads:
        model = _escape_latex(payload.get("model", ""))
        n = int(_to_float(payload.get("sample_n")) or 0)
        acc = _format_float(payload.get("accuracy"))
        macro = _format_float(payload.get("macro_f1"))
        lines.append(rf"{model} (n={n}) & {acc} & {macro} \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _write_table_appstore_baselines(output_path: Path, payload: dict[str, Any]) -> None:
    if not payload:
        return
    majority = payload.get("majority", {})
    lexical = payload.get("lexical", {})
    tfidf = payload.get("tfidf_logreg_cv")
    embed = payload.get("ollama_embed_logreg_cv")

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Cheap baselines for the annotated Appstore subset (same $n$ as Table~\ref{tab:appstore-eval}); embedding baseline uses a subset for cost.}",
        r"\label{tab:appstore-baselines}",
        r"\begin{tabular}{lrr}",
        r"\toprule",
        r"Baseline & Accuracy & Macro-F1 \\",
        r"\midrule",
        rf"Majority & {_format_float(majority.get('accuracy'))} & {_format_float(majority.get('macro_f1'))} \\",
        rf"Lexical taxonomy match & {_format_float(lexical.get('accuracy'))} & {_format_float(lexical.get('macro_f1'))} \\",
    ]
    if isinstance(tfidf, dict):
        lines.append(
            rf"TF-IDF + logistic regression (CV) & {_format_float(tfidf.get('accuracy_mean'))} & {_format_float(tfidf.get('macro_f1_mean'))} \\"
        )
    if isinstance(embed, dict):
        model = _escape_latex(embed.get("embedding_model", ""))
        used = int(_to_float(embed.get("records_used")) or 0)
        total = int(_to_float(embed.get("records_total")) or 0)
        note = ""
        if used:
            note = f" (n={used})"
        lines.append(
            rf"Embedding ({model}) + logistic regression (CV){_escape_latex(note)} & {_format_float(embed.get('accuracy_mean'))} & {_format_float(embed.get('macro_f1_mean'))} \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _write_table_appstore_confusions(output_path: Path, csv_path: Path, max_rows: int = 8) -> None:
    if not csv_path.exists():
        return
    rows = _read_csv(csv_path)
    if not rows:
        return

    counts: dict[tuple[str, str], int] = {}
    total = 0
    for row in rows:
        gold = (row.get("gold_label") or "").strip()
        pred = (row.get("pred_label") or "").strip()
        if not gold or not pred:
            continue
        total += 1
        if gold == pred:
            continue
        counts[(gold, pred)] = counts.get((gold, pred), 0) + 1

    if not counts:
        return

    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))[:max_rows]

    def fmt_label(label: str) -> str:
        return r"\texttt{" + _escape_latex(label) + "}"

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        rf"\caption{{Most frequent label confusions in LLM classification (Amazon annotated; n={total}).}}",
        r"\label{tab:appstore-confusions}",
        r"\resizebox{0.98\linewidth}{!}{%",
        r"\begin{tabular}{llr}",
        r"\toprule",
        r"Gold & Predicted & Count \\",
        r"\midrule",
    ]

    for (gold, pred), count in ordered:
        lines.append(rf"{fmt_label(gold)} & {fmt_label(pred)} & {count} \\")

    lines += [r"\bottomrule", r"\end{tabular}", r"}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _write_table_alignment_sensitivity(output_path: Path, md_path: Path) -> None:
    if not md_path.exists():
        return
    raw = md_path.read_text(encoding="utf-8").splitlines()
    rows: list[list[str]] = []
    for line in raw:
        if not line.startswith("|") or "run" in line or "---" in line:
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) != 7:
            continue
        rows.append(cols)
    if not rows:
        return

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\small",
        r"\caption{Sensitivity analysis on the Amazon annotated proxy (selected settings).}",
        r"\label{tab:alignment-sensitivity}",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Variant & $k$ & Threshold & $J_k$ & $W$ \\",
        r"\midrule",
    ]

    def variant_label(method: str) -> str:
        return METHOD_MACROS.get(method, _escape_latex(method))

    for run, method, top_k, tfidf_thr, embed_thr, jaccard, weighted in rows:
        threshold = "-"
        if method == "tfidf":
            threshold = tfidf_thr
        elif method == "embedding":
            threshold = embed_thr
        lines.append(
            f"{variant_label(method)} & {_escape_latex(top_k)} & {_escape_latex(threshold)} & "
            f"{_escape_latex(jaccard)} & {_escape_latex(weighted)} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _write_table_alignment_oss(output_path: Path, rows: list[AlignmentRow]) -> None:
    oss_prefixes = (
        "proxy_validation_grafana_",
        "proxy_validation_prometheus_",
        "proxy_validation_open-telemetry__",
        "proxy_validation_openzipkin__",
        "proxy_validation_jaegertracing__",
        "proxy_validation_getsentry__",
    )
    oss_rows = [row for row in rows if row.dataset.startswith(oss_prefixes)]
    if not oss_rows:
        return

    def repo_label(dataset: str) -> str:
        mapping = [
            ("proxy_validation_getsentry__sentry_", "Sentry"),
            ("proxy_validation_grafana_", "Grafana"),
            ("proxy_validation_jaegertracing__jaeger_", "Jaeger"),
            ("proxy_validation_open-telemetry__opentelemetry-collector_", "OpenTelemetry Collector"),
            ("proxy_validation_open-telemetry__opentelemetry-js_", "OpenTelemetry JS"),
            ("proxy_validation_openzipkin__zipkin_", "Zipkin"),
            ("proxy_validation_prometheus_", "Prometheus"),
        ]
        for prefix, label in mapping:
            if dataset.startswith(prefix):
                return label
        return dataset

    def prefer(candidate: AlignmentRow, current: AlignmentRow | None) -> bool:
        if current is None:
            return True

        score_candidate = 0
        score_current = 0

        if "__" in candidate.dataset:
            score_candidate += 2
        if "__" in current.dataset:
            score_current += 2

        if candidate.method == "lexical" and candidate.dataset.endswith("_lexical"):
            score_candidate += 2
        if current.method == "lexical" and current.dataset.endswith("_lexical"):
            score_current += 2

        if candidate.method == "embedding" and candidate.dataset.endswith("_embedding"):
            score_candidate += 2
        if current.method == "embedding" and current.dataset.endswith("_embedding"):
            score_current += 2

        if candidate.records > current.records:
            score_candidate += 1
        elif current.records > candidate.records:
            score_current += 1

        if score_candidate != score_current:
            return score_candidate > score_current

        return candidate.dataset > current.dataset

    grouped: dict[str, dict[str, AlignmentRow]] = {}
    for row in oss_rows:
        repo = repo_label(row.dataset)
        by_method = grouped.setdefault(repo, {})
        if prefer(row, by_method.get(row.method)):
            by_method[row.method] = row
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{OSS issues proxy alignment (selected repositories).}",
        r"\label{tab:alignment-oss}",
        r"\begin{tabular}{lrr}",
        r"\toprule",
        rf"Repository & $W$ ({METHOD_MACROS['lexical']}) & $W$ ({METHOD_MACROS['embedding']}) \\",
        r"\midrule",
    ]
    for repo in sorted(grouped.keys()):
        lex = grouped[repo].get("lexical")
        emb = grouped[repo].get("embedding")
        if not lex and not emb:
            continue
        lines.append(
            f"{_escape_latex(repo)} & {_format_float(lex.weighted_jaccard) if lex else '-'} & "
            f"{_format_float(emb.weighted_jaccard) if emb else '-'} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _agent_label(agent: str) -> str:
    mapping = {
        "single_pass": "Single-pass",
        "write_then_score": "Best-of-N",
        "hybrid": "Hybrid",
        "anchoring_aware": "Score-then-select",
    }
    return mapping.get(agent, agent or "-")


def _prompt_label(prompt_path: str) -> str:
    name = Path(prompt_path).name if prompt_path else "-"
    if name == "ux_simulation.md":
        return "v1"
    if name == "ux_simulation_v2.md":
        return "v2"
    return name


_RUN_ID_N_RE = re.compile(r"_n(?P<n>\d+)(?:_|$)", flags=re.IGNORECASE)


def _infer_candidate_n(row: dict[str, str]) -> str:
    configured = (row.get("candidate_n_configured") or "").strip()
    if configured:
        return configured
    run_id = (row.get("run_id") or "").strip()
    match = _RUN_ID_N_RE.search(run_id)
    if match:
        return match.group("n")
    candidate_n = (row.get("candidate_n_requested") or "").strip()
    return candidate_n or "-"


_RUN_ID_LABEL_RE = re.compile(r"^(?:ablation_ux_(?:hq|cq)_)?(?P<label>.+?)_\d{8}_\d{6}$", flags=re.IGNORECASE)
# Canonical-label extractor: locate the condition portion (starting at v<digit>) and
# strip any rerun / model-scoped prefix and the trailing timestamp. This lets us
# match the same condition across reruns with different RunIdPrefix values.
_RUN_ID_CANONICAL_RE = re.compile(r"(?P<label>v\d+_[A-Za-z0-9_]+?)_\d{8}_\d{6}$", flags=re.IGNORECASE)


def _infer_run_label(run_id: str) -> str:
    run_id = (run_id or "").strip()
    if not run_id:
        return "-"
    canonical = _RUN_ID_CANONICAL_RE.search(run_id)
    if canonical:
        return canonical.group("label")
    match = _RUN_ID_LABEL_RE.match(run_id)
    if match:
        return match.group("label")
    # Fallback: remove trailing timestamp if present.
    parts = run_id.split("_")
    if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
        return "_".join(parts[:-2])
    return run_id


_TEMP_RE = re.compile(r"_t(?P<t>\d{2})", flags=re.IGNORECASE)


def _infer_candidate_temperature_from_label(label: str) -> float | None:
    match = _TEMP_RE.search(label or "")
    if not match:
        return None
    t = int(match.group("t"))
    return float(t) / 10.0


def _judge_label(judge_mode: str) -> str:
    mode = (judge_mode or "").strip().lower()
    if mode == "auto":
        return "Auto"
    return "LLM"


def _hybrid_fallback_label(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "-"
    return _agent_label(text)


def _write_table_agent_ablation(
    output_path: Path,
    rows: list[dict[str, str]],
    caption: str,
    label: str,
) -> None:
    if not rows:
        return

    def pick(row: dict[str, str], key: str) -> str:
        return str(row.get(key, "") or "").strip()

    agent_order = {"single_pass": 0, "hybrid": 1, "write_then_score": 2, "anchoring_aware": 3}
    rows = sorted(
        rows,
        key=lambda r: (
            pick(r, "model"),
            agent_order.get(pick(r, "agent"), 99),
            _prompt_label(pick(r, "prompt_path")),
            pick(r, "judge_mode"),
        ),
    )

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        rf"\caption{{{_escape_latex(caption)}}}",
        rf"\label{{{_escape_latex(label)}}}",
        r"\resizebox{0.98\linewidth}{!}{%",
        r"\begin{tabular}{llllrrrrrrr}",
        r"\toprule",
        r"Model & Agent & Judge & Fallback & $N$ & Prefix ok & Calls & Quality & Q/Cost & Hall.\ proxy & Fab.\ proxy \\",
        r"\midrule",
    ]
    for row in rows:
        prompt_label = _prompt_label(pick(row, "prompt_path"))
        agent_raw = pick(row, "agent")
        model = _escape_latex(pick(row, "model") or "-")
        agent = _escape_latex(_agent_label(agent_raw))
        judge = "-" if agent_raw == "single_pass" else _escape_latex(_judge_label(pick(row, "judge_mode")))
        fallback_raw = pick(row, "hybrid_fallback")
        if agent_raw == "hybrid" and not fallback_raw:
            fallback_raw = "write_then_score"
        fallback = "-" if agent_raw != "hybrid" else _escape_latex(_hybrid_fallback_label(fallback_raw))
        n = _escape_latex(_infer_candidate_n(row))
        prefix_ok = "-" if prompt_label == "v1" else _format_float(pick(row, "friction_prefix_ok_rate"), digits=3)
        calls = _format_float(pick(row, "cost_units_per_sim"), digits=3)
        quality = _format_float(pick(row, "quality_score"), digits=3)
        qpc = _format_float(pick(row, "quality_per_cost"), digits=3)
        hall = _format_float(pick(row, "avg_hallucination_proxy"), digits=3)
        fab = _format_float(pick(row, "fabrication_proxy_rate"), digits=3)
        lines.append(
            f"{model} & {agent} & {judge} & {fallback} & {n} & {prefix_ok} & {calls} & {quality} & {qpc} & {hall} & {fab} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _write_table_agent_conditions(output_path: Path, hq_rows: list[dict[str, str]], cq_rows: list[dict[str, str]]) -> None:
    if not hq_rows and not cq_rows:
        return

    def pick(row: dict[str, str], key: str) -> str:
        return str(row.get(key, "") or "").strip()

    def row_key(row: dict[str, str]) -> tuple[int, str]:
        agent = pick(row, "agent")
        agent_order = {"single_pass": 0, "hybrid": 1, "write_then_score": 2, "anchoring_aware": 3}
        return (agent_order.get(agent, 99), pick(row, "model"), _infer_run_label(pick(row, "run_id")))

    hq_rows = sorted(hq_rows, key=row_key)
    cq_rows = sorted(cq_rows, key=row_key)

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Experimental conditions for agent ablations: each row is uniquely identified by the (Suite, Model, Agent, $N$, CandT, Judge, Fallback) tuple; the legacy compound condition label that encoded the same information as a single underscore-separated token is omitted for readability.}",
        r"\label{tab:agent-ablation-conditions}",
        r"\resizebox{\linewidth}{!}{%",
        r"\begin{tabular}{lllrlllrr}",
        r"\toprule",
        r"Suite & Model & Agent & $N$ & CandT & Judge & Fallback & Calls & Quality \\",
        r"\midrule",
    ]

    def emit(suite: str, rows: list[dict[str, str]]) -> None:
        for row in rows:
            cond_raw = _infer_run_label(pick(row, "run_id"))
            model = _escape_latex(pick(row, "model") or "-")
            agent = _escape_latex(_agent_label(pick(row, "agent")))
            n = _escape_latex(_infer_candidate_n(row))
            candt = _format_float(pick(row, "candidate_temperature_configured") or pick(row, "candidate_temperature"), digits=2)
            if candt == "-":
                inferred = _infer_candidate_temperature_from_label(cond_raw)
                if inferred is not None:
                    candt = _format_float(inferred, digits=2)
            agent_raw = pick(row, "agent")
            judge = "-" if agent_raw == "single_pass" else _escape_latex(_judge_label(pick(row, "judge_mode")))
            fallback = "-" if agent_raw != "hybrid" else _escape_latex(_hybrid_fallback_label(pick(row, "hybrid_fallback")))
            calls = _format_float(pick(row, "cost_units_per_sim"), digits=3)
            quality = _format_float(pick(row, "quality_score"), digits=3)
            lines.append(
                f"{suite} & {model} & {agent} & {n} & {candt} & {judge} & {fallback} & {calls} & {quality} \\\\"
            )

    emit("HQ", hq_rows)
    if hq_rows and cq_rows:
        lines.append(r"\midrule")
    emit("CQ", cq_rows)

    lines += [r"\bottomrule", r"\end{tabular}", r"}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _write_table_agent_output_examples(
    output_path: Path,
    runs_root: Path,
    hq_rows: list[dict[str, str]],
) -> None:
    if not hq_rows:
        return

    def pick(row: dict[str, str], key: str) -> str:
        return str(row.get(key, "") or "").strip()

    preferred_model = os.getenv("UX_AGENT_EXAMPLE_MODEL", "gpt-4.1").strip()
    model_rows = [row for row in hq_rows if pick(row, "model") == preferred_model]
    if model_rows:
        hq_rows = model_rows

    def find_run_id(pattern: str) -> str | None:
        for row in hq_rows:
            rid = pick(row, "run_id")
            if pattern in rid:
                return rid
        return None

    run_single = find_run_id("_v2_single_")
    run_wts = find_run_id("_v2_wts_n2_t03_")
    run_wts_auto = find_run_id("_v3_wts_auto_n2_t03_")
    if not (run_single and run_wts and run_wts_auto):
        return

    n_value = "?"
    for row in hq_rows:
        if pick(row, "run_id") == run_single:
            n_value = pick(row, "n") or "?"
            break

    def by_key(run_id: str) -> dict[tuple[str, str, str], dict[str, Any]]:
        records = _read_jsonl(runs_root / run_id / "simulations.jsonl")
        mapping: dict[tuple[str, str, str], dict[str, Any]] = {}
        for rec in records:
            key = (
                str(rec.get("persona_id", "") or ""),
                str(rec.get("journey_id", "") or ""),
                str(rec.get("task_id", "") or ""),
            )
            mapping[key] = rec
        return mapping

    a = by_key(run_single)
    b = by_key(run_wts)
    c = by_key(run_wts_auto)
    keys = sorted(set(a) & set(b) & set(c))
    if not keys:
        return

    def friction(rec: dict[str, Any]) -> str:
        fps = rec.get("friction_points")
        if isinstance(fps, list) and fps and isinstance(fps[0], str):
            return fps[0]
        return "-"

    def fix(rec: dict[str, Any]) -> str:
        return str(rec.get("suggested_fix", "") or "").strip() or "-"

    def _is_present(text: str) -> bool:
        t = str(text or "").strip()
        return bool(t) and t != "-" and t.lower() not in {"n/a", "na", "none", "null"}

    chosen = keys[0]
    valid_keys: list[tuple[str, str, str]] = []
    for key in keys:
        fa, fb, fc = friction(a[key]), friction(b[key]), friction(c[key])
        xa, xb, xc = fix(a[key]), fix(b[key]), fix(c[key])
        if not (_is_present(fa) and _is_present(fb) and _is_present(fc) and _is_present(xa) and _is_present(xb) and _is_present(xc)):
            continue
        valid_keys.append(key)
        frs = {fa, fb, fc}
        fxs = {xa, xb, xc}
        if len(frs) > 1 or len(fxs) > 1:
            chosen = key
            break
    if valid_keys:
        # Fallback: pick any fully-populated example even if outputs match.
        chosen = chosen if chosen in valid_keys else valid_keys[0]

    def esc(text: str) -> str:
        return _escape_latex(text).encode("ascii", errors="ignore").decode("ascii")

    rows = [
        ("Single-pass", a[chosen]),
        ("Best-of-2 (LLM judge)", b[chosen]),
        ("Best-of-2 (auto)", c[chosen]),
    ]
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        rf"\caption{{Example outputs for the same (persona, journey, task) under different agent strategies (HQ suite; model={_escape_latex(preferred_model)}; $n={_escape_latex(n_value)}$).}}",
        r"\label{tab:agent-output-examples}",
        r"\resizebox{0.98\linewidth}{!}{%",
        r"\begin{tabular}{lp{0.46\linewidth}p{0.46\linewidth}}",
        r"\toprule",
        r"Setting & Friction point & Suggested fix \\",
        r"\midrule",
    ]
    for name, rec in rows:
        lines.append(f"{esc(name)} & {esc(friction(rec))} & {esc(fix(rec))} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _fabrication_setting_label(run_label: str) -> str:
    """Map a raw condition label like ``v3_hybrid_sts_auto_n2_t03`` to a
    reader-friendly setting string like ``Hybrid (score-then-select, auto judge)``.

    Mirrors the disambiguation now applied to the conditions table: the
    compound run-id encodes (agent, fallback, judge mode); we present that as
    a human-readable phrase instead of an underscore-separated token.
    """
    label = (run_label or "").lower()
    is_hybrid_sts = "hybrid_sts" in label
    is_hybrid = "hybrid" in label and not is_hybrid_sts
    is_wts = "wts" in label
    is_single = "single" in label
    # The v3_* prefix or an explicit "auto" tag both encode auto-judge selection.
    is_auto = "auto" in label or label.startswith("v3_") or "_v3_" in label
    judge = "auto judge" if is_auto else "LLM judge"
    if is_single:
        return "Single-pass"
    if is_hybrid_sts:
        return f"Hybrid (score-then-select, {judge})"
    if is_hybrid:
        return f"Hybrid (best-of-$N$ fallback, {judge})"
    if is_wts:
        return f"Best-of-$N$ ({judge})"
    return run_label


def _write_table_fabrication_examples(output_path: Path, examples_json_path: Path, max_rows: int = 4) -> None:
    """Render adversarial-judge fabrication examples directly from the JSON.

    The legacy hand-edited table mixed real fabricated examples with manually invented
    non-fabricated rows, which violated the artifact-first contract. The artifact only
    contains items flagged as fabricated (the eval is one-sided), so this table now
    honestly reports them as such with caption matching the data.
    """
    if not examples_json_path.exists():
        return
    try:
        items = json.loads(examples_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if not isinstance(items, list) or not items:
        return

    rows: list[dict[str, Any]] = []
    seen_friction: set[str] = set()
    for entry in sorted(items, key=lambda d: -float(d.get("confidence") or 0.0)):
        if not entry.get("fabricated"):
            continue
        friction_list = entry.get("friction_points") or []
        friction = friction_list[0] if friction_list else ""
        if not friction:
            continue
        if friction in seen_friction:
            continue
        seen_friction.add(friction)
        rows.append(entry)
        if len(rows) >= max_rows:
            break

    if not rows:
        return

    def _trim(text: str, limit: int = 160) -> str:
        import unicodedata
        text = str(text or "").strip().replace("\n", " ")
        # Normalize to ASCII so the output file (encoded as ASCII for stability) round-trips.
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        # Replace underscores with hyphens so escaped \_ sequences do not create
        # unbreakable tokens that overflow narrow p{} columns.
        text = text.replace("_", "-")
        if len(text) > limit:
            text = text[: limit - 3].rstrip() + "..."
        return _escape_latex(text)

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        rf"\caption{{Top examples flagged as fabricated by an adversarial judge ({len(rows)} representative cases, HQ ablation; the eval only emits items where unsupported spans are detected, so all rows are positive cases by construction).}}",
        r"\label{tab:fabrication-examples}",
        r"\begin{tabular}{p{0.22\linewidth}rp{0.20\linewidth}p{0.42\linewidth}}",
        r"\toprule",
        r"Setting & Conf. & Friction & Unsupported span / rationale \\",
        r"\midrule",
    ]
    for entry in rows:
        run_label = _infer_run_label(str(entry.get("run_id") or ""))
        # Map the compound run label to a human-readable setting descriptor.
        setting_display = _fabrication_setting_label(run_label)
        conf = _format_float(entry.get("confidence"), digits=2)
        friction = _trim(entry.get("friction_points", [""])[0], limit=80)
        spans = entry.get("unsupported_spans") or []
        span_text = spans[0] if spans else ""
        rationale = entry.get("rationale") or ""
        details = _trim(f"span: {span_text} | {rationale}", limit=200)
        lines.append(
            rf"{setting_display} & {conf} & {friction} & {details} \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def _write_table_taxonomy(output_path: Path, taxonomy_json_path: Path) -> None:
    if not taxonomy_json_path.exists():
        return
    payload = _read_json(taxonomy_json_path)
    categories = payload.get("categories", {})
    default_weights = payload.get("default_weights", {})
    if not categories:
        return

    def _shorten(keywords: list[str], limit: int = 6) -> str:
        ascii_only = []
        for kw in keywords:
            cleaned = str(kw).strip()
            if not cleaned:
                continue
            ascii_only.append(cleaned)
            if len(ascii_only) >= limit:
                break
        if len(keywords) > limit:
            ascii_only.append("...")
        return ", ".join(_escape_latex(k) for k in ascii_only)

    version = _escape_latex(payload.get("version", "v1"))
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\small",
        rf"\caption{{Friction taxonomy ({version}): categories, default weights, and representative keywords (truncated to 6 per row; the complete multilingual keyword list and weight overrides are in the versioned taxonomy configuration).}}",
        r"\label{tab:friction-taxonomy}",
        r"\begin{tabular}{lrp{0.58\linewidth}}",
        r"\toprule",
        r"Category & Default $w$ & Representative keywords \\",
        r"\midrule",
    ]
    for category in sorted(categories.keys()):
        keywords = categories.get(category, []) or []
        if not isinstance(keywords, list):
            continue
        weight = _format_float(default_weights.get(category, 1.0), digits=2)
        cat_label = r"\texttt{" + _escape_latex(category) + "}"
        lines.append(f"{cat_label} & {weight} & {_shorten(keywords)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="ascii")


def main() -> None:
    reports_dir = Path("reports/ux")
    paper_dir = Path("paper_ux")
    tables_dir = paper_dir / "tables"

    alignment_rows = _alignment_rows_from_csv(_read_csv(reports_dir / "alignment_table.csv"))
    selected = _select_alignment_rows(alignment_rows)
    appstore_eval = _read_json(reports_dir / "annotations/amazon_appstore_eval.json")
    appstore_eval_extras: list[dict[str, Any]] = []
    for extra_path in sorted((reports_dir / "annotations").glob("amazon_appstore_eval_*.json")):
        if extra_path.name == "amazon_appstore_eval.json":
            continue
        payload = _read_json(extra_path)
        if payload:
            appstore_eval_extras.append(payload)

    _write_table_alignment_main(tables_dir / "alignment_main.tex", selected)
    _write_table_run_contract(tables_dir / "run_contract.tex", alignment_rows, appstore_eval, appstore_eval_extras)
    _write_table_bootstrap(tables_dir / "bootstrap_ci.tex", _read_json(reports_dir / "alignment_bootstrap.json"))
    _write_table_bootstrap_multi(tables_dir / "bootstrap_ci_multi.tex", reports_dir)
    _write_table_appstore_eval(tables_dir / "appstore_eval.tex", appstore_eval, appstore_eval_extras)
    _write_table_appstore_baselines(
        tables_dir / "appstore_baselines.tex",
        _read_json(reports_dir / "annotations/amazon_appstore_baseline_eval.json"),
    )
    # Provider-only policy: confusions come from the provider eval when available.
    confusions_csv = reports_dir / "annotations/amazon_appstore_eval.csv"
    for cand in sorted((reports_dir / "annotations").glob("amazon_appstore_eval_*.csv")):
        if cand.name != "amazon_appstore_eval.csv":
            confusions_csv = cand
            break
    _write_table_appstore_confusions(
        tables_dir / "appstore_confusions.tex",
        confusions_csv,
    )
    _write_table_alignment_sensitivity(tables_dir / "alignment_sensitivity.tex", reports_dir / "alignment_sensitivity.md")
    _write_table_alignment_oss(tables_dir / "alignment_oss.tex", alignment_rows)
    hq_rows = _read_agent_ablation_rows(reports_dir, "agent_ablation_hallucination_quality_summary")
    cq_rows = _read_agent_ablation_rows(reports_dir, "agent_ablation_cost_quality_summary")
    _write_table_agent_ablation(
        tables_dir / "agent_ablation_hq.tex",
        hq_rows,
        caption="Agent ablation (hallucination-quality focus).",
        label="tab:agent-ablation-hq",
    )
    _write_table_agent_ablation(
        tables_dir / "agent_ablation_cq.tex",
        cq_rows,
        caption="Agent ablation (cost-quality focus).",
        label="tab:agent-ablation-cq",
    )
    _write_table_agent_conditions(
        tables_dir / "agent_ablation_conditions.tex",
        hq_rows,
        cq_rows,
    )
    _write_table_agent_output_examples(
        tables_dir / "agent_output_examples.tex",
        Path("reports/ux/runs"),
        hq_rows,
    )
    _write_table_taxonomy(
        tables_dir / "friction_taxonomy.tex",
        Path("configs/ux/friction_taxonomy_v1.json"),
    )
    _write_table_fabrication_examples(
        tables_dir / "fabrication_examples.tex",
        reports_dir / "fabrication_ablation_hq_summary_examples.json",
    )


if __name__ == "__main__":
    main()
