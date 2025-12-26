"""Train a RandomForestClassifier on the iris dataset and report accuracy metrics."""
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


def main() -> None:
    iris = load_iris()
    features, labels = iris.data, iris.target

    train_features, test_features, train_labels, test_labels = train_test_split(
        features,
        labels,
        test_size=0.2,
        stratify=labels,
        random_state=42,
    )

    model = RandomForestClassifier(random_state=42)
    model.fit(train_features, train_labels)

    predictions = model.predict(test_features)
    accuracy = accuracy_score(test_labels, predictions)
    report = classification_report(test_labels, predictions, target_names=iris.target_names)

    print(f"Accuracy: {accuracy:.4f}")
    print("Classification report:\n")
    print(report)


if __name__ == "__main__":
    main()
