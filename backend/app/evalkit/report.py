"""Render evaluation reports as a text table, Markdown, and JSON."""

import json
from dataclasses import asdict
from pathlib import Path

from app.evalkit.runner import EvalReport

HEADLINE_METRICS: tuple[tuple[str, str], ...] = (
    ("retrieval_recall_at_1", "retrieval recall@1"),
    ("retrieval_recall_at_5", "retrieval recall@5"),
    ("retrieval_mrr", "retrieval MRR"),
    ("extraction_micro_f1", "clause span F1"),
    ("extraction_type_micro_f1", "clause type F1"),
    ("citation_faithfulness", "citation faithfulness"),
    ("offset_integrity", "offset integrity"),
    ("risk_flag_accuracy", "risk-flag accuracy"),
    ("risk_flag_micro_f1", "risk-flag F1"),
)


def format_metric(value: float) -> str:
    """Three decimal places, shared by the CLI table and the README."""

    return f"{value:.3f}"


def render_headline_table(report: EvalReport) -> str:
    """Plain-text table of baseline versus upgraded headline metrics."""

    baseline = report.strategies["baseline"]
    upgraded = report.strategies["upgraded"]
    header = f"{'metric':<24} {'baseline':>10} {'upgraded':>10} {'delta':>10}"
    lines = [
        (
            f"provider={report.provider}  judge={upgraded.judge}  "
            f"contracts={report.contract_count}  questions={report.question_count}"
        ),
        header,
        "-" * len(header),
    ]
    for attribute, label in HEADLINE_METRICS:
        before = getattr(baseline, attribute)
        after = getattr(upgraded, attribute)
        lines.append(
            f"{label:<24} {format_metric(before):>10} {format_metric(after):>10} {format_metric(after - before):>10}"
        )
    return "\n".join(lines)


def render_markdown(report: EvalReport) -> str:
    """Markdown report, including per-type span F1."""

    lines = [
        "# ArbiLens evaluation",
        "",
        f"- Provider: `{report.provider}` (offline deterministic embedder and extractive reader)",
        f"- Dataset fingerprint: `{report.dataset_fingerprint}`",
        f"- Contracts: {report.contract_count}",
        f"- Questions: {report.question_count}",
        "",
        "Span F1 requires intersection-over-union of at least 0.5 with the gold clause.",
        "Type F1 accepts any overlapping span of the right clause type, so a fixed window",
        "that catches the heading still counts. Citation faithfulness requires the gold",
        "evidence sentence to appear inside a citation whose offsets match the document.",
        "",
        "| metric | baseline | upgraded | delta |",
        "| --- | ---: | ---: | ---: |",
    ]
    baseline = report.strategies["baseline"]
    upgraded = report.strategies["upgraded"]
    for attribute, label in HEADLINE_METRICS:
        before = getattr(baseline, attribute)
        after = getattr(upgraded, attribute)
        lines.append(
            f"| {label} | {format_metric(before)} | {format_metric(after)} | {format_metric(after - before)} |"
        )
    lines.extend(["", "## Per-type span F1", ""])
    lines.append("| clause type | baseline | upgraded |")
    lines.append("| --- | ---: | ---: |")
    types = sorted(set(baseline.per_type_f1) | set(upgraded.per_type_f1))
    for clause_type in types:
        before = format_metric(baseline.per_type_f1.get(clause_type, 0.0))
        after = format_metric(upgraded.per_type_f1.get(clause_type, 0.0))
        lines.append(f"| {clause_type} | {before} | {after} |")
    lines.append("")
    return "\n".join(lines)


def report_to_json(report: EvalReport) -> str:
    """Stable JSON. No timestamps, so two runs of the same code match byte for byte."""

    payload = asdict(report)
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def suite_to_json(reports: dict[str, EvalReport]) -> str:
    """Stable JSON for every split. No timestamps."""

    payload = {
        "judge": "deterministic",
        "provider": "fake",
        "splits": {name: json.loads(report_to_json(report)) for name, report in reports.items()},
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def suite_to_markdown(reports: dict[str, EvalReport]) -> str:
    """Markdown with one section per split."""

    parts = ["# ArbiLens evaluation", ""]
    for name, report in reports.items():
        parts.append(f"## {name}")
        parts.append("")
        parts.append(render_markdown(report))
    return "\n".join(parts)


def write_suite(reports: dict[str, EvalReport], output_dir: Path) -> tuple[Path, Path]:
    """Write ``latest.json`` and ``latest.md`` for every split."""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "latest.json"
    markdown_path = directory / "latest.md"
    json_path.write_text(suite_to_json(reports), encoding="utf-8")
    markdown_path.write_text(suite_to_markdown(reports), encoding="utf-8")
    return json_path, markdown_path
