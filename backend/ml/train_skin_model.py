"""Train a skin type classifier from datasets."""

from __future__ import annotations

import argparse
import pickle
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

try:
    import tensorflow as tf
except Exception:  # pragma: no cover - optional dependency
    tf = None

try:
    from .skin_model import (
        KERAS_MODEL_PATH,
        MODEL_PATH,
        classification_metrics,
        confusion_matrix,
        extract_conv_features_pil,
        normalize_confusion_matrix,
        train_conv_softmax_classifier,
    )
except ImportError:  # pragma: no cover - support direct script execution
    from skin_model import (
        KERAS_MODEL_PATH,
        MODEL_PATH,
        classification_metrics,
        confusion_matrix,
        extract_conv_features_pil,
        normalize_confusion_matrix,
        train_conv_softmax_classifier,
    )

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def iter_images(folder: Path):
    seen: set[Path] = set()
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS and path not in seen:
            seen.add(path)
            yield path


def load_split(split_root: Path, labels: list[str]) -> tuple[np.ndarray, np.ndarray]:
    features = []
    targets = []

    for label in labels:
        class_dir = split_root / label
        if not class_dir.exists():
            continue

        for img_path in iter_images(class_dir):
            try:
                img = Image.open(img_path).convert("RGB")
                fv = extract_conv_features_pil(img)
                features.append(fv)
                targets.append(label)
            except (UnidentifiedImageError, OSError):
                continue

    if not features:
        raise RuntimeError(f"No images loaded from {split_root}")

    return np.vstack(features), np.array(targets)


def _require_tensorflow() -> None:
    if tf is None:
        raise RuntimeError(
            "TensorFlow is required for EfficientNetV2 training. Install backend requirements including tensorflow."
        )


def _count_images(split_root: Path, labels: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in labels:
        class_dir = split_root / label
        counts[label] = sum(1 for _ in iter_images(class_dir)) if class_dir.exists() else 0
    return counts


def _print_test_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, labels: list[str]) -> None:
    matrix = confusion_matrix(y_true, y_pred, labels)
    normalized = normalize_confusion_matrix(matrix)
    width = max(10, *(len(label) for label in labels))

    print("Test confusion matrix (rows=true, columns=predicted)")
    print(f"Label order: {labels}")
    print("Raw counts:")
    print(f"{'true/pred':>{width}} " + " ".join(f"{label:>{width}}" for label in labels))
    for label, row in zip(labels, matrix):
        print(f"{label:>{width}} " + " ".join(f"{count:>{width}}" for count in row))

    print("Row-normalized:")
    print(f"{'true/pred':>{width}} " + " ".join(f"{label:>{width}}" for label in labels))
    for label, row in zip(labels, normalized):
        print(f"{label:>{width}} " + " ".join(f"{value:>{width}.3f}" for value in row))


def _fit_training_phase(
    model,
    train_ds,
    valid_ds,
    *,
    epochs: int,
    initial_epoch: int = 0,
    class_weight=None,
    callbacks=None,
    verbose: int = 1,
):
    model.fit(
        train_ds,
        validation_data=valid_ds,
        epochs=epochs,
        initial_epoch=initial_epoch,
        class_weight=class_weight or None,
        callbacks=callbacks,
        verbose=verbose,
    )


def _log_training_phase(label: str, start_epoch: int, end_epoch: int) -> None:
    print(f"\n=== {label} ===")
    if start_epoch == 0:
        print(f"Training epochs: 1-{end_epoch}")
    else:
        print(f"Continuing training from epoch {start_epoch} to {end_epoch}")


def _build_efficientnetv2_model(input_shape: tuple[int, int, int], num_classes: int):
    _require_tensorflow()

    augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.08),
            tf.keras.layers.RandomZoom(0.12),
            tf.keras.layers.RandomContrast(0.08),
        ],
        name="augmentation",
    )

    base_model = tf.keras.applications.EfficientNetV2B0(
        include_top=False,
        weights="imagenet",
        input_shape=input_shape,
        pooling="avg",
    )
    base_model.trainable = False

    inputs = tf.keras.Input(shape=input_shape)
    x = augmentation(inputs)
    x = tf.keras.applications.efficientnet_v2.preprocess_input(x)
    x = base_model(x, training=False)
    x = tf.keras.layers.Dropout(0.3)(x)
    outputs = tf.keras.layers.Dense(num_classes, activation="softmax")(x)

    model = tf.keras.Model(inputs, outputs, name="efficientnetv2_skin_classifier")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model, base_model


