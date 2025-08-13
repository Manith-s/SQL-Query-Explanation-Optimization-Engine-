import os
import json
from pathlib import Path
import pytest


@pytest.mark.skipif(os.getenv("RUN_DB_TESTS") != "1", reason="bench gated by RUN_DB_TESTS")
def test_bench_reports_exist():
    # Ensure reports exist and have expected keys
    base = Path("bench/report")
    assert (base / "report.json").exists()
    assert (base / "report.csv").exists()
    data = json.loads((base / "report.json").read_text(encoding="utf-8"))
    assert "cases" in data


