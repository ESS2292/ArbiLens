"""Locate the labeled dataset from the repository root or an explicit path."""

import os
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    """Walk parents until ``eval/data/labels.json`` is found."""

    cursor = (start or Path.cwd()).resolve()
    candidates = [cursor, *cursor.parents]
    for candidate in candidates:
        if (candidate / "eval" / "data" / "labels.json").is_file():
            return candidate
    raise FileNotFoundError("Could not find eval/data/labels.json. Run from the ArbiLens repo root or pass --dataset.")


def default_labels_path() -> Path:
    """Dataset path from ``ARBILENS_DATASET`` or the repository checkout."""

    override = os.environ.get("ARBILENS_DATASET")
    if override:
        return Path(override)
    return find_repo_root() / "eval" / "data" / "labels.json"


def default_report_dir(labels_path: Path | None = None) -> Path:
    """``eval/reports`` next to the dataset, when the dataset lives in the repo."""

    labels = labels_path if labels_path is not None else default_labels_path()
    return labels.resolve().parent.parent / "reports"


def default_thresholds_path(labels_path: Path | None = None) -> Path:
    """``eval/thresholds.json`` next to the dataset directory."""

    labels = labels_path if labels_path is not None else default_labels_path()
    return labels.resolve().parent.parent / "thresholds.json"
