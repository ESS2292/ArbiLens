"""Command line for offline analysis and the evaluation gate.

``arbilens eval`` always uses the fake providers so the numbers do not depend
on network access. ``arbilens ask`` and ``arbilens analyze`` honor
``ARBILENS_LLM_PROVIDER`` and ``ARBILENS_EMBEDDING_PROVIDER``.
"""

import argparse
import sys
from pathlib import Path

from app.engine.errors import ProviderError
from app.engine.pipeline import analyze_document, ask_document
from app.engine.strategy import STRATEGIES
from app.evalkit.dataset import load_dataset
from app.evalkit.paths import default_labels_path, default_report_dir, default_thresholds_path
from app.evalkit.report import render_headline_table, write_suite
from app.evalkit.runner import EvalReport, run_evaluation
from app.evalkit.thresholds import load_thresholds, suite_failures


def main(argv: list[str] | None = None) -> int:
    """Run a subcommand. Returns a process exit code."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "eval":
            return _eval_command(args)
        if args.command == "ask":
            return _ask_command(args)
        if args.command == "analyze":
            return _analyze_command(args)
    except (FileNotFoundError, ValueError, ProviderError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    parser.error(f"unknown command {args.command}")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arbilens", description="Analyze contracts and run the offline eval.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    evaluate = subparsers.add_parser("eval", help="Compare baseline and upgraded retrieval on the labeled set.")
    evaluate.add_argument("--dataset", type=Path, default=None, help="Path to eval/data/labels.json.")
    evaluate.add_argument("--output-dir", type=Path, default=None, help="Where to write latest.json and latest.md.")
    evaluate.add_argument("--thresholds", type=Path, default=None, help="Threshold file used with --check.")
    evaluate.add_argument("--check", action="store_true", help="Exit 1 when the upgraded strategy regresses.")

    ask = subparsers.add_parser("ask", help="Answer one question with citations to exact character spans.")
    ask.add_argument("contract", type=Path)
    ask.add_argument("question")
    ask.add_argument("--strategy", choices=sorted(STRATEGIES), default="upgraded")

    analyze = subparsers.add_parser("analyze", help="Print clause tags and deterministic risk flags.")
    analyze.add_argument("contract", type=Path)
    analyze.add_argument("--strategy", choices=sorted(STRATEGIES), default="upgraded")
    return parser


def _eval_command(args: argparse.Namespace) -> int:
    labels = args.dataset if args.dataset is not None else default_labels_path()
    reports = _load_reports(labels)
    output_dir = args.output_dir if args.output_dir is not None else default_report_dir(labels)
    json_path, markdown_path = write_suite(reports, output_dir)
    for name, report in reports.items():
        print(f"split={name}")
        print(render_headline_table(report))
        print()
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")
    if not args.check:
        return 0
    thresholds_path = args.thresholds if args.thresholds is not None else default_thresholds_path(labels)
    failures = suite_failures(reports, load_thresholds(thresholds_path))
    if not failures:
        print("Thresholds: passed")
        return 0
    print("Thresholds: failed", file=sys.stderr)
    for failure in failures:
        print(f"- {failure}", file=sys.stderr)
    return 1


def _load_reports(labels: Path) -> dict[str, EvalReport]:
    reports = {"dev": run_evaluation(load_dataset(labels))}
    for name in ("tuning", "heldout"):
        path = labels.parent / f"{name}.json"
        if path.is_file():
            reports[name] = run_evaluation(load_dataset(path))
    return reports


def _ask_command(args: argparse.Namespace) -> int:
    text = _read_contract(args.contract)
    answer = ask_document(text, args.question, STRATEGIES[args.strategy])
    print(answer.answer)
    print(f"Grounded: {'yes' if answer.grounded else 'no'}")
    print(f"Provider: {answer.provider}")
    print(f"Strategy: {answer.strategy}")
    if not answer.citations:
        print("Citations: none")
        return 0
    print("Citations:")
    for citation in answer.citations:
        title = citation.section_title or "(no heading)"
        print(f"- chars {citation.char_start}-{citation.char_end}  {title}")
        print(f"  {citation.text}")
    return 0


def _analyze_command(args: argparse.Namespace) -> int:
    text = _read_contract(args.contract)
    analysis = analyze_document(text, STRATEGIES[args.strategy])
    print(f"Strategy: {args.strategy}")
    print("Clauses:")
    if not analysis.clauses:
        print("- none")
    for clause in analysis.clauses:
        title = clause.title or "(no heading)"
        print(f"- {clause.clause_type}  chars {clause.char_start}-{clause.char_end}  {title}")
    print("Risks:")
    if not analysis.risks:
        print("- none")
    for risk in analysis.risks:
        print(f"- {risk.rule_code}  {risk.severity}  score {risk.score}")
    return 0


def _read_contract(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Contract file not found: {path}")
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
