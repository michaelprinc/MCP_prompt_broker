# sklearn Toy Model

This miniature project demonstrates how to train and evaluate a `LinearRegression` model with scikit-learn's toy regression dataset. The script in `main.py` generates a synthetic regression dataset, splits it into training and test sets, fits the model, evaluates it with MSE and R2 score, and saves the trained model.

## Prerequisites

- Python 3.9+ (any version supported by scikit-learn works)
- `pip` for installing dependencies

Install the requirements into your environment:

```bash
pip install -r requirements.txt
```

## Running the script

From the project root run:

```bash
python main.py
```

The script will print the Mean Squared Error (MSE) and R2 score for the test set, followed by saving the model to `linear_regression_model.joblib`.

## Project structure

- `main.py`: entry point that generates the dataset, trains the Linear Regression model, evaluates it, and saves the model.
- `requirements.txt`: dependency list including `scikit-learn` and `joblib`.
- `linear_regression_model.joblib`: saved trained model (generated after running the script).

## What to expect

The run completes quickly on a typical laptop. The model should achieve a high R2 score (close to 1.0) on this simple toy dataset. Use the saved model for predictions or as a baseline for more complex regression tasks.

## Hyperparameter tuning with Optuna

A simple Optuna-based tuner is provided in `optuna_tune.py`. It runs trials to optimize a `RandomForestRegressor` inside a pipeline with `StandardScaler` and saves the best model and parameters.

Run the tuner from this folder:

```bash
pip install -r requirements.txt
python optuna_tune.py --n-trials 50 --output-model optuna_best_model.joblib --output-params optuna_best_params.json
```

This will run the specified number of trials (default 50), train the final model on the full toy dataset, and save the results.

