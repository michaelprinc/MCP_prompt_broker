from pathlib import Path
import importlib.util
import sys


def _import_train_module():
    # import module by file path to avoid relying on package import paths
    mod_path = Path(__file__).resolve().parent.parent / "train_classification.py"
    spec = importlib.util.spec_from_file_location("train_classification", str(mod_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_train_classification_creates_model(tmp_path):
    mod = _import_train_module()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    # call main with args: use make_classification and output-dir
    mod.main(["--dataset", "make_classification", "--output-dir", str(out_dir)])

    model_file = out_dir / "models" / "classification_model.joblib"
    assert model_file.exists(), f"Expected model file at {model_file}"
