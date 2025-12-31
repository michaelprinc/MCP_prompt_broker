"""Train a toy classifier (Iris or synthetic) and save the model."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import joblib
from sklearn.datasets import load_iris, make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


def _load_data(dataset_name: str, random_state: int = 42):
    if dataset_name == "iris":
        data = load_iris()
        return data.data, data.target
    if dataset_name == "make_classification":
        X, y = make_classification(
            n_samples=200,
            n_features=6,
            n_informative=4,
            n_redundant=0,
            n_classes=3,
            random_state=random_state,
        )
        return X, y
    raise ValueError(f"Unsupported dataset: {dataset_name}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a toy classifier.")
    parser.add_argument(
        "--dataset",
        choices=["iris", "make_classification"],
        default="iris",
        help="Dataset to use for training.",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where to save the model (default: current dir).",
    )
    parser.add_argument("--random-state", type=int, default=42)
    return parser


def train_and_save(dataset: str, output_dir: Path, random_state: int = 42) -> float:
    X, y = _load_data(dataset, random_state=random_state)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state
    )

    clf = RandomForestClassifier(n_estimators=100, random_state=random_state)
    clf.fit(X_train, y_train)

    preds = clf.predict(X_test)
    acc = float(accuracy_score(y_test, preds))

    model_dir = Path(output_dir) / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "classification_model.joblib"
    joblib.dump(clf, model_path)

    print(f"Accuracy: {acc:.4f}")
    print(f"Model saved to {model_path.resolve()}")
    return acc


def main(args: Sequence[str] | None = None):
    parser = build_arg_parser()
    parsed = parser.parse_args(args=args)
    output_dir = Path(parsed.output_dir)
    return train_and_save(parsed.dataset, output_dir, random_state=parsed.random_state)


if __name__ == "__main__":
    main()
