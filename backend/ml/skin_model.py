"""SKINSIGHT v2 — Skin predictor with a lightweight CNN-style classifier."""

from __future__ import annotations

import io
import logging
import pickle
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

try:
    import tensorflow as tf
except Exception:  # pragma: no cover - optional dependency
    tf = None

logger = logging.getLogger(__name__)
CLASSES = ["oily", "dry", "normal"]
MODEL_PATH = Path(__file__).parent / "skin_type_classifier.pkl"
KERAS_MODEL_PATH = Path(__file__).parent / "skin_type_classifier.keras"


def _tensorflow_available() -> bool:
    return tf is not None


def _train_default_model() -> dict | None:
    """Train a fallback classifier from the bundled dataset if the artifact is missing."""
    dataset_root = Path(__file__).resolve().parents[2] / "datasets"
    train_root = dataset_root / "train"
    if not train_root.exists():
        logger.warning("Dataset train folder not found at %s", train_root)
        return None

    try:
        from train_skin_model import load_split, train_conv_softmax_classifier

        labels = ["oily", "dry", "normal"]
        x_train, y_train = load_split(train_root, labels)
        model = train_conv_softmax_classifier(x_train, y_train, labels, epochs=15, lr=0.05)
        artifact = {
            **model,
            "valid_accuracy": 0.0,
            "test_accuracy": 0.0,
            "feature_version": "v1",
        }
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with MODEL_PATH.open("wb") as fp:
            pickle.dump(artifact, fp)
        logger.info("Trained fallback classifier and saved it to %s", MODEL_PATH)
        return artifact
    except Exception as exc:
        logger.warning("Fallback training failed: %s", exc)
        return None


def _mock(image_bytes: bytes) -> dict:
    import random

    random.seed(len(image_bytes) % 97)
    raw = [random.uniform(0.05, 0.9) for _ in CLASSES]
    raw[len(image_bytes) % len(CLASSES)] *= 2.8
    total = sum(raw)
    scores = {c: round(r / total, 4) for c, r in zip(CLASSES, raw)}
    condition = max(scores, key=scores.get)
    return {
        "condition": condition,
        "confidence": scores[condition],
        "all_scores": scores,
        "using_mock": True,
        "error": None,
    }


def extract_features_pil(image: Image.Image) -> np.ndarray:
    """Extract compact color and texture features from an RGB image."""
    rgb = image.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR)
    arr = np.asarray(rgb, dtype=np.float32) / 255.0

    channel_means = arr.mean(axis=(0, 1))
    channel_stds = arr.std(axis=(0, 1))

    luminance = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    lum_percentiles = np.percentile(luminance, [10, 25, 50, 75, 90])

    hist_features = []
    for channel in range(3):
        hist, _ = np.histogram(arr[:, :, channel], bins=16, range=(0.0, 1.0), density=True)
        hist_features.append(hist)

    grad_x = np.abs(np.diff(luminance, axis=1)).mean()
    grad_y = np.abs(np.diff(luminance, axis=0)).mean()

    small_gray = np.asarray(
        rgb.convert("L").resize((16, 16), Image.Resampling.BILINEAR),
        dtype=np.float32,
    ) / 255.0

    feature_vector = np.concatenate(
        [
            channel_means,
            channel_stds,
            lum_percentiles,
            np.concatenate(hist_features),
            np.array([grad_x, grad_y], dtype=np.float32),
            small_gray.ravel(),
        ]
    )
    return feature_vector.astype(np.float32)


def _default_conv_filters(num_filters: int = 4) -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.normal(0.0, 0.12, size=(num_filters, 3, 3, 3)).astype(np.float32)


def _conv2d(images: np.ndarray, filters: np.ndarray) -> np.ndarray:
    batch_size, height, width, channels = images.shape
    num_filters, kernel_h, kernel_w, in_channels = filters.shape
    if channels != in_channels:
        raise ValueError("Input channels do not match filter shape")

    padding = kernel_h // 2
    padded = np.pad(images, ((0, 0), (padding, padding), (padding, padding), (0, 0)), mode="constant")

    output = np.zeros((batch_size, height, width, num_filters), dtype=np.float32)
    for n in range(batch_size):
        for f in range(num_filters):
            for i in range(height):
                for j in range(width):
                    patch = padded[n, i : i + kernel_h, j : j + kernel_w, :]
                    output[n, i, j, f] = np.sum(patch * filters[f])
    return output


