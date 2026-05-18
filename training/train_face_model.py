"""
Model Training Script
Fine-tune ArcFace / FaceNet on custom dataset of missing children.
Run: python training/train_face_model.py --dataset data/faces --epochs 30
"""

import argparse
import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from PIL import Image
import logging
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─── Dataset ──────────────────────────────────────────────────────────────────

class FaceDataset(Dataset):
    """
    Expected folder structure:
    data/faces/
      person_001/
        img1.jpg
        img2.jpg
      person_002/
        img1.jpg
    """
    def __init__(self, root: str, transform=None):
        self.samples = []
        self.labels = []
        self.class_to_idx = {}
        root_path = Path(root)
        for idx, person_dir in enumerate(sorted(root_path.iterdir())):
            if person_dir.is_dir():
                self.class_to_idx[person_dir.name] = idx
                for img_path in person_dir.glob("*.jpg"):
                    self.samples.append(str(img_path))
                    self.labels.append(idx)
                for img_path in person_dir.glob("*.png"):
                    self.samples.append(str(img_path))
                    self.labels.append(idx)
        self.transform = transform
        logger.info(f"Dataset: {len(self.samples)} images, {len(self.class_to_idx)} identities")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img = Image.open(self.samples[idx]).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, self.labels[idx]


# ─── ArcFace Loss ─────────────────────────────────────────────────────────────

class ArcFaceLoss(nn.Module):
    """ArcFace: Additive Angular Margin Loss."""
    def __init__(self, in_features: int, num_classes: int, s=64.0, m=0.50):
        super().__init__()
        import math
        self.s = s
        self.m = m
        self.weight = nn.Parameter(torch.FloatTensor(num_classes, in_features))
        nn.init.xavier_uniform_(self.weight)
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m

    def forward(self, input, label):
        import math
        cosine = nn.functional.linear(
            nn.functional.normalize(input),
            nn.functional.normalize(self.weight)
        )
        sine = torch.sqrt(1.0 - torch.pow(cosine, 2))
        phi = cosine * self.cos_m - sine * self.sin_m
        phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, label.view(-1, 1).long(), 1)
        output = (one_hot * phi) + ((1.0 - one_hot) * cosine)
        output *= self.s
        return nn.functional.cross_entropy(output, label)


# ─── Model ───────────────────────────────────────────────────────────────────

def get_model(num_classes: int, pretrained: bool = True):
    try:
        from facenet_pytorch import InceptionResnetV1
        backbone = InceptionResnetV1(pretrained="vggface2" if pretrained else None, classify=False)
        embedding_dim = 512
        logger.info("Using FaceNet backbone (InceptionResnetV1)")
    except ImportError:
        from torchvision.models import resnet50
        backbone = resnet50(pretrained=pretrained)
        embedding_dim = backbone.fc.in_features
        backbone.fc = nn.Linear(embedding_dim, 512)
        embedding_dim = 512
        logger.info("Using ResNet-50 backbone")

    arc_loss = ArcFaceLoss(embedding_dim, num_classes)
    return backbone, arc_loss


# ─── Training Loop ────────────────────────────────────────────────────────────

def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Training on {device}")

    transform = transforms.Compose([
        transforms.Resize((160, 160)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    ])

    dataset = FaceDataset(args.dataset, transform=transform)
    if len(dataset) == 0:
        logger.error("No training images found. Check dataset path.")
        return

    train_size = int(0.9 * len(dataset))
    val_size = len(dataset) - train_size
    train_ds, val_ds = torch.utils.data.random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=2)

    num_classes = len(dataset.class_to_idx)
    backbone, criterion = get_model(num_classes, pretrained=True)
    backbone = backbone.to(device)
    criterion = criterion.to(device)

    optimizer = optim.AdamW(
        list(backbone.parameters()) + list(criterion.parameters()),
        lr=args.lr,
        weight_decay=5e-4
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_loss = float("inf")
    os.makedirs(args.output, exist_ok=True)

    for epoch in range(args.epochs):
        backbone.train()
        train_loss = 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            embeddings = backbone(imgs)
            loss = criterion(embeddings, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        backbone.eval()
        val_loss = 0.0
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                embeddings = backbone(imgs)
                loss = criterion(embeddings, labels)
                val_loss += loss.item()

        avg_train = train_loss / len(train_loader)
        avg_val = val_loss / len(val_loader)
        scheduler.step()
        logger.info(f"Epoch {epoch+1}/{args.epochs} | Train: {avg_train:.4f} | Val: {avg_val:.4f}")

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            save_path = os.path.join(args.output, "best_face_model.pt")
            torch.save({
                "epoch": epoch + 1,
                "model_state": backbone.state_dict(),
                "val_loss": avg_val,
                "num_classes": num_classes,
                "class_to_idx": dataset.class_to_idx,
            }, save_path)
            logger.info(f"  -> Saved best model to {save_path}")

    # Export ONNX for faster inference
    logger.info("Exporting ONNX model...")
    backbone.eval()
    dummy = torch.randn(1, 3, 160, 160).to(device)
    onnx_path = os.path.join(args.output, "face_model.onnx")
    torch.onnx.export(
        backbone, dummy, onnx_path,
        input_names=["input"], output_names=["embedding"],
        dynamic_axes={"input": {0: "batch_size"}, "embedding": {0: "batch_size"}},
        opset_version=12
    )
    logger.info(f"ONNX model saved: {onnx_path}")

    # Save class map
    with open(os.path.join(args.output, "class_map.json"), "w") as f:
        json.dump(dataset.class_to_idx, f)
    logger.info("Training complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train face recognition model")
    parser.add_argument("--dataset", default="data/faces", help="Path to face dataset")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--output", default="models/", help="Output directory for saved models")
    args = parser.parse_args()
    train(args)
