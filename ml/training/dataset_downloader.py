"""
Dataset Downloader & Preparer for Phase 3 Training
===================================================
Handles: LFW, UTKFace, CASIA-WebFace (partial), VGGFace2

Usage:
    python dataset_downloader.py --dataset lfw        # ~200MB, auto-downloads
    python dataset_downloader.py --dataset utk        # ~110MB, auto-downloads
    python dataset_downloader.py --dataset vggface2   # manual — prints instructions
    python dataset_downloader.py --dataset casia      # manual — prints instructions
    python dataset_downloader.py --align --input ./data/raw --output ./data/aligned
    python dataset_downloader.py --split  --input ./data/aligned --ratio 0.9
"""

import os
import sys
import shutil
import tarfile
import zipfile
import argparse
import logging
import urllib.request
from pathlib import Path
from typing import Tuple

import numpy as np
import cv2
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ── Progress bar for urllib ───────────────────────────────────────────────────

class _ProgressBar:
    def __init__(self, desc="Downloading"):
        self.pbar = None
        self.desc = desc

    def __call__(self, block_num, block_size, total_size):
        if self.pbar is None:
            self.pbar = tqdm(total=total_size, unit="B",
                             unit_scale=True, desc=self.desc)
        self.pbar.update(block_size)

    def close(self):
        if self.pbar:
            self.pbar.close()


# ── Dataset downloaders ───────────────────────────────────────────────────────

def download_lfw(output_dir: str):
    """
    LFW — Labeled Faces in the Wild
    ~200 MB | 13,233 images | 5,749 identities
    Best for: verification evaluation, NOT training (too small)
    """
    output_path = Path(output_dir) / "lfw"
    if output_path.exists():
        logger.info(f"LFW already exists at {output_path}")
        return str(output_path)

    output_path.mkdir(parents=True, exist_ok=True)
    url  = "http://vis-www.cs.umass.edu/lfw/lfw-funneled.tgz"
    tgz  = output_path.parent / "lfw-funneled.tgz"

    logger.info("Downloading LFW (~200 MB)...")
    pb = _ProgressBar("LFW")
    urllib.request.urlretrieve(url, tgz, reporthook=pb)
    pb.close()

    logger.info("Extracting...")
    with tarfile.open(tgz) as tar:
        tar.extractall(output_path.parent)
    tgz.unlink()

    # Also download pairs.txt for verification evaluation
    pairs_url  = "http://vis-www.cs.umass.edu/lfw/pairs.txt"
    urllib.request.urlretrieve(pairs_url, output_path / "pairs.txt")

    logger.info(f"LFW ready at {output_path}")
    return str(output_path)


def download_utk(output_dir: str):
    """
    UTKFace — Age-labeled face dataset
    ~110 MB | 20,000+ images | age range 0-116
    Best for: age estimation, age progression GAN training
    Filename format: [age]_[gender]_[race]_[date].jpg
    """
    output_path = Path(output_dir) / "utk"
    if output_path.exists():
        logger.info(f"UTKFace already exists at {output_path}")
        return str(output_path)

    # Try direct download (mirror links — primary source requires Google Drive)
    mirrors = [
        "https://github.com/aicip/UTKFace/raw/master/",  # placeholder
    ]

    logger.info("=" * 60)
    logger.info("UTKFace requires manual download:")
    logger.info("1. Go to: https://susanqq.github.io/UTKFace/")
    logger.info("2. Click 'Download' → 'Part 1', 'Part 2', 'Part 3'")
    logger.info("3. Extract all .jpg files into:")
    logger.info(f"   {output_path}/")
    logger.info("4. Re-run with --align to align faces")
    logger.info("=" * 60)

    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "PUT_UTK_IMAGES_HERE.txt").write_text(
        "Download UTKFace from https://susanqq.github.io/UTKFace/\n"
        "Place all .jpg files directly in this folder.\n"
        "Filename format: age_gender_race_date.jpg\n"
        "Example: 25_0_2_20170116174525125.jpg\n"
    )
    return str(output_path)