def _max_pool2d(x: np.ndarray, pool_size: int = 2) -> np.ndarray:
    batch, height, width, channels = x.shape
    pooled_height = height // pool_size
    pooled_width = width // pool_size
    pooled = np.zeros((batch, pooled_height, pooled_width, channels), dtype=np.float32)
    for n in range(batch):
        for c in range(channels):
            for i in range(pooled_height):
                for j in range(pooled_width):
                    region = x[n, i * pool_size : (i + 1) * pool_size, j * pool_size : (j + 1) * pool_size, c]
                    pooled[n, i, j, c] = np.max(region)
    return pooled


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / (np.sum(exp, axis=-1, keepdims=True) + 1e-12)


def extract_conv_features_pil(image: Image.Image, filters: np.ndarray | None = None) -> np.ndarray:
    """Extract a lightweight CNN-style feature vector from an RGB image."""
    rgb = image.convert("RGB").resize((32, 32), Image.Resampling.BILINEAR)
    arr = np.asarray(rgb, dtype=np.float32) / 255.0
    arr = arr[None, ...]

    if filters is None:
        filters = _default_conv_filters()

    conv_out = _conv2d(arr, filters)
    relu_out = np.maximum(conv_out, 0.0)
    pooled = _max_pool2d(relu_out, pool_size=2)
    pooled = pooled[0]

    channel_means = pooled.mean(axis=(0, 1))
    channel_stds = pooled.std(axis=(0, 1))
    return np.concatenate([channel_means, channel_stds]).astype(np.float32)


def train_conv_softmax_classifier(
    features: list[np.ndarray] | np.ndarray,
    labels: list[str] | np.ndarray,
    class_labels: list[str],
    epochs: int = 20,
    lr: float = 0.05,
) -> dict:
    """Train a small dense softmax classifier on top of CNN-style features."""
    x = np.asarray(features, dtype=np.float32)
    if x.ndim == 1:
        x = x[None, :]

    y = np.asarray(labels)
    label_to_idx = {label: idx for idx, label in enumerate(class_labels)}
    y_idx = np.array([label_to_idx[label] for label in y], dtype=np.int32)

    mean = x.mean(axis=0).astype(np.float32)
    std = (x.std(axis=0) + 1e-6).astype(np.float32)
    x_scaled = ((x - mean) / std).astype(np.float32)

    num_features = x_scaled.shape[1]
    num_classes = len(class_labels)
    weights = np.zeros((num_features, num_classes), dtype=np.float32)
    bias = np.zeros((num_classes,), dtype=np.float32)

    for _ in range(int(epochs)):
        logits = x_scaled @ weights + bias
        probs = _softmax(logits)
        one_hot = np.zeros_like(probs)
        one_hot[np.arange(len(y_idx)), y_idx] = 1.0

        error = probs - one_hot
        grad_w = x_scaled.T @ error / max(1, len(y_idx))
        grad_b = error.mean(axis=0)

        weights -= lr * grad_w
        bias -= lr * grad_b

    return {
        "model_type": "conv_softmax",
        "class_labels": list(class_labels),
        "weights": weights.astype(np.float32),
        "bias": bias.astype(np.float32),
        "feature_mean": mean.astype(np.float32),
        "feature_std": std.astype(np.float32),
        "filters": _default_conv_filters().astype(np.float32),
    }


def _load_efficientnetv2_model(model_path: Path):
    if not _tensorflow_available():
        raise RuntimeError("TensorFlow is required to load an EfficientNetV2 model artifact.")
    if not model_path.exists():
        raise FileNotFoundError(f"EfficientNetV2 model file not found: {model_path}")
    return tf.keras.models.load_model(model_path)


