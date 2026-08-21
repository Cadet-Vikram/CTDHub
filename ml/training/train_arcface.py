"""
ArcFace Training Script — Full Production Version
==================================================
Supports: config file, mixed precision, checkpoint resume,
          LR scheduling, TensorBoard logging, model export.

Usage:
    # With config file (recommended):
    python train_arcface.py --config ../configs/arcface_config.yaml

    # Quick CLI:
    python train_arcface.py --data_dir ./data/aligned --epochs 50

    # Resume from checkpoint:
    python train_arcface.py --config ../configs/arcface_config.yaml \
                            --resume ./checkpoints/arcface/epoch_20.pth
"""

import os
import sys
import json
import math
import time
import shutil
import logging
import argparse
from pathlib import Path
from typing import Optional

import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from torch.cuda.amp import autocast, GradScaler
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 1. ArcFace Loss
# ══════════════════════════════════════════════════════════════════════════════

class ArcFaceLoss(nn.Module):
    """
    ArcFace: Additive Angular Margin Loss for Face Recognition
    Paper: https://arxiv.org/abs/1801.07698

    Intuition: Instead of softmax cross-entropy, we push embeddings of the
    same person to be angularly very close, and different persons very far apart.
    The margin `m` controls how strict this separation is.
    """

    def __init__(self, embedding_size: int, num_classes: int,
                 scale: float = 64.0, margin: float = 0.5):
        super().__init__()
        self.s   = scale
        self.m   = margin
        self.W   = nn.Parameter(torch.empty(num_classes, embedding_size))
        nn.init.xavier_uniform_(self.W)

        self.cos_m     = math.cos(margin)
        self.sin_m     = math.sin(margin)
        self.threshold = math.cos(math.pi - margin)
        self.mm        = math.sin(math.pi - margin) * margin

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        # Normalise embeddings and weights to unit hypersphere
        x = nn.functional.normalize(embeddings, p=2, dim=1)
        W = nn.functional.normalize(self.W, p=2, dim=1)

        cosine = nn.functional.linear(x, W)          # (B, C)
        sine   = torch.sqrt(1.0 - cosine.pow(2).clamp(0, 1))

        # cos(θ + m) = cos·cos_m − sin·sin_m
        phi = cosine * self.cos_m - sine * self.sin_m
        # Back-off for θ near π (numerical stability)
        phi = torch.where(cosine > self.threshold, phi, cosine - self.mm)

        # Apply margin only to the ground-truth class
        one_hot = torch.zeros_like(cosine).scatter_(1, labels.view(-1, 1), 1.0)
        logits  = one_hot * phi + (1.0 - one_hot) * cosine
        logits  *= self.s

        return nn.functional.cross_entropy(logits, labels)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Backbone Networks
# ══════════════════════════════════════════════════════════════════════════════

class FaceEmbeddingNet(nn.Module):
    """
    ResNet-based face embedding network.
    Input:  (B, 3, 112, 112)
    Output: (B, embedding_size) — L2-normalised
    """

    def __init__(self, backbone: str = "resnet50",
                 embedding_size: int = 512,
                 pretrained: bool = True):
        super().__init__()
        self.backbone_name = backbone

        if backbone == "resnet50":
            base = models.resnet50(weights="IMAGENET1K_V2" if pretrained else None)
            feat_dim = 2048
        elif backbone == "resnet100":
            base = models.resnet101(weights="IMAGENET1K_V2" if pretrained else None)
            feat_dim = 2048
        elif backbone == "mobilenetv3":
            base = models.mobilenet_v3_large(
                weights="IMAGENET1K_V2" if pretrained else None)
            feat_dim = 960
        else:
            raise ValueError(f"Unknown backbone: {backbone}")

        # Remove final classifier head
        if backbone.startswith("resnet"):
            self.features = nn.Sequential(*list(base.children())[:-1])
        else:
            self.features = base.features

        self.head = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.BatchNorm1d(feat_dim),
            nn.Dropout(p=0.4),
            nn.Linear(feat_dim, embedding_size, bias=False),
            nn.BatchNorm1d(embedding_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.features(x)
        emb  = self.head(feat)
        return nn.functional.normalize(emb, p=2, dim=1)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Dataset
# ══════════════════════════════════════════════════════════════════════════════

class FaceDataset(Dataset):
    """
    Expects folder structure:
        root/
            identity_001/
                img1.jpg
                img2.jpg
            identity_002/
                img1.jpg
    """

    def __init__(self, root_dir: str, transform=None):
        self.root       = Path(root_dir)
        self.transform  = transform
        self.samples    = []         # [(path, label), ...]
        self.class_to_idx = {}

        for idx, person_dir in enumerate(sorted(self.root.iterdir())):
            if not person_dir.is_dir():
                continue
            self.class_to_idx[person_dir.name] = idx
            for ext in ("*.jpg", "*.jpeg", "*.png"):
                for img in person_dir.glob(ext):
                    self.samples.append((img, idx))

        logger.info(f"Dataset: {len(self.samples)} images, "
                    f"{len(self.class_to_idx)} identities")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = cv2.imread(str(path))
        if img is None:
            img = np.zeros((112, 112, 3), dtype=np.uint8)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        if self.transform:
            from PIL import Image
            img = self.transform(Image.fromarray(img))
        else:
            img = torch.FloatTensor(img).permute(2, 0, 1) / 127.5 - 1.0

        return img, label


def build_transforms(img_size: int = 112, augment: bool = True):
    train_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3),
        transforms.RandomGrayscale(p=0.05),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ]) if augment else transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])

    val_tf = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])
    return train_tf, val_tf


