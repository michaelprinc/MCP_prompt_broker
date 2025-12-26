# sklearn Toy Model

This miniature project demonstrates how to train and evaluate a `RandomForestClassifier` with scikit-learn's classic Iris dataset. The script in `main.py` loads the data, splits it into training and test sets, fits the model, and reports accuracy along with a detailed classification report so you can inspect per-class performance.

## Prerequisites

- Python 3.9+ (any version supported by scikit-learn works)
- `pip` for installing dependencies

Install the lone requirement into your environment:

```bash
pip install -r requirements.txt
```

## Running the script

From the project root run:

```bash
python main.py
```

The script will print the overall test accuracy followed by a scikit-learn classification report that includes precision, recall, f1-score, and support for each Iris species.

## Project structure

- `main.py`: entry point that loads the dataset, trains the Random Forest model, and prints metrics.
- `requirements.txt`: minimal dependency list (`scikit-learn`).

## What to expect

The run completes in under a second on a typical laptop. Because the dataset is small, no GPU is required. Use the output metrics to verify that the toy model is learning properly or as a baseline for experimenting with other models, hyperparameters, or datasets.