def predict_proba_batch(model: dict, x: np.ndarray | list[np.ndarray]) -> np.ndarray:
    if model.get("model_type") != "conv_softmax":
        raise RuntimeError("This helper expects a conv_softmax model artifact.")

    if isinstance(x, list):
        x_arr = np.asarray([np.asarray(item, dtype=np.float32) for item in x])
    else:
        x_arr = np.asarray(x, dtype=np.float32)

    if x_arr.ndim == 1:
        x_arr = x_arr[None, :]

    mean = model["feature_mean"]
    std = model["feature_std"]
    x_scaled = ((x_arr - mean) / std).astype(np.float32)
    logits = x_scaled @ model["weights"] + model["bias"]
    return _softmax(logits).astype(np.float32)


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, labels: list[str]) -> dict:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    if len(y_true) == 0:
        empty = {label: {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0} for label in labels}
        return {
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "per_class": empty,
        }

    accuracy = float((y_true == y_pred).sum() / len(y_true))
    per_class: dict[str, dict[str, float | int]] = {}
    precisions: list[float] = []
    recalls: list[float] = []
    f1_scores: list[float] = []

    for label in labels:
        actual = y_true == label
        predicted = y_pred == label
        tp = int(np.logical_and(actual, predicted).sum())
        fp = int(np.logical_and(~actual, predicted).sum())
        fn = int(np.logical_and(actual, ~predicted).sum())

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)
        per_class[label] = {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "support": int(actual.sum()),
            "accuracy": float((y_pred[actual] == label).sum() / actual.sum()) if actual.any() else 0.0,
        }

    macro_precision = float(np.mean(precisions)) if precisions else 0.0
    macro_recall = float(np.mean(recalls)) if recalls else 0.0
    macro_f1 = float(np.mean(f1_scores)) if f1_scores else 0.0
    return {
        "accuracy": accuracy,
        "precision": macro_precision,
        "recall": macro_recall,
        "f1": macro_f1,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "per_class": per_class,
    }


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, labels: list[str]) -> np.ndarray:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    if y_true.shape != y_pred.shape:
        raise ValueError("y_true and y_pred must have the same shape")

    label_to_index = {label: index for index, label in enumerate(labels)}
    matrix = np.zeros((len(labels), len(labels)), dtype=np.int64)
    for actual, predicted in zip(y_true, y_pred):
        if actual not in label_to_index or predicted not in label_to_index:
            raise ValueError("y_true and y_pred must contain only the configured labels")
        matrix[label_to_index[actual], label_to_index[predicted]] += 1
    return matrix


def normalize_confusion_matrix(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float64)
    row_totals = matrix.sum(axis=1, keepdims=True)
    return np.divide(matrix, row_totals, out=np.zeros_like(matrix), where=row_totals != 0)


