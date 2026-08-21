"""
Dataset Preparation Script for Connecting the Dots
Downloads and prepares training datasets for face recognition.

Supported datasets:
1. LFW (Labeled Faces in the Wild) - for validation
2. CASIA-WebFace - for training ArcFace
3. UTKFace - for age estimation/progression
4. MS-Celeb-1M - large scale training

Usage:
    python prepare_dataset.py --dataset lfw --output ./data/lfw
    python prepare_dataset.py --dataset utk --output ./data/utk
"""

import os
import cv2
import numpy as np
import argparse
import logging
from pathlib import Path
from tqdm import tqdm
import urllib.request
import zipfile
import tarfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_lfw(output_dir: str):
    """Download LFW dataset for evaluation"""
    url = "http://vis-www.cs.umass.edu/lfw/lfw-funneled.tgz"
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    tgz_path = output_path / "lfw.tgz"
    logger.info(f"Downloading LFW to {tgz_path}...")

    urllib.request.urlretrieve(url, tgz_path, reporthook=lambda *args: None)

    logger.info("Extracting LFW...")
    with tarfile.open(tgz_path) as tar:
        tar.extractall(output_path)

    logger.info(f"LFW downloaded to {output_path}")


def align_faces_mtcnn(input_dir: str, output_dir: str, img_size: int = 112):
    """Detect and align all faces using MTCNN"""
    try:
        from mtcnn import MTCNN
        detector = MTCNN()
    except ImportError:
        logger.error("Install MTCNN: pip install mtcnn")
        return

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    success, failed = 0, 0
    image_files = list(input_path.rglob("*.jpg")) + list(input_path.rglob("*.png"))

    for img_file in tqdm(image_files, desc="Aligning faces"):
        img = cv2.imread(str(img_file))
        if img is None:
            failed += 1
            continue

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        faces = detector.detect_faces(rgb)

        if not faces:
            failed += 1
            continue

        face = max(faces, key=lambda f: f["confidence"])
        x, y, w, h = face["box"]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(img.shape[1], x + w), min(img.shape[0], y + h)
        face_crop = img[y1:y2, x1:x2]

        if face_crop.size == 0:
            failed += 1
            continue

        face_resized = cv2.resize(face_crop, (img_size, img_size))
        rel_path = img_file.relative_to(input_path)
        out_file = output_path / rel_path
        out_file.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_file), face_resized)
        success += 1

    logger.info(f"Aligned: {success} success, {failed} failed")


def augment_dataset(input_dir: str, output_dir: str, augment_factor: int = 5):
    """Data augmentation for small datasets"""
    import random

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    image_files = list(input_path.rglob("*.jpg")) + list(input_path.rglob("*.png"))
    logger.info(f"Augmenting {len(image_files)} images by factor {augment_factor}")

    for img_file in tqdm(image_files, desc="Augmenting"):
        img = cv2.imread(str(img_file))
        if img is None:
            continue

        rel_path = img_file.relative_to(input_path)
        base_out = output_path / rel_path.parent
        base_out.mkdir(parents=True, exist_ok=True)

        # Original
        cv2.imwrite(str(base_out / img_file.name), img)

        for i in range(augment_factor - 1):
            aug = img.copy()

            # Random horizontal flip
            if random.random() > 0.5:
                aug = cv2.flip(aug, 1)

            # Random brightness/contrast
            alpha = random.uniform(0.8, 1.2)
            beta = random.randint(-20, 20)
            aug = np.clip(aug.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)

            # Random rotation (±10 degrees)
            angle = random.uniform(-10, 10)
            h, w = aug.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            aug = cv2.warpAffine(aug, M, (w, h))

            # Random Gaussian noise
            noise = np.random.normal(0, 5, aug.shape).astype(np.uint8)
            aug = cv2.add(aug, noise)

            stem = img_file.stem
            out_name = f"{stem}_aug{i+1}{img_file.suffix}"
            cv2.imwrite(str(base_out / out_name), aug)

    logger.info("Augmentation complete")


def create_pairs_for_verification(dataset_dir: str, output_file: str, num_pairs: int = 6000):
    """Create positive/negative pairs for face verification evaluation"""
    import random
    import json

    dataset_path = Path(dataset_dir)
    persons = [d for d in dataset_path.iterdir() if d.is_dir()]
    pairs = []

    # Positive pairs (same person)
    for _ in range(num_pairs // 2):
        person = random.choice(persons)
        imgs = list(person.glob("*.jpg"))
        if len(imgs) < 2:
            continue
        a, b = random.sample(imgs, 2)
        pairs.append({"img1": str(a), "img2": str(b), "same_person": True})

    # Negative pairs (different persons)
    for _ in range(num_pairs // 2):
        p1, p2 = random.sample(persons, 2)
        imgs1 = list(p1.glob("*.jpg"))
        imgs2 = list(p2.glob("*.jpg"))
        if not imgs1 or not imgs2:
            continue
        pairs.append({"img1": str(random.choice(imgs1)), "img2": str(random.choice(imgs2)), "same_person": False})

    random.shuffle(pairs)
    with open(output_file, "w") as f:
        json.dump(pairs, f, indent=2)
    logger.info(f"Saved {len(pairs)} pairs to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["lfw", "align", "augment", "pairs"])
    parser.add_argument("--input", default="./data/raw")
    parser.add_argument("--output", default="./data/processed")
    parser.add_argument("--img_size", type=int, default=112)
    parser.add_argument("--augment_factor", type=int, default=5)
    args = parser.parse_args()

    if args.dataset == "lfw":
        download_lfw(args.output)
    elif args.dataset == "align":
        align_faces_mtcnn(args.input, args.output, args.img_size)
    elif args.dataset == "augment":
        augment_dataset(args.input, args.output, args.augment_factor)
    elif args.dataset == "pairs":
        create_pairs_for_verification(args.input, f"{args.output}/pairs.json")
