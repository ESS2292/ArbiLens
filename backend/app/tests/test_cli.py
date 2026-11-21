"""CLI coverage for eval, ask, and analyze."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.cli import main
from app.evalkit.paths import find_repo_root

ROOT = find_repo_root(Path(__file__))
CONTRACT = ROOT / "eval" / "data" / "contracts" / "harbor-msa.txt"


def test_ask_and_analyze_print_offsets_and_flags(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ask", str(CONTRACT), "Which ceiling bounds monetary exposure?", "--strategy", "upgraded"]) == 0
    ask_output = capsys.readouterr().out
    assert "unlimited" in ask_output
    assert "Grounded: yes" in ask_output
    assert "Provider: fake" in ask_output
    assert "chars " in ask_output

    assert main(["analyze", str(CONTRACT), "--strategy", "upgraded"]) == 0
    analyze_output = capsys.readouterr().out
    assert "uncapped_liability" in analyze_output
    assert "indemnification" in analyze_output


def test_eval_writes_a_report_and_passes_the_gate(tmp_path: Path) -> None:
    output = tmp_path / "reports"
    code = main(
        [
            "eval",
            "--dataset",
            str(ROOT / "eval" / "data" / "labels.json"),
            "--output-dir",
            str(output),
            "--thresholds",
            str(ROOT / "eval" / "thresholds.json"),
            "--check",
        ]
    )
    assert code == 0
    saved = json.loads((output / "latest.json").read_text(encoding="utf-8"))
    assert saved["provider"] == "fake"
    assert saved["judge"] == "deterministic"
    assert saved["splits"]["dev"]["strategies"]["upgraded"]["citation_faithfulness"] == 1
    assert saved["splits"]["heldout"]["strategies"]["upgraded"]["extraction_micro_f1"] < 1
    assert "retrieval recall@5" in (output / "latest.md").read_text(encoding="utf-8")


def test_cli_reports_a_missing_contract() -> None:
    assert main(["ask", "missing-contract.txt", "What is the cap?"]) == 1


def test_module_entrypoint_matches_the_library(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli",
            "eval",
            "--dataset",
            str(ROOT / "eval" / "data" / "labels.json"),
            "--output-dir",
            str(tmp_path),
            "--check",
            "--thresholds",
            str(ROOT / "eval" / "thresholds.json"),
        ],
        cwd=ROOT / "backend",
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "provider=fake" in completed.stdout
    assert "Thresholds: passed" in completed.stdout
