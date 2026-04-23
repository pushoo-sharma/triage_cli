import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_eval_subcommand_exit_zero_on_perfect_sample():
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "triage.runner",
            "eval",
            str(REPO / "data" / "sample_messages.json"),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    out = r.stdout.lower()
    assert "all_labeled_match" in out and "true" in out
    assert "accuracy" in out


def test_eval_subcommand_exit_one_on_mismatch():
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "triage.runner",
            "eval",
            str(REPO / "tests" / "fixtures" / "eval_mismatch.json"),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1