def train_efficientnetv2_classifier(
    train_root: Path,
    valid_root: Path,
    test_root: Path,
    labels: list[str],
    *,
    image_size: int = 224,
    batch_size: int = 16,
    epochs: int = 10,
    fine_tune_epochs: int = 4,
    fine_tune_at: int = 200,
) -> dict:
    _require_tensorflow()

    input_shape = (image_size, image_size, 3)
    train_ds = tf.keras.utils.image_dataset_from_directory(
        train_root,
        class_names=labels,
        label_mode="categorical",
        image_size=(image_size, image_size),
        batch_size=batch_size,
        shuffle=True,
        seed=42,
    )
    valid_ds = tf.keras.utils.image_dataset_from_directory(
        valid_root,
        class_names=labels,
        label_mode="categorical",
        image_size=(image_size, image_size),
        batch_size=batch_size,
        shuffle=False,
    )
    test_ds = tf.keras.utils.image_dataset_from_directory(
        test_root,
        class_names=labels,
        label_mode="categorical",
        image_size=(image_size, image_size),
        batch_size=batch_size,
        shuffle=False,
    )

    autotune = tf.data.AUTOTUNE
    train_ds = train_ds.cache().prefetch(buffer_size=autotune)
    valid_ds = valid_ds.cache().prefetch(buffer_size=autotune)
    test_ds = test_ds.cache().prefetch(buffer_size=autotune)

    class_counts = _count_images(train_root, labels)
    total_count = sum(class_counts.values())
    class_weight = {
        idx: float(total_count / (len(labels) * count))
        for idx, (label, count) in enumerate(class_counts.items())
        if count > 0
    }

    model, base_model = _build_efficientnetv2_model(input_shape, len(labels))

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=3,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_accuracy",
            factor=0.3,
            patience=2,
            min_lr=1e-6,
        ),
    ]

    _log_training_phase("Base training", 0, epochs)
    _fit_training_phase(
        model,
        train_ds,
        valid_ds,
        epochs=epochs,
        initial_epoch=0,
        class_weight=class_weight,
        callbacks=callbacks,
        verbose=1,
    )

    if fine_tune_epochs > 0:
        base_model.trainable = True
        for layer in base_model.layers[:fine_tune_at]:
            layer.trainable = False

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
            loss="categorical_crossentropy",
            metrics=["accuracy"],
        )
        _log_training_phase("Fine-tuning", epochs, epochs + fine_tune_epochs)
        _fit_training_phase(
            model,
            train_ds,
            valid_ds,
            epochs=epochs + fine_tune_epochs,
            initial_epoch=epochs,
            class_weight=class_weight,
            callbacks=callbacks,
            verbose=1,
        )

    valid_loss, valid_acc = model.evaluate(valid_ds, verbose=0)
    test_loss, test_acc = model.evaluate(test_ds, verbose=0)

    class_labels = list(labels)
    test_true = np.concatenate(
        [np.asarray(class_labels)[np.argmax(targets.numpy(), axis=1)] for _, targets in test_ds]
    )
    test_probabilities = model.predict(test_ds, verbose=0)
    test_pred = np.asarray(class_labels)[np.argmax(test_probabilities, axis=1)]
    _print_test_confusion_matrix(test_true, test_pred, class_labels)

    KERAS_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model.save(KERAS_MODEL_PATH)

    artifact = {
        "model_type": "efficientnetv2",
        "class_labels": list(labels),
        "image_size": [image_size, image_size],
        "keras_model_path": KERAS_MODEL_PATH.name,
        "valid_accuracy": float(valid_acc),
        "test_accuracy": float(test_acc),
        "feature_version": "v2",
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("wb") as fp:
        pickle.dump(artifact, fp)

    print(f"Validation accuracy: {valid_acc:.4f}")
    print(f"Test accuracy: {test_acc:.4f}")
    print(f"Saved EfficientNetV2 model to: {KERAS_MODEL_PATH}")
    print(f"Saved trained model metadata to: {MODEL_PATH}")
    return artifact


def train_knn_classifier(x_train: np.ndarray, y_train: np.ndarray, labels: list[str], k: int) -> dict:
    mean = x_train.mean(axis=0).astype(np.float32)
    std = (x_train.std(axis=0) + 1e-6).astype(np.float32)
    x_train_scaled = ((x_train - mean) / std).astype(np.float32)
    return {
        "model_type": "knn",
        "class_labels": labels,
        "k": int(k),
        "feature_mean": mean,
        "feature_std": std,
        "x_train": x_train_scaled,
        "y_train": y_train,
    }


def train_gaussian_classifier(x_train: np.ndarray, y_train: np.ndarray, labels: list[str]) -> dict:
    means = {}
    variances = {}
    priors = {}

    for label in labels:
        class_data = x_train[y_train == label]
        if len(class_data) == 0:
            continue
        means[label] = class_data.mean(axis=0).astype(np.float32)
        variances[label] = (class_data.var(axis=0) + 1e-4).astype(np.float32)
        priors[label] = float(len(class_data) / len(x_train))

    return {
        "model_type": "gaussian",
        "class_labels": labels,
        "means": means,
        "variances": variances,
        "priors": priors,
    }


def predict_proba_batch(model: dict, x: np.ndarray) -> np.ndarray:
    labels = model["class_labels"]
    model_type = model.get("model_type", "gaussian")

    if model_type == "knn":
        k = model["k"]
        x_train = model["x_train"]
        y_train = model["y_train"]
        mean = model["feature_mean"]
        std = model["feature_std"]

        probs_all = []
        for row in x:
            row_scaled = ((row - mean) / std).astype(np.float32)
            dists = np.sum((x_train - row_scaled) ** 2, axis=1)
            nn_idx = np.argpartition(dists, min(k, len(dists) - 1))[:k]

            vote_weights = np.zeros(len(labels), dtype=np.float64)
            for idx in nn_idx:
                label = y_train[idx]
                label_pos = labels.index(label)
                vote_weights[label_pos] += 1.0 / (float(dists[idx]) + 1e-6)

            vote_weights /= vote_weights.sum() + 1e-12
            probs_all.append(vote_weights)

        return np.vstack(probs_all)

    if model_type == "conv_softmax":
        probs_all = []
        for row in x:
            row_scaled = ((row - model["feature_mean"]) / model["feature_std"]).astype(np.float32)
            logits = row_scaled @ model["weights"] + model["bias"]
            logits = logits - np.max(logits)
            probs = np.exp(logits)
            probs /= probs.sum() + 1e-12
            probs_all.append(probs)
        return np.vstack(probs_all)

    means = model["means"]
    variances = model["variances"]
    priors = model["priors"]

    probs_all = []
    for row in x:
        log_probs = []
        for label in labels:
            mu = means[label]
            var = variances[label]
            log_prior = np.log(priors[label] + 1e-12)
            ll = -0.5 * np.sum(np.log(2.0 * np.pi * var) + ((row - mu) ** 2) / var)
            log_probs.append(log_prior + ll)

        log_probs = np.array(log_probs, dtype=np.float64)
        log_probs -= np.max(log_probs)
        probs = np.exp(log_probs)
        probs /= probs.sum() + 1e-12
        probs_all.append(probs)

    return np.vstack(probs_all)


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float((y_true == y_pred).sum() / len(y_true))


def per_class_accuracy(y_true: np.ndarray, y_pred: np.ndarray, labels: list[str]) -> dict[str, float]:
    metrics = classification_metrics(y_true, y_pred, labels)
    return {label: float(data["accuracy"]) for label, data in metrics["per_class"].items()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train skin type classifier")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "datasets",
        help="Path to dataset root containing train/valid/test",
    )
    parser.add_argument(
        "--labels",
        nargs="+",
        default=["oily", "dry", "normal"],
        help="Class labels to train",
    )
    parser.add_argument(
        "--model-type",
        choices=["gaussian", "knn", "conv_softmax", "efficientnetv2"],
        default="conv_softmax",
        help="Type of classifier to train",
    )
    parser.add_argument("--k", type=int, default=11, help="Number of nearest neighbors")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs for the conv_softmax model")
    parser.add_argument("--lr", type=float, default=0.05, help="Learning rate for the conv_softmax model")
    parser.add_argument("--image-size", type=int, default=224, help="Input image size for EfficientNetV2")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size for EfficientNetV2 training")
    parser.add_argument(
        "--fine-tune-epochs",
        type=int,
        default=4,
        help="Fine-tuning epochs for EfficientNetV2 after the classifier head warms up",
    )
    parser.add_argument(
        "--fine-tune-at",
        type=int,
        default=200,
        help="Layer index from which EfficientNetV2 fine-tuning should begin",
    )
    args = parser.parse_args()

    dataset_root: Path = args.dataset_root
    train_root = dataset_root / "train"
    valid_root = dataset_root / "valid"
    test_root = dataset_root / "test"

    if not train_root.exists():
        raise FileNotFoundError(f"Dataset train folder not found: {train_root}")

    labels = args.labels

    if args.model_type == "efficientnetv2":
        train_efficientnetv2_classifier(
            train_root,
            valid_root,
            test_root,
            labels,
            image_size=args.image_size,
            batch_size=args.batch_size,
            epochs=args.epochs,
            fine_tune_epochs=args.fine_tune_epochs,
            fine_tune_at=args.fine_tune_at,
        )
        return

    print(f"Loading train split from: {train_root}")
    x_train, y_train = load_split(train_root, labels)
    print(f"Train samples: {len(y_train)} | Distribution: {dict(Counter(y_train))}")

    x_valid, y_valid = load_split(valid_root, labels)
    print(f"Valid samples: {len(y_valid)} | Distribution: {dict(Counter(y_valid))}")

    x_test, y_test = load_split(test_root, labels)
    print(f"Test samples: {len(y_test)} | Distribution: {dict(Counter(y_test))}")

    if args.model_type == "knn":
        model = train_knn_classifier(x_train, y_train, labels, k=args.k)
    elif args.model_type == "gaussian":
        model = train_gaussian_classifier(x_train, y_train, labels)
    else:
        model = train_conv_softmax_classifier(x_train, y_train, labels, epochs=args.epochs, lr=args.lr)

    valid_probs = predict_proba_batch(model, x_valid)
    test_probs = predict_proba_batch(model, x_test)

    class_labels = list(model["class_labels"])
    valid_preds = np.array([class_labels[i] for i in np.argmax(valid_probs, axis=1)])
    test_preds = np.array([class_labels[i] for i in np.argmax(test_probs, axis=1)])

    valid_metrics = classification_metrics(y_valid, valid_preds, class_labels)
    test_metrics = classification_metrics(y_test, test_preds, class_labels)

    valid_acc = valid_metrics["accuracy"]
    test_acc = test_metrics["accuracy"]

    print(f"Validation accuracy: {valid_acc:.4f}")
    print(f"Validation precision: {valid_metrics['macro_precision']:.4f}")
    print(f"Validation recall: {valid_metrics['macro_recall']:.4f}")
    print(f"Validation F1: {valid_metrics['macro_f1']:.4f}")
    print(f"Test accuracy: {test_acc:.4f}")
    print(f"Test precision: {test_metrics['macro_precision']:.4f}")
    print(f"Test recall: {test_metrics['macro_recall']:.4f}")
    print(f"Test F1: {test_metrics['macro_f1']:.4f}")
    print(f"Validation per-class accuracy: {per_class_accuracy(y_valid, valid_preds, class_labels)}")
    print(f"Test per-class accuracy: {per_class_accuracy(y_test, test_preds, class_labels)}")
    _print_test_confusion_matrix(y_test, test_preds, class_labels)

    artifact = {
        **model,
        "valid_accuracy": float(valid_acc),
        "valid_precision": float(valid_metrics["macro_precision"]),
        "valid_recall": float(valid_metrics["macro_recall"]),
        "valid_f1": float(valid_metrics["macro_f1"]),
        "test_accuracy": float(test_acc),
        "test_precision": float(test_metrics["macro_precision"]),
        "test_recall": float(test_metrics["macro_recall"]),
        "test_f1": float(test_metrics["macro_f1"]),
        "feature_version": "v1",
    }
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("wb") as fp:
        pickle.dump(artifact, fp)

    print(f"Saved trained model to: {MODEL_PATH}")


if __name__ == "__main__":
    main()