def instructions_casia():
    """CASIA-WebFace — 494,414 images, 10,575 identities"""
    logger.info("=" * 60)
    logger.info("CASIA-WebFace (recommended for ArcFace training):")
    logger.info("494K images | 10,575 identities | ~4 GB")
    logger.info("")
    logger.info("Download options:")
    logger.info("  A) Academic request: insightface.ai/casia")
    logger.info("  B) Baidu Netdisk: Search 'CASIA-WebFace' on academic forums")
    logger.info("  C) Use VGGFace2 instead (see --dataset vggface2)")
    logger.info("")
    logger.info("After download, folder structure should be:")
    logger.info("  casia/")
    logger.info("    0000045/  (identity ID)")
    logger.info("      001.jpg")
    logger.info("      002.jpg")
    logger.info("    0000099/")
    logger.info("      ...")
    logger.info("")
    logger.info("Then run: python dataset_downloader.py --align \\")
    logger.info("    --input ./data/casia --output ./data/aligned")
    logger.info("=" * 60)


def instructions_vggface2():
    """VGGFace2 — 3.31M images, 9,131 identities"""
    logger.info("=" * 60)
    logger.info("VGGFace2 (high quality, good alternative to CASIA):")
    logger.info("3.3M images | 9,131 identities | ~36 GB")
    logger.info("")
    logger.info("1. Register at: https://www.robots.ox.ac.uk/~vgg/data/vgg_face2/")
    logger.info("2. Download train.tar.gz and test.tar.gz")
    logger.info("3. Extract to ./data/vggface2/")
    logger.info("4. Run alignment step")
    logger.info("=" * 60)


# ── Face alignment ────────────────────────────────────────────────────────────

def align_dataset(input_dir: str, output_dir: str, img_size: int = 112,
                  min_confidence: float = 0.9):
    """
    Detect and align all faces using MTCNN.
    Crops to face bounding box with margin, resizes to img_size×img_size.
    Skips images where no face is detected with sufficient confidence.
    """
    try:
        from mtcnn import MTCNN
        detector = MTCNN()
    except ImportError:
        logger.error("MTCNN not installed. Run: pip install mtcnn tensorflow")
        sys.exit(1)

    input_path  = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    exts   = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    images = [p for p in input_path.rglob("*") if p.suffix.lower() in exts]
    logger.info(f"Found {len(images)} images in {input_path}")

    ok, skip, fail = 0, 0, 0

    for img_path in tqdm(images, desc="Aligning faces"):
        try:
            img = cv2.imread(str(img_path))
            if img is None:
                fail += 1
                continue

            rgb   = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            faces = detector.detect_faces(rgb)

            # Keep only high-confidence detections
            faces = [f for f in faces if f["confidence"] >= min_confidence]
            if not faces:
                skip += 1
                continue

            # Use largest face by area
            best   = max(faces, key=lambda f: f["box"][2] * f["box"][3])
            x, y, w, h = best["box"]
            margin = int(max(w, h) * 0.2)
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(img.shape[1], x + w + margin)
            y2 = min(img.shape[0], y + h + margin)

            face_crop = img[y1:y2, x1:x2]
            if face_crop.size == 0:
                skip += 1
                continue

            face_resized = cv2.resize(face_crop, (img_size, img_size),
                                      interpolation=cv2.INTER_LANCZOS4)

            # Mirror output directory structure
            rel      = img_path.relative_to(input_path)
            out_file = output_path / rel
            out_file.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out_file), face_resized,
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            ok += 1

        except Exception as e:
            logger.debug(f"Failed {img_path}: {e}")
            fail += 1

    total = ok + skip + fail
    logger.info(f"Alignment complete: {ok}/{total} aligned, "
                f"{skip} skipped (no face), {fail} errors")
    return ok, skip, fail


# ── Train / Val split ─────────────────────────────────────────────────────────