# ══════════════════════════════════════════════════════════════════════════════
# 4. Training Loop
# ══════════════════════════════════════════════════════════════════════════════

def train(cfg: dict, resume: Optional[str] = None):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = cfg["training"].get("mixed_precision", True) and device.type == "cuda"
    logger.info(f"Device: {device} | Mixed precision: {use_amp}")

    # ── Data ────────────────────────────────────────────────────────────────
    train_tf, val_tf = build_transforms(
        cfg["data"]["img_size"],
        cfg["data"].get("augment", True),
    )
    train_ds = FaceDataset(cfg["data"]["train_dir"], transform=train_tf)
    val_ds   = FaceDataset(cfg["data"].get("val_dir", cfg["data"]["train_dir"]),
                           transform=val_tf)

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg["training"]["batch_size"],
        shuffle=True,
        num_workers=cfg["training"]["num_workers"],
        pin_memory=device.type == "cuda",
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg["training"]["batch_size"],
        shuffle=False,
        num_workers=cfg["training"]["num_workers"],
    )

    num_classes = len(train_ds.class_to_idx)
    logger.info(f"Training on {num_classes} identities")

    # ── Models ──────────────────────────────────────────────────────────────
    model   = FaceEmbeddingNet(
        backbone       = cfg["model"]["backbone"],
        embedding_size = cfg["model"]["embedding_size"],
        pretrained     = cfg["model"].get("pretrained", True),
    ).to(device)

    arcface = ArcFaceLoss(
        embedding_size = cfg["model"]["embedding_size"],
        num_classes    = num_classes,
        scale          = cfg["arcface_loss"]["scale"],
        margin         = cfg["arcface_loss"]["margin"],
    ).to(device)

    # ── Optimiser ───────────────────────────────────────────────────────────
    params = list(model.parameters()) + list(arcface.parameters())
    optimizer = optim.SGD(
        params,
        lr           = cfg["training"]["learning_rate"],
        momentum     = cfg["training"]["momentum"],
        weight_decay = cfg["training"]["weight_decay"],
    )
    scheduler = optim.lr_scheduler.MultiStepLR(
        optimizer,
        milestones = cfg["training"]["lr_milestones"],
        gamma      = cfg["training"]["lr_gamma"],
    )
    scaler = GradScaler() if use_amp else None

    # ── Resume ──────────────────────────────────────────────────────────────
    start_epoch = 0
    best_loss   = float("inf")
    history     = []

    if resume and Path(resume).exists():
        ckpt = torch.load(resume, map_location=device)
        model.load_state_dict(ckpt["model"])
        arcface.load_state_dict(ckpt["arcface"])
        optimizer.load_state_dict(ckpt["optimizer"])
        scheduler.load_state_dict(ckpt["scheduler"])
        start_epoch = ckpt["epoch"]
        best_loss   = ckpt.get("best_loss", best_loss)
        history     = ckpt.get("history", [])
        logger.info(f"Resumed from epoch {start_epoch}")

    # ── Output ──────────────────────────────────────────────────────────────
    out_dir = Path(cfg["output"]["checkpoint_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Training ────────────────────────────────────────────────────────────
    logger.info(f"Starting training for {cfg['training']['epochs']} epochs")
    epochs = cfg["training"]["epochs"]
    save_every = cfg["output"].get("save_every_n_epochs", 5)

    for epoch in range(start_epoch, epochs):
        # Train
        model.train()
        arcface.train()
        train_loss = 0.0
        t0 = time.time()

        for imgs, labels in tqdm(train_loader, desc=f"Ep {epoch+1}/{epochs} train"):
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()

            if use_amp:
                with autocast():
                    emb  = model(imgs)
                    loss = arcface(emb, labels)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(params, max_norm=5.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                emb  = model(imgs)
                loss = arcface(emb, labels)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(params, max_norm=5.0)
                optimizer.step()

            train_loss += loss.item()

        train_loss /= len(train_loader)
        scheduler.step()

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for imgs, labels in tqdm(val_loader, desc=f"Ep {epoch+1}/{epochs} val"):
                imgs, labels = imgs.to(device), labels.to(device)
                emb  = model(imgs)
                loss = arcface(emb, labels)
                val_loss += loss.item()
        val_loss /= max(len(val_loader), 1)

        elapsed = time.time() - t0
        lr_now  = scheduler.get_last_lr()[0]
        row = {
            "epoch": epoch + 1,
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4),
            "lr": lr_now,
            "time_s": round(elapsed, 1),
        }
        history.append(row)
        logger.info(f"Epoch {epoch+1:3d} | train={train_loss:.4f} "
                    f"val={val_loss:.4f} | lr={lr_now:.2e} | {elapsed:.0f}s")

        # Save best
        if val_loss < best_loss:
            best_loss = val_loss
            torch.save({
                "epoch":     epoch + 1,
                "model":     model.state_dict(),
                "arcface":   arcface.state_dict(),
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "best_loss": best_loss,
                "history":   history,
                "class_to_idx": train_ds.class_to_idx,
                "config":    cfg,
            }, out_dir / "best.pth")
            logger.info(f"  ✅ Best model saved (val_loss={best_loss:.4f})")

        # Periodic checkpoint
        if (epoch + 1) % save_every == 0:
            torch.save({
                "epoch":     epoch + 1,
                "model":     model.state_dict(),
                "arcface":   arcface.state_dict(),
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "best_loss": best_loss,
                "history":   history,
                "class_to_idx": train_ds.class_to_idx,
            }, out_dir / f"epoch_{epoch+1:04d}.pth")

    # Save final + export for inference
    torch.save(model.state_dict(), out_dir / "final_weights.pth")

    # Export to ONNX (for production deployment without PyTorch)
    try:
        model.eval()
        dummy = torch.randn(1, 3, 112, 112).to(device)
        torch.onnx.export(
            model, dummy,
            str(out_dir / "arcface.onnx"),
            input_names  = ["face_image"],
            output_names = ["embedding"],
            dynamic_axes = {"face_image": {0: "batch"}, "embedding": {0: "batch"}},
            opset_version = 14,
        )
        logger.info(f"ONNX model exported → {out_dir}/arcface.onnx")
    except Exception as e:
        logger.warning(f"ONNX export failed: {e}")

    # Save history
    with open(out_dir / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)

    logger.info(f"Training complete. Best val loss: {best_loss:.4f}")
    return history


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",    default=None,
                        help="Path to YAML config file (recommended)")
    parser.add_argument("--data_dir",  default="./data/aligned")
    parser.add_argument("--output_dir",default="./checkpoints/arcface")
    parser.add_argument("--backbone",  default="resnet50",
                        choices=["resnet50", "resnet100", "mobilenetv3"])
    parser.add_argument("--epochs",    type=int,   default=50)
    parser.add_argument("--batch_size",type=int,   default=32)
    parser.add_argument("--lr",        type=float, default=0.1)
    parser.add_argument("--resume",    default=None,
                        help="Path to checkpoint to resume from")
    args = parser.parse_args()

    # Build config dict
    if args.config:
        import yaml
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
    else:
        cfg = {
            "model": {
                "backbone": args.backbone,
                "embedding_size": 512,
                "pretrained": True,
            },
            "arcface_loss": {"scale": 64.0, "margin": 0.5},
            "training": {
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "num_workers": 4,
                "learning_rate": args.lr,
                "momentum": 0.9,
                "weight_decay": 5e-4,
                "lr_milestones": [20, 35, 45],
                "lr_gamma": 0.1,
                "mixed_precision": True,
            },
            "data": {
                "train_dir": args.data_dir + "/train",
                "val_dir":   args.data_dir + "/val",
                "img_size": 112,
                "augment": True,
            },
            "output": {
                "checkpoint_dir": args.output_dir,
                "save_every_n_epochs": 5,
            },
        }

    train(cfg, resume=args.resume)
