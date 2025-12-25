#!/usr/bin/env python3
"""Simple CLI to train and evaluate a scikit-learn toy classification task.

Usage:
  python run_toy_model.py --dataset iris --model random_forest --outdir outputs

This script is intentionally small and dependency-light so it can be used
as a reproducible example for the Codex CLI integration demo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
from sklearn import datasets
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


def load_toy(dataset: str) -> Tuple[np.ndarray, np.ndarray, list]:
    if dataset == "iris":
        data = datasets.load_iris()
    elif dataset == "digits":
        data = datasets.load_digits()
    elif dataset == "wine":
        data = datasets.load_wine()
    else:
        raise ValueError(f"Unknown dataset: {dataset}")
    return data.data, data.target, list(map(str, data.target_names)) if hasattr(data, "target_names") else []


def build_model(name: str, random_state: int = 42):
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=100, random_state=random_state)
    elif name == "logistic":
        return LogisticRegression(max_iter=500, random_state=random_state)
    else:
        raise ValueError(f"Unknown model: {name}")


def run(dataset: str, model_name: str, outdir: str, test_size: float, random_state: int):
    X, y, target_names = load_toy(dataset)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y if len(np.unique(y)) > 1 else None
    )

    model = build_model(model_name, random_state=random_state)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    acc = float(accuracy_score(y_test, preds))
    report = classification_report(y_test, preds, target_names=target_names if target_names else None, output_dict=True)

    out_path = Path(outdir)
    out_path.mkdir(parents=True, exist_ok=True)

    # save model and metrics
    joblib.dump(model, out_path / "model.joblib")
    metrics = {"accuracy": acc, "report": report}
    with open(out_path / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    # summary to stdout
    print(f"Dataset: {dataset}")
    print(f"Model: {model_name}")
    print(f"Test size: {test_size}")
    print(f"Accuracy: {acc:.4f}")
    print(f"Saved model -> {out_path / 'model.joblib'}")
    print(f"Saved metrics -> {out_path / 'metrics.json'}")


def main():
    parser = argparse.ArgumentParser(description="Train a toy classifier and save metrics.")
    parser.add_argument("--dataset", default="iris", choices=["iris", "digits", "wine"], help="Which sklearn toy dataset to use.")
    parser.add_argument("--model", dest="model_name", default="random_forest", choices=["random_forest", "logistic"], help="Model type.")
    parser.add_argument("--outdir", default="outputs", help="Output directory to save model and metrics.")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test set fraction.")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed.")
    args = parser.parse_args()

    run(args.dataset, args.model_name, args.outdir, args.test_size, args.random_state)


if __name__ == "__main__":
    main()