def split_dataset(input_dir: str, output_dir: str, train_ratio: float = 0.9,
                  min_images_per_identity: int = 2):
    """
    Split aligned dataset into train/ and val/ subdirectories.
    Only includes identities that have at least min_images_per_identity images.
    """
    import random
    random.seed(42)

    input_path  = Path(input_dir)
    output_path = Path(output_dir)
    train_dir   = output_path / "train"
    val_dir     = output_path / "val"

    identities  = [d for d in input_path.iterdir() if d.is_dir()]
    logger.info(f"Found {len(identities)} identities")

    kept, dropped = 0, 0
    for identity in tqdm(identities, desc="Splitting"):
        imgs = list(identity.glob("*.jpg")) + list(identity.glob("*.png"))
        if len(imgs) < min_images_per_identity:
            dropped += 1
            continue

        random.shuffle(imgs)
        n_train = max(1, int(len(imgs) * train_ratio))
        train_imgs = imgs[:n_train]
        val_imgs   = imgs[n_train:] or imgs[-1:]  # at least 1 in val

        for img in train_imgs:
            dst = train_dir / identity.name / img.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img, dst)

        for img in val_imgs:
            dst = val_dir / identity.name / img.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img, dst)

        kept += 1

    logger.info(f"Split complete: {kept} identities kept, {dropped} dropped "
                f"(< {min_images_per_identity} images)")
    logger.info(f"Train → {train_dir}")
    logger.info(f"Val   → {val_dir}")


# ── Augmentation ──────────────────────────────────────────────────────────────

def augment_dataset(input_dir: str, output_dir: str, factor: int = 5,
                    img_size: int = 112):
    """
    Augment training data to increase dataset size.
    Applies: flip, brightness, contrast, rotation, noise, blur.
    Creates `factor` total copies per image (1 original + factor-1 augmented).
    """
    import random
    random.seed(0)

    input_path  = Path(input_dir)
    output_path = Path(output_dir)
    images = [p for p in input_path.rglob("*.jpg")]
    logger.info(f"Augmenting {len(images)} images × {factor}")

    for img_path in tqdm(images, desc="Augmenting"):
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        rel     = img_path.relative_to(input_path)
        out_dir = output_path / rel.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        # Always copy original
        cv2.imwrite(str(out_dir / img_path.name), img)

        for i in range(factor - 1):
            aug = img.copy()

            # Random horizontal flip (50%)
            if random.random() > 0.5:
                aug = cv2.flip(aug, 1)

            # Random brightness/contrast
            alpha = random.uniform(0.75, 1.25)
            beta  = random.randint(-25, 25)
            aug   = np.clip(aug.astype(np.float32) * alpha + beta, 0, 255)
            aug   = aug.astype(np.uint8)

            # Random rotation ±12°
            angle  = random.uniform(-12, 12)
            h, w   = aug.shape[:2]
            M      = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            aug    = cv2.warpAffine(aug, M, (w, h),
                                    borderMode=cv2.BORDER_REFLECT)

            # Random Gaussian noise
            if random.random() > 0.5:
                noise = np.random.normal(0, random.uniform(2, 8), aug.shape)
                aug   = np.clip(aug.astype(np.float32) + noise, 0, 255).astype(np.uint8)

            # Random Gaussian blur (light)
            if random.random() > 0.7:
                ksize = random.choice([3, 5])
                aug   = cv2.GaussianBlur(aug, (ksize, ksize), 0)

            stem    = img_path.stem
            outname = f"{stem}_aug{i+1:02d}.jpg"
            cv2.imwrite(str(out_dir / outname), aug,
                        [cv2.IMWRITE_JPEG_QUALITY, 90])

    logger.info(f"Augmentation complete → {output_dir}")


# ── Verification pair generation ──────────────────────────────────────────────

