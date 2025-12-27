from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Tuple

import joblib
import optuna
from sklearn.datasets import make_regression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def load_data(n_samples: int = 300, n_features: int = 4, noise: float = 12.0, seed: int = 42) -> Tuple[Any, Any]:
    X, y = make_regression(n_samples=n_samples, n_features=n_features, noise=noise, random_state=seed)
    return X, y


def _suggest_max_features(trial: optuna.Trial) -> Any:
    choice = trial.suggest_categorical("max_features_choice", ["sqrt", "log2", "float"])
    if choice == "float":
        return trial.suggest_float("max_features_float", 0.3, 1.0)
    return choice


def objective(trial: optuna.Trial, X: Any, y: Any, seed: int) -> float:
    max_features = _suggest_max_features(trial)

    params: Dict[str, Any] = {
        "n_estimators": trial.suggest_int("n_estimators", 50, 500),
        "max_depth": trial.suggest_categorical("max_depth", [None, *list(range(2, 31))]),
        "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        "max_features": max_features,
        "random_state": seed,
        "n_jobs": -1,
    }

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestRegressor(**{k: v for k, v in params.items() if k in RandomForestRegressor().get_params()})),
    ])

    # Use negative MSE from cross_val_score and convert to positive MSE
    scores = cross_val_score(pipeline, X, y, scoring="neg_mean_squared_error", cv=3, n_jobs=1)
    mean_mse = -float(scores.mean())

    # optuna minimizes the objective by default when study.direction='minimize'
    return mean_mse


def run_tuning(n_trials: int, seed: int, output_model: Path, output_params: Path) -> None:
    X, y = load_data(seed=seed)

    study = optuna.create_study(direction="minimize")
    func = lambda trial: objective(trial, X, y, seed)

    print(f"Starting Optuna study with {n_trials} trials...")
    study.optimize(func, n_trials=n_trials)

    print("Best trial:")
    print(study.best_trial.params)

    # Train final model on the full dataset with best params
    best_params = study.best_trial.params.copy()

    # If max_features stored as float choice name, ensure correct key
    if "max_features_choice" in best_params:
        choice = best_params.pop("max_features_choice")
        if choice == "float":
            best_params["max_features"] = best_params.pop("max_features_float")
        else:
            best_params["max_features"] = choice

    # Map categorical max_depth if present
    if "max_depth" in best_params and best_params["max_depth"] == "None":
        best_params["max_depth"] = None

    # Ensure integer params are ints
    for k in ["n_estimators", "min_samples_split", "min_samples_leaf"]:
        if k in best_params:
            best_params[k] = int(best_params[k])

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("model", RandomForestRegressor(**{k: v for k, v in best_params.items() if k in RandomForestRegressor().get_params()})),
    ])

    model.fit(X, y)

    joblib.dump(model, output_model)
    print(f"Saved best model to {output_model}")

    # Save params
    with open(output_params, "w", encoding="utf-8") as fh:
        json.dump(best_params, fh, indent=2)
    print(f"Saved best params to {output_params}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optuna hyperparameter tuning for sklearn toy regression")
    parser.add_argument("--n-trials", type=int, default=50, help="Number of Optuna trials")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-model", type=Path, default=Path("optuna_best_model.joblib"), help="Path to save best model")
    parser.add_argument("--output-params", type=Path, default=Path("optuna_best_params.json"), help="Path to save best params JSON")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_tuning(n_trials=args.n_trials, seed=args.seed, output_model=args.output_model, output_params=args.output_params)
