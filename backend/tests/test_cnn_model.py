import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.skin_model import (
    classification_metrics,
    confusion_matrix,
    extract_conv_features_pil,
    normalize_confusion_matrix,
    predict_proba_batch,
    train_conv_softmax_classifier,
)


def test_classification_metrics_report():
    y_true = np.array(["dry", "dry", "oily", "normal", "normal"])
    y_pred = np.array(["dry", "oily", "oily", "normal", "dry"])

    report = classification_metrics(y_true, y_pred, ["dry", "oily", "normal"])

    assert report["accuracy"] == 0.6
    assert report["macro_precision"] == 0.6666666666666666
    assert report["macro_recall"] == 0.6666666666666666
    assert report["macro_f1"] == 0.611111111111111
    assert report["per_class"]["dry"]["precision"] == 0.5
    assert report["per_class"]["dry"]["recall"] == 0.5
    assert report["per_class"]["dry"]["f1"] == 0.5


def test_confusion_matrix_uses_label_order_and_handles_zero_support():
    labels = ["dry", "oily", "normal"]
    y_true = np.array(["normal", "dry", "dry"])
    y_pred = np.array(["dry", "dry", "normal"])

    matrix = confusion_matrix(y_true, y_pred, labels)
    normalized = normalize_confusion_matrix(matrix)

    np.testing.assert_array_equal(
        matrix,
        np.array([[1, 0, 1], [0, 0, 0], [1, 0, 0]]),
    )
    np.testing.assert_array_equal(
        normalized,
        np.array([[0.5, 0.0, 0.5], [0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
    )


def test_conv_feature_extractor_and_classifier_smoke():
    images = [
        Image.new("RGB", (64, 64), color=(255, 0, 0)),
        Image.new("RGB", (64, 64), color=(0, 255, 0)),
        Image.new("RGB", (64, 64), color=(0, 0, 255)),
        Image.new("RGB", (64, 64), color=(255, 255, 0)),
    ]
    labels = ["dry", "oily", "dry", "normal"]
    class_labels = ["dry", "oily", "normal"]

    features = [extract_conv_features_pil(img) for img in images]
    model = train_conv_softmax_classifier(features, labels, class_labels, epochs=10, lr=0.05)
    probs = predict_proba_batch(model, features)

    assert probs.shape == (len(images), len(class_labels))
    assert probs.shape[1] == 3
    assert probs.sum(axis=1).shape[0] == len(images)


def test_fit_training_phase_continues_epoch_counter(monkeypatch):
    import ml.train_skin_model as train_skin_model

    calls = []

    class DummyModel:
        def fit(self, *args, **kwargs):
            calls.append(kwargs.copy())

    class DummyDataset:
        pass

    model = DummyModel()
    train_skin_model._fit_training_phase(
        model,
        DummyDataset(),
        DummyDataset(),
        epochs=14,
        initial_epoch=10,
        class_weight=None,
        callbacks=[],
        verbose=1,
    )

    assert calls[0]["epochs"] == 14
    assert calls[0]["initial_epoch"] == 10
