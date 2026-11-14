"""Regression thresholds for ``arbilens eval --check``."""

import json
from dataclasses import dataclass
from pathlib import Path

from app.evalkit.runner import EvalReport, StrategyScore

_HEADLINE = {
    "retrieval_recall_at_5",
    "retrieval_mrr",
    "extraction_micro_f1",
    "extraction_type_micro_f1",
    "citation_faithfulness",
    "offset_integrity",
    "risk_flag_accuracy",
    "risk_flag_micro_f1",
}


@dataclass(frozen=True)
class Thresholds:
    """Floors on the upgraded strategy and required gaps over the baseline."""

    upgraded: dict[str, float]
    min_delta_over_baseline: dict[str, float]


def load_thresholds(path: Path) -> Thresholds:
    """Load the checked-in threshold file."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object.")
    upgraded = _metric_map(raw.get("upgraded"), path, "upgraded")
    delta = _metric_map(raw.get("min_delta_over_baseline"), path, "min_delta_over_baseline")
    return Thresholds(upgraded=upgraded, min_delta_over_baseline=delta)


def threshold_failures(report: EvalReport, thresholds: Thresholds) -> list[str]:
    """Return human-readable failures. An empty list means the gate passed.

    Comparisons use three decimal places, the same precision as the printed table.
    """

    if "upgraded" not in report.strategies or "baseline" not in report.strategies:
        return ["report is missing baseline or upgraded"]
    upgraded = report.strategies["upgraded"]
    baseline = report.strategies["baseline"]
    failures: list[str] = []
    for metric, floor in thresholds.upgraded.items():
        actual = _metric(upgraded, metric)
        if round(actual, 3) < floor:
            failures.append(f"upgraded {metric}={actual:.3f} is below {floor:.3f}")
    for metric, required in thresholds.min_delta_over_baseline.items():
        gap = _metric(upgraded, metric) - _metric(baseline, metric)
        if round(gap, 3) < required:
            failures.append(f"delta {metric}={gap:.3f} is below {required:.3f}")
    return failures


def _metric(score: StrategyScore, name: str) -> float:
    if name not in _HEADLINE:
        raise ValueError(f"Unknown metric {name}.")
    value = getattr(score, name)
    if not isinstance(value, float):
        raise ValueError(f"Metric {name} is not a float.")
    return value


def _metric_map(raw: object, path: Path, label: str) -> dict[str, float]:
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"{path} is missing {label}.")
    parsed: dict[str, float] = {}
    for key, value in raw.items():
        if key not in _HEADLINE or isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"{path} has an invalid {label} entry: {key}")
        parsed[str(key)] = float(value)
    return parsed