class SkinPredictor:
    def __init__(self):
        self.model_artifact = None
        self.class_labels = []
        self.keras_model = None
        model_file_existed = MODEL_PATH.exists()
        try:
            if MODEL_PATH.exists():
                with MODEL_PATH.open("rb") as fp:
                    artifact = pickle.load(fp)

                if artifact.get("model_type") == "conv_softmax":
                    weights = artifact.get("weights")
                    feature_mean = artifact.get("feature_mean")
                    feature_std = artifact.get("feature_std")
                    if weights is None or feature_mean is None or feature_std is None:
                        raise ValueError("Incomplete conv_softmax artifact")
                    if np.asarray(feature_mean).shape[-1] != np.asarray(weights).shape[0]:
                        raise ValueError("Feature dimension mismatch in model artifact")
                elif artifact.get("model_type") == "efficientnetv2":
                    model_path = Path(artifact.get("keras_model_path") or KERAS_MODEL_PATH)
                    if not model_path.is_absolute():
                        model_path = MODEL_PATH.parent / model_path
                    self.keras_model = _load_efficientnetv2_model(model_path)
                    if self.keras_model.output_shape[-1] != len(artifact.get("class_labels", [])):
                        raise ValueError("Class count mismatch in EfficientNetV2 artifact")

                self.model_artifact = artifact
                self.class_labels = list(artifact.get("class_labels", []))
                logger.info("Loaded trained skin type classifier from %s", MODEL_PATH)
        except Exception as exc:
            logger.warning("Model load failed: %s", exc)
            self.model_artifact = None
            self.class_labels = []
            self.keras_model = None

        if self.model_artifact is None and not model_file_existed:
            fallback = _train_default_model()
            if fallback is not None:
                self.model_artifact = fallback
                self.class_labels = list(fallback.get("class_labels", []))

    def _predict_proba(self, features: np.ndarray) -> np.ndarray:
        if self.model_artifact.get("model_type") == "knn":
            k = int(self.model_artifact["k"])
            x_train = self.model_artifact["x_train"]
            y_train = self.model_artifact["y_train"]
            mean = self.model_artifact["feature_mean"]
            std = self.model_artifact["feature_std"]

            row_scaled = ((features - mean) / std).astype(np.float32)
            dists = np.sum((x_train - row_scaled) ** 2, axis=1)
            nn_idx = np.argpartition(dists, min(k, len(dists) - 1))[:k]

            vote_weights = np.zeros(len(self.class_labels), dtype=np.float64)
            label_to_idx = {label: i for i, label in enumerate(self.class_labels)}
            for idx in nn_idx:
                label = y_train[idx]
                vote_weights[label_to_idx[label]] += 1.0 / (float(dists[idx]) + 1e-6)

            vote_weights /= vote_weights.sum() + 1e-12
            return vote_weights.astype(np.float32)

        if self.model_artifact.get("model_type") == "gaussian":
            means = self.model_artifact["means"]
            variances = self.model_artifact["variances"]
            priors = self.model_artifact["priors"]

            log_probs = []
            for label in self.class_labels:
                mu = means[label]
                var = variances[label]
                log_prior = np.log(priors[label] + 1e-12)
                ll = -0.5 * np.sum(np.log(2.0 * np.pi * var) + ((features - mu) ** 2) / var)
                log_probs.append(log_prior + ll)

            log_probs = np.array(log_probs, dtype=np.float64)
            log_probs -= np.max(log_probs)
            probs = np.exp(log_probs)
            probs /= probs.sum() + 1e-12
            return probs.astype(np.float32)

        if self.model_artifact.get("model_type") == "conv_softmax":
            mean = self.model_artifact["feature_mean"]
            std = self.model_artifact["feature_std"]
            weights = self.model_artifact["weights"]
            bias = self.model_artifact["bias"]
            row_scaled = ((features - mean) / std).astype(np.float32)
            logits = row_scaled @ weights + bias
            return _softmax(logits).astype(np.float32)

        raise RuntimeError("Unsupported model artifact type.")

    def _predict_proba_efficientnet(self, image: Image.Image) -> np.ndarray:
        if self.keras_model is None:
            raise RuntimeError("EfficientNetV2 model is not loaded.")

        image_size = self.model_artifact.get("image_size", [224, 224])
        width, height = int(image_size[0]), int(image_size[1])
        rgb = image.convert("RGB").resize((width, height), Image.Resampling.BILINEAR)
        arr = np.asarray(rgb, dtype=np.float32)[None, ...]
        probs = self.keras_model.predict(arr, verbose=0)
        return np.asarray(probs[0], dtype=np.float32)

    def predict(self, image_bytes: bytes) -> dict:
        if self.model_artifact is None:
            return _mock(image_bytes)

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            if self.model_artifact.get("model_type") == "efficientnetv2":
                probs = self._predict_proba_efficientnet(image)
            else:
                features = extract_conv_features_pil(image)
                probs = self._predict_proba(features)

            scores = {label: float(prob) for label, prob in zip(self.class_labels, probs)}

            all_scores = {c: 0.01 for c in CLASSES}
            for label, score in scores.items():
                if label in all_scores:
                    all_scores[label] = score

            total = sum(all_scores.values())
            all_scores = {k: round(v / total, 4) for k, v in all_scores.items()}

            condition = max(all_scores, key=all_scores.get)
            return {
                "condition": condition,
                "confidence": all_scores[condition],
                "all_scores": all_scores,
                "using_mock": False,
                "error": None,
            }
        except UnidentifiedImageError:
            return {
                "condition": "normal",
                "confidence": 0.0,
                "all_scores": {c: 0.0 for c in CLASSES},
                "using_mock": False,
                "error": "Invalid image format.",
            }
        except Exception as exc:
            logger.error("Inference error: %s", exc)
            return _mock(image_bytes)
