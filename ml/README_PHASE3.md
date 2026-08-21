# Phase 3: Model Training Guide

## Overview

Phase 3 trains two custom models:
1. **ArcFace** — face recognition backbone (replaces mock embeddings)
2. **Age Progression GAN** — ages a child's photo forward in time

---

## Hardware Requirements

| Mode | Hardware | Speed |
|------|----------|-------|
| CPU only | Any modern laptop | ~3 days / 50 epochs |
| GPU (recommended) | NVIDIA GTX 1060+ / Google Colab T4 | ~4 hours / 50 epochs |
| Cloud GPU | Colab Pro / RunPod / Vast.ai | Fastest, cheapest |

**Recommendation: Use Google Colab (free T4 GPU). See notebooks/train_on_colab.ipynb**

---

## Step-by-Step

### Step 1 — Install ML dependencies
```bash
cd ml
setup_ml_windows.bat        # Windows
# OR
pip install -r requirements_ml.txt
```

### Step 2 — Get Datasets

**For ArcFace (face recognition):**
```bash
cd ml/training

# LFW — free, auto-downloads ~200 MB, good for testing
python dataset_downloader.py --dataset lfw --output ../data

# Then align all faces:
python dataset_downloader.py --align \
    --input  ../data/lfw/lfw-funneled \
    --output ../data/aligned \
    --img-size 112

# Split into train/val:
python dataset_downloader.py --split \
    --input  ../data/aligned \
    --output ../data/split \
    --ratio  0.9
```

For better accuracy, use CASIA-WebFace (494K images):
```bash
python dataset_downloader.py --dataset casia
# Follow the printed instructions
```

**For Age GAN:**
1. Download UTKFace from https://susanqq.github.io/UTKFace/
2. Place all .jpg files in `ml/data/utk/`
3. Run:
```bash
python dataset_downloader.py --utk-prep \
    --input  ../data/utk \
    --output ../data/utk_grouped \
    --img-size 256
```

### Step 3 — Augment (optional but recommended for small datasets)
```bash
python dataset_downloader.py --augment \
    --input  ../data/split/train \
    --output ../data/augmented \
    --factor 5
```

### Step 4 — Train ArcFace
```bash
python training/train_arcface.py \
    --data_dir   ../data/split \
    --output_dir ../checkpoints/arcface \
    --backbone   resnet50 \
    --epochs     50 \
    --batch_size 32

# Monitor progress:
# tail -f ../checkpoints/arcface/training_history.json (Linux)
# Checkpoints saved every 5 epochs to ../checkpoints/arcface/
```

### Step 5 — Evaluate ArcFace
```bash
# First generate verification pairs:
python training/dataset_downloader.py --pairs \
    --input  ../data/split/val \
    --output ../data \
    --num-pairs 3000

# Evaluate:
python training/evaluate_model.py \
    --checkpoint ../checkpoints/arcface/best.pth \
    --pairs      ../data/pairs.json \
    --output_dir ../eval_results

# Target metrics:
#   ROC-AUC > 0.95  ← acceptable
#   ROC-AUC > 0.97  ← good
#   EER      < 0.08  ← good
```

### Step 6 — Train Age GAN
```bash
python training/train_age_gan.py \
    --data_dir   ../data/utk_grouped \
    --output_dir ../checkpoints/age_gan \
    --epochs     100 \
    --batch_size 8

# View generated sample images in:
# ../checkpoints/age_gan/samples/epoch_XXXX.jpg
```

### Step 7 — Register model into backend
```bash
python scripts/register_model.py \
    --checkpoint ../checkpoints/arcface/best.pth \
    --test_image  any_face_photo.jpg \
    --backend_dir ../../backend

# Follow the printed instructions to wire it into face_model.py
```

---

## Expected Training Curves

### ArcFace (good run)
```
Epoch  1: train=8.2  val=8.0
Epoch 10: train=5.1  val=5.3
Epoch 20: train=3.8  val=4.0   ← LR drops
Epoch 35: train=2.9  val=3.1   ← LR drops again
Epoch 50: train=2.4  val=2.6   ← Best model
```

### Age GAN (good run)
```
Epoch  1:  G=5.2  D=0.7
Epoch 20:  G=3.1  D=0.5
Epoch 50:  G=2.3  D=0.4   ← Faces look natural
Epoch 100: G=1.9  D=0.4   ← Fine details sharp
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `CUDA out of memory` | Reduce `--batch_size` to 16 or 8 |
| `No face detected` in alignment | Lower `--min_confidence` to 0.8 |
| GAN produces noise/blurry output | Reduce LR to 1e-4, train longer |
| AUC stuck at 0.5 | Dataset too small — use CASIA, not just LFW |
| Loss is NaN | Reduce learning rate, check for corrupt images |