def make_verification_pairs(dataset_dir: str, output_file: str,
                             num_pairs: int = 6000):
    """
    Generate positive (same person) and negative (different person) pairs
    for face verification evaluation.
    Output: JSON file consumed by evaluate_model.py
    """
    import random
    import json
    random.seed(42)

    dataset_path = Path(dataset_dir)
    persons      = [d for d in dataset_path.iterdir()
                    if d.is_dir() and len(list(d.glob("*.jpg"))) >= 2]
    logger.info(f"Building pairs from {len(persons)} identities")

    pairs = []

    # Positive pairs (same person, different photos)
    for _ in range(num_pairs // 2):
        person = random.choice(persons)
        imgs   = list(person.glob("*.jpg"))
        a, b   = random.sample(imgs, 2)
        pairs.append({"img1": str(a), "img2": str(b), "same_person": True,
                      "identity": person.name})

    # Negative pairs (different persons)
    for _ in range(num_pairs // 2):
        p1, p2 = random.sample(persons, 2)
        a = random.choice(list(p1.glob("*.jpg")))
        b = random.choice(list(p2.glob("*.jpg")))
        pairs.append({"img1": str(a), "img2": str(b), "same_person": False,
                      "identity": None})

    random.shuffle(pairs)

    with open(output_file, "w") as f:
        json.dump(pairs, f, indent=2)

    pos = sum(1 for p in pairs if p["same_person"])
    neg = len(pairs) - pos
    logger.info(f"Saved {len(pairs)} pairs ({pos} positive, {neg} negative) → {output_file}")


# ── UTKFace specific preparation ──────────────────────────────────────────────

def prepare_utk_for_gan(input_dir: str, output_dir: str, img_size: int = 256):
    """
    Organise UTKFace images into age-group folders for GAN training.
    UTK filename format: [age]_[gender]_[race]_[date].jpg
    """
    input_path  = Path(input_dir)
    output_path = Path(output_dir)

    age_groups = {
        "0_10":   (0,  10),
        "10_20":  (10, 20),
        "20_30":  (20, 30),
        "30_40":  (30, 40),
        "40_50":  (40, 50),
        "50_60":  (50, 60),
        "60_100": (60, 100),
    }

    counts = {k: 0 for k in age_groups}
    errors = 0

    images = list(input_path.glob("*.jpg")) + list(input_path.glob("*.JPG"))
    logger.info(f"Organising {len(images)} UTKFace images")

    for img_path in tqdm(images, desc="Organising UTK"):
        try:
            age = int(img_path.stem.split("_")[0])
        except (ValueError, IndexError):
            errors += 1
            continue

        group = None
        for gname, (lo, hi) in age_groups.items():
            if lo <= age < hi:
                group = gname
                break

        if group is None:
            errors += 1
            continue

        out_dir = output_path / group
        out_dir.mkdir(parents=True, exist_ok=True)

        img = cv2.imread(str(img_path))
        if img is None:
            errors += 1
            continue

        img_resized = cv2.resize(img, (img_size, img_size),
                                 interpolation=cv2.INTER_LANCZOS4)
        cv2.imwrite(str(out_dir / img_path.name), img_resized)
        counts[group] += 1

    logger.info("UTKFace age distribution:")
    for group, count in counts.items():
        bar = "█" * (count // 20)
        logger.info(f"  {group:>7}: {count:5d}  {bar}")
    logger.info(f"  Errors: {errors}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dataset downloader and preparer for Phase 3 training"
    )
    parser.add_argument("--dataset",  choices=["lfw", "utk", "casia", "vggface2"],
                        help="Download/show instructions for a dataset")
    parser.add_argument("--align",    action="store_true",
                        help="Align faces with MTCNN")
    parser.add_argument("--split",    action="store_true",
                        help="Split into train/val")
    parser.add_argument("--augment",  action="store_true",
                        help="Augment training data")
    parser.add_argument("--utk-prep", action="store_true",
                        help="Prepare UTKFace for GAN training")
    parser.add_argument("--pairs",    action="store_true",
                        help="Generate verification pairs JSON")
    parser.add_argument("--input",    default="./data/raw")
    parser.add_argument("--output",   default="./data/processed")
    parser.add_argument("--ratio",    type=float, default=0.9,
                        help="Train split ratio (default 0.9)")
    parser.add_argument("--factor",   type=int, default=5,
                        help="Augmentation factor (default 5)")
    parser.add_argument("--img-size", type=int, default=112,
                        help="Output image size (default 112)")
    parser.add_argument("--num-pairs", type=int, default=6000)
    args = parser.parse_args()

    if args.dataset == "lfw":
        download_lfw(args.output)
    elif args.dataset == "utk":
        download_utk(args.output)
    elif args.dataset == "casia":
        instructions_casia()
    elif args.dataset == "vggface2":
        instructions_vggface2()

    if args.align:
        align_dataset(args.input, args.output, img_size=args.img_size)

    if args.split:
        split_dataset(args.input, args.output, train_ratio=args.ratio)

    if args.augment:
        augment_dataset(args.input, args.output, factor=args.factor,
                        img_size=args.img_size)

    if args.utk_prep:
        prepare_utk_for_gan(args.input, args.output, img_size=args.img_size)

    if args.pairs:
        make_verification_pairs(args.input,
                                os.path.join(args.output, "pairs.json"),
                                args.num_pairs)
