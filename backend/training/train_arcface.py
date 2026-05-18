"""
ArcFace Fine-tuning Script
Fine-tune ArcFace on Indian children's face dataset for better accuracy.

Usage:
    python training/train_arcface.py --data_dir data/raw/faces --epochs 30

Architecture:
    Backbone: ResNet-50 or MobileNetV3 (lightweight for mobile inference)
    Loss: ArcFace (Additive Angular Margin Loss)
    Optimizer: SGD with cosine LR schedule

Dataset format expected:
    data/raw/faces/
        person_001/
            img1.jpg
            img2.jpg
        person_002/
            ...
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import torchvision.transforms as T
import torchvision.datasets as datasets
import torchvision.models as models
import numpy as np
import math, os, argparse, logging
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ── ArcFace Loss ──────────────────────────────────────────────────────────────

class ArcFaceLoss(nn.Module):
    """
    ArcFace: Additive Angular Margin Loss for face recognition.
    Paper: https://arxiv.org/abs/1801.07698

    Margin (m): 0.5 radians (~28.6°)
    Scale (s): 64
    """
    def __init__(self, in_features: int, num_classes: int, s: float = 64.0, m: float = 0.5):
        super().__init__()
        self.s = s
        self.m = m
        self.weight = nn.Parameter(torch.FloatTensor(num_classes, in_features))
        nn.init.xavier_uniform_(self.weight)
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m

    def forward(self, input: torch.Tensor, label: torch.Tensor) -> torch.Tensor:
        # Normalize weights and input
        cosine = nn.functional.linear(
            nn.functional.normalize(input),
            nn.functional.normalize(self.weight),
        )
        sine = torch.sqrt(1.0 - torch.pow(cosine, 2))
        phi = cosine * self.cos_m - sine * self.sin_m  # cos(θ + m)
        phi = torch.where(cosine > self.th, phi, cosine - self.mm)

        one_hot = torch.zeros(cosine.size(), device=DEVICE)
        one_hot.scatter_(1, label.view(-1, 1).long(), 1)

        output = (one_hot * phi) + ((1.0 - one_hot) * cosine)
        output *= self.s
        return nn.functional.cross_entropy(output, label)


# ── Backbone ──────────────────────────────────────────────────────────────────

class FaceEmbedder(nn.Module):
    """
    Face embedding network.
    Output: 512-dim L2-normalized embedding vector.
    """
    def __init__(self, embedding_dim: int = 512, backbone: str = "resnet50"):
        super().__init__()
        if backbone == "resnet50":
            base = models.resnet50(pretrained=True)
            in_features = base.fc.in_features
            base.fc = nn.Identity()
            self.backbone = base
        elif backbone == "mobilenet":
            base = models.mobilenet_v3_small(pretrained=True)
            in_features = base.classifier[-1].in_features
            base.classifier[-1] = nn.Identity()
            self.backbone = base
            in_features = 576  # MobileNetV3-small
        else:
            raise ValueError(f"Unknown backbone: {backbone}")

        self.neck = nn.Sequential(
            nn.BatchNorm1d(in_features),
            nn.Linear(in_features, embedding_dim),
            nn.BatchNorm1d(embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.backbone(x)
        emb = self.neck(feat)
        return nn.functional.normalize(emb, p=2, dim=1)  # L2 normalize


# ── Data Augmentation ─────────────────────────────────────────────────────────

def get_transforms(train: bool = True):
    if train:
        return T.Compose([
            T.Resize((160, 160)),
            T.RandomHorizontalFlip(),
            T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
            T.RandomRotation(10),
            T.ToTensor(),
            T.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
        ])
    return T.Compose([
        T.Resize((160, 160)),
        T.ToTensor(),
        T.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    ])


# ── Training ──────────────────────────────────────────────────────────────────

def train(args):
    os.makedirs(args.output_dir, exist_ok=True)

    # Load dataset
    train_dataset = datasets.ImageFolder(args.data_dir, transform=get_transforms(train=True))
    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size,
        shuffle=True, num_workers=4, pin_memory=True,
    )
    num_classes = len(train_dataset.classes)
    logger.info(f"Dataset: {len(train_dataset)} images | {num_classes} identities")

    if num_classes < 2:
        logger.error("Need at least 2 identity folders in data_dir")
        return

    # Models
    model = FaceEmbedder(embedding_dim=512, backbone=args.backbone).to(DEVICE)
    arc_loss = ArcFaceLoss(in_features=512, num_classes=num_classes).to(DEVICE)

    optimizer = optim.SGD(
        list(model.parameters()) + list(arc_loss.parameters()),
        lr=args.lr, momentum=0.9, weight_decay=5e-4,
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_loss = float("inf")

    for epoch in range(args.epochs):
        model.train()
        total_loss, correct, total = 0.0, 0, 0

        for batch_idx, (images, labels) in enumerate(train_loader):
            images, labels = images.to(DEVICE), labels.to(DEVICE)

            optimizer.zero_grad()
            embeddings = model(images)
            loss = arc_loss(embeddings, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            total += labels.size(0)

            if batch_idx % 20 == 0:
                logger.info(
                    f"Epoch [{epoch+1}/{args.epochs}] "
                    f"[{batch_idx*len(images)}/{len(train_dataset)}] "
                    f"Loss: {loss.item():.4f} LR: {scheduler.get_last_lr()[0]:.6f}"
                )

        scheduler.step()
        avg_loss = total_loss / len(train_loader)
        logger.info(f"✅ Epoch {epoch+1} complete | Avg Loss: {avg_loss:.4f}")

        # Save best
        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save({
                "epoch": epoch + 1,
                "model_state_dict": model.state_dict(),
                "loss": best_loss,
                "num_classes": num_classes,
                "backbone": args.backbone,
            }, f"{args.output_dir}/best_arcface.pth")
            logger.info(f"💾 Best model saved (loss={best_loss:.4f})")

    # Export to ONNX for mobile deployment
    model.eval()
    dummy_input = torch.randn(1, 3, 160, 160, device=DEVICE)
    torch.onnx.export(
        model, dummy_input,
        f"{args.output_dir}/arcface_mobile.onnx",
        export_params=True,
        opset_version=11,
        input_names=["face_image"],
        output_names=["embedding"],
        dynamic_axes={"face_image": {0: "batch_size"}},
    )
    logger.info(f"📱 ONNX model exported for mobile: {args.output_dir}/arcface_mobile.onnx")


# ── Evaluation: Compute TAR@FAR ───────────────────────────────────────────────

def evaluate_model(model_path: str, test_pairs_csv: str):
    """
    Compute TAR (True Acceptance Rate) at FAR (False Acceptance Rate) = 0.001
    Standard face verification metric.
    """
    import pandas as pd
    from sklearn.metrics import roc_curve

    checkpoint = torch.load(model_path, map_location=DEVICE)
    model = FaceEmbedder(embedding_dim=512, backbone=checkpoint["backbone"]).to(DEVICE)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    transform = get_transforms(train=False)
    pairs_df = pd.read_csv(test_pairs_csv)  # columns: img1, img2, same_person (0/1)

    sims, labels = [], []
    for _, row in pairs_df.iterrows():
        img1 = transform(Image.open(row["img1"])).unsqueeze(0).to(DEVICE)
        img2 = transform(Image.open(row["img2"])).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            e1 = model(img1).cpu().numpy().flatten()
            e2 = model(img2).cpu().numpy().flatten()
        sim = float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2)))
        sims.append(sim)
        labels.append(int(row["same_person"]))

    fpr, tpr, thresholds = roc_curve(labels, sims)
    # TAR @ FAR=0.1%
    idx = np.searchsorted(fpr, 0.001)
    tar = tpr[idx] if idx < len(tpr) else tpr[-1]
    logger.info(f"TAR @ FAR=0.1%: {tar:.4f}")
    return tar


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune ArcFace for child face recognition")
    parser.add_argument("--data_dir", default="data/raw/faces", help="ImageFolder-style dataset")
    parser.add_argument("--output_dir", default="data/models/arcface", help="Output directory")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--backbone", choices=["resnet50", "mobilenet"], default="resnet50")
    args = parser.parse_args()
    train(args)
