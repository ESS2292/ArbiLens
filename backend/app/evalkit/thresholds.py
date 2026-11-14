"""Regression thresholds for ``arbilens eval --check``."""

import json
from dataclasses import dataclass
from pathlib import Path

from app.evalkit.runner import EvalReport, StrategyScore

_HEADLINE = {
    "retrieval_recall_at_1",
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


def load_thresholds(path: Path) -> dict[str, Thresholds]:
    """Load per-split floors. ``min_delta_over_baseline`` may be empty."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("splits"), dict) or not raw["splits"]:
        raise ValueError(f"{path} must contain a non-empty splits object.")
    loaded: dict[str, Thresholds] = {}
    for name, body in raw["splits"].items():
        if not isinstance(body, dict):
            raise ValueError(f"{path} split {name} must be an object.")
        upgraded = _metric_map(body.get("upgraded"), path, f"{name}.upgraded")
        delta = _metric_map(
            body.get("min_delta_over_baseline", {}),
            path,
            f"{name}.min_delta_over_baseline",
            allow_empty=True,
        )
        loaded[str(name)] = Thresholds(upgraded=upgraded, min_delta_over_baseline=delta)
    return loaded


def suite_failures(reports: dict[str, EvalReport], thresholds: dict[str, Thresholds]) -> list[str]:
    """Failures across dev and held-out splits."""

    failures: list[str] = []
    for name, report in reports.items():
        if name not in thresholds:
            failures.append(f"{name}: no thresholds configured")
            continue
        failures.extend(f"{name}: {item}" for item in threshold_failures(report, thresholds[name]))
    return failures


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


def _metric_map(raw: object, path: Path, label: str, *, allow_empty: bool = False) -> dict[str, float]:
    if not isinstance(raw, dict) or (not raw and not allow_empty):
        raise ValueError(f"{path} is missing {label}.")
    parsed: dict[str, float] = {}
    for key, value in raw.items():
        if key not in _HEADLINE or isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"{path} has an invalid {label} entry: {key}")
        parsed[str(key)] = float(value)
    return parsed
