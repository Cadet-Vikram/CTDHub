"""
ArcFace Model Training Script
Trains a face recognition model using ArcFace loss on a custom dataset.

Usage:
    python train_arcface.py --data_dir ./dataset --epochs 50 --batch_size 32

Dataset Structure:
    dataset/
        person_1/
            img1.jpg
            img2.jpg
        person_2/
            img1.jpg
        ...
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from pathlib import Path
import numpy as np
import cv2
import argparse
import logging
import json
import math
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─── ArcFace Loss ────────────────────────────────────────────────────────────

class ArcFaceLoss(nn.Module):
    """
    ArcFace: Additive Angular Margin Loss
    Paper: https://arxiv.org/abs/1801.07698
    """

    def __init__(self, embedding_size: int, num_classes: int, scale: float = 64.0, margin: float = 0.5):
        super().__init__()
        self.scale = scale
        self.margin = margin
        self.weight = nn.Parameter(torch.FloatTensor(num_classes, embedding_size))
        nn.init.xavier_uniform_(self.weight)

        self.cos_margin = math.cos(margin)
        self.sin_margin = math.sin(margin)
        self.threshold = math.cos(math.pi - margin)
        self.mm = math.sin(math.pi - margin) * margin

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        # Normalize embeddings and weights
        embeddings = nn.functional.normalize(embeddings, p=2, dim=1)
        weight = nn.functional.normalize(self.weight, p=2, dim=1)

        cosine = nn.functional.linear(embeddings, weight)
        sine = torch.sqrt(1.0 - torch.clamp(cosine ** 2, 0, 1))

        # cos(theta + margin)
        phi = cosine * self.cos_margin - sine * self.sin_margin
        phi = torch.where(cosine > self.threshold, phi, cosine - self.mm)

        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1.0)

        output = one_hot * phi + (1.0 - one_hot) * cosine
        output *= self.scale

        return nn.functional.cross_entropy(output, labels)


# ─── Backbone ────────────────────────────────────────────────────────────────

class FaceEmbeddingNet(nn.Module):
    """ResNet-50 backbone for face embedding extraction"""

    def __init__(self, embedding_size: int = 512):
        super().__init__()
        backbone = models.resnet50(pretrained=True)
        # Remove final FC layer
        self.features = nn.Sequential(*list(backbone.children())[:-1])
        self.embedding = nn.Sequential(
            nn.Flatten(),
            nn.BatchNorm1d(2048),
            nn.Linear(2048, embedding_size),
            nn.BatchNorm1d(embedding_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.embedding(x)
        return nn.functional.normalize(x, p=2, dim=1)


# ─── Dataset ─────────────────────────────────────────────────────────────────

class FaceDataset(Dataset):
    def __init__(self, root_dir: str, transform=None):
        self.root = Path(root_dir)
        self.transform = transform
        self.samples = []
        self.class_to_idx = {}

        for idx, person_dir in enumerate(sorted(self.root.iterdir())):
            if not person_dir.is_dir():
                continue
            self.class_to_idx[person_dir.name] = idx
            for img_path in person_dir.glob("*.jpg"):
                self.samples.append((img_path, idx))
            for img_path in person_dir.glob("*.png"):
                self.samples.append((img_path, idx))

        logger.info(f"Dataset: {len(self.samples)} images, {len(self.class_to_idx)} identities")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        img = cv2.imread(str(img_path))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (112, 112))

        if self.transform:
            from PIL import Image
            img = self.transform(Image.fromarray(img))
        else:
            img = torch.FloatTensor(img).permute(2, 0, 1) / 255.0

        return img, label


# ─── Training ────────────────────────────────────────────────────────────────

def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Training on: {device}")

    transform = transforms.Compose([
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]),
    ])

    dataset = FaceDataset(args.data_dir, transform=transform)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True,
                        num_workers=4, pin_memory=True)

    num_classes = len(dataset.class_to_idx)
    model = FaceEmbeddingNet(embedding_size=512).to(device)
    arcface = ArcFaceLoss(512, num_classes).to(device)

    optimizer = optim.SGD(
        list(model.parameters()) + list(arcface.parameters()),
        lr=args.lr, momentum=0.9, weight_decay=5e-4
    )
    scheduler = optim.lr_scheduler.MultiStepLR(
        optimizer, milestones=[20, 35, 45], gamma=0.1
    )

    best_loss = float("inf")
    history = []

    for epoch in range(args.epochs):
        model.train()
        arcface.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for images, labels in tqdm(loader, desc=f"Epoch {epoch+1}/{args.epochs}"):
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            embeddings = model(images)
            loss = arcface(embeddings, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            total += labels.size(0)

        avg_loss = total_loss / len(loader)
        scheduler.step()
        history.append({"epoch": epoch + 1, "loss": avg_loss})
        logger.info(f"Epoch {epoch+1}: Loss={avg_loss:.4f}, LR={scheduler.get_last_lr()[0]:.6f}")

        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save({
                "epoch": epoch + 1,
                "model_state": model.state_dict(),
                "arcface_state": arcface.state_dict(),
                "class_to_idx": dataset.class_to_idx,
                "loss": best_loss,
            }, f"{args.output_dir}/arcface_best.pth")
            logger.info(f"  ✅ Saved best model (loss={best_loss:.4f})")

    # Save final
    torch.save(model.state_dict(), f"{args.output_dir}/arcface_final.pth")
    with open(f"{args.output_dir}/training_history.json", "w") as f:
        json.dump(history, f, indent=2)
    logger.info("Training complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default="./dataset")
    parser.add_argument("--output_dir", default="./checkpoints")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.1)
    args = parser.parse_args()

    import os
    os.makedirs(args.output_dir, exist_ok=True)
    train(args)
