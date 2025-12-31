"""Train a LinearRegression model on a toy regression dataset and save it."""
from pathlib import Path

import joblib
from sklearn.datasets import make_regression
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


def main() -> None:
    features, targets = make_regression(
        n_samples=300,
        n_features=4,
        noise=12.0,
        random_state=42,
    )

    train_features, test_features, train_labels, test_labels = train_test_split(
        features,
        targets,
        test_size=0.2,
        random_state=42,
    )

    model = LinearRegression()
    model.fit(train_features, train_labels)

    predictions = model.predict(test_features)
    mse = mean_squared_error(test_labels, predictions)
    r2 = r2_score(test_labels, predictions)

    print(f"Mean squared error: {mse:.2f}")
    print(f"R2 score: {r2:.3f}")

    model_path = Path("linear_regression_model.joblib")
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path.resolve()}")


if __name__ == "__main__":
    main()
