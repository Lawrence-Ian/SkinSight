"""Build a deduplicated copy of the dataset.

The script keeps one copy of each exact image hash and preserves the first
split encountered in the order train -> valid -> test.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from collections import defaultdict
from pathlib import Path


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLIT_ORDER = ["train", "valid", "test"]


def iter_images(folder: Path):
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            yield path


def sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_clean_dataset(source_root: Path, output_root: Path) -> dict[str, int]:
    seen_hashes: set[str] = set()
    copied = defaultdict(int)
    skipped_duplicates = 0

    for split in SPLIT_ORDER:
        split_root = source_root / split
        if not split_root.exists():
            continue
        for class_dir in sorted([p for p in split_root.iterdir() if p.is_dir()]):
            for src_path in sorted(iter_images(class_dir)):
                file_hash = sha256_bytes(src_path)
                if file_hash in seen_hashes:
                    skipped_duplicates += 1
                    continue
                seen_hashes.add(file_hash)

                relative_path = src_path.relative_to(source_root)
                dest_path = output_root / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dest_path)
                copied[split] += 1

    return {
        "copied_train": copied["train"],
        "copied_valid": copied["valid"],
        "copied_test": copied["test"],
        "skipped_duplicates": skipped_duplicates,
        "total_copied": sum(copied.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a deduplicated skin dataset")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "datasets",
        help="Original dataset root",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "datasets",
        help="Destination for the deduplicated dataset",
    )
    args = parser.parse_args()

    if not args.source_root.exists():
        raise FileNotFoundError(f"Source dataset not found: {args.source_root}")

    if args.output_root.exists():
        shutil.rmtree(args.output_root)

    stats = prepare_clean_dataset(args.source_root, args.output_root)
    print(f"Clean dataset written to: {args.output_root}")
    print(stats)


if __name__ == "__main__":
    main()