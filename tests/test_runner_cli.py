import json
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


def test_triage_writes_json_file_with_dash_o(tmp_path: Path):
    out = tmp_path / "triage_out.json"
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "triage.runner",
            str(REPO / "data" / "sample_messages.json"),
            "-o",
            str(out),
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert r.stdout.strip() == ""
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "results" in data and isinstance(data["results"], list)
    assert len(data["results"]) > 0
    first = data["results"][0]
    assert "input" in first and isinstance(first["input"], dict)
    assert "output" in first and isinstance(first["output"], dict)
    first_out = first["output"]
    assert "urgency_score" in first_out
    assert isinstance(first_out["urgency_score"], int)
    assert 0 <= first_out["urgency_score"] <= 100
    assert "priority_bucket" in first_out
    assert first_out["priority_bucket"] in {"low", "medium", "high", "critical"}
    assert "summary" in data
    assert "accuracy" in data["summary"]
    assert 0.0 <= data["summary"]["accuracy"] <= 1.0
