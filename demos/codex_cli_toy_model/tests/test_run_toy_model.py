import subprocess
import sys
import tempfile
from pathlib import Path


def test_runs_and_writes_outputs():
    runner = [sys.executable, str(Path(__file__).parents[2] / "run_toy_model.py")]
    with tempfile.TemporaryDirectory() as td:
        res = subprocess.run(runner + ["--outdir", td, "--dataset", "iris", "--model", "logistic"], capture_output=True, text=True)
        assert res.returncode == 0, f"Script failed: {res.stderr}"
        p = Path(td)
        assert (p / "model.joblib").exists()
        assert (p / "metrics.json").exists()
