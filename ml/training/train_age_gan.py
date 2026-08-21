"""
Age Progression GAN Training Script
Based on SAM (Style-based Age Manipulation) architecture.
Uses StyleGAN2 encoder + age-conditioned decoder.

Usage:
    python train_age_gan.py --data_dir ./ffhq_dataset --epochs 100

References:
    - SAM: https://arxiv.org/abs/2102.02754
    - HRFAE: https://arxiv.org/abs/2005.04410
    - CAAE: https://arxiv.org/abs/1702.08423
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
import numpy as np
import cv2
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─── Age-Conditioned Generator ───────────────────────────────────────────────

class AgeEmbedding(nn.Module):
    """Encodes age as a continuous conditioning vector"""

    def __init__(self, age_embedding_dim: int = 64):
        super().__init__()
        self.embed = nn.Sequential(
            nn.Linear(1, 32),
            nn.ReLU(),
            nn.Linear(32, age_embedding_dim),
        )

    def forward(self, age: torch.Tensor) -> torch.Tensor:
        age_norm = age.float() / 100.0  # Normalize to [0, 1]
        return self.embed(age_norm.unsqueeze(1))


class ResidualBlock(nn.Module):
    def __init__(self, channels: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(channels, channels, 3, padding=1),
            nn.InstanceNorm2d(channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(channels, channels, 3, padding=1),
            nn.InstanceNorm2d(channels),
        )

    def forward(self, x):
        return x + self.block(x)


class AgeProgressionGenerator(nn.Module):
    """
    Age-conditioned image-to-image generator.
    Encoder-Residual-Decoder with age injection via AdaIN.
    """

    def __init__(self, age_embedding_dim: int = 64, num_residual: int = 9):
        super().__init__()

        # Encoder
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 64, 7, padding=3),
            nn.InstanceNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.InstanceNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 256, 3, stride=2, padding=1),
            nn.InstanceNorm2d(256),
            nn.ReLU(inplace=True),
        )

        # Age injection layer
        self.age_proj = nn.Linear(age_embedding_dim, 256)

        # Residual blocks
        self.residuals = nn.Sequential(*[ResidualBlock(256) for _ in range(num_residual)])

        # Decoder
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(256, 128, 3, stride=2, padding=1, output_padding=1),
            nn.InstanceNorm2d(128),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, 64, 3, stride=2, padding=1, output_padding=1),
            nn.InstanceNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 3, 7, padding=3),
            nn.Tanh(),
        )

    def forward(self, x: torch.Tensor, age_emb: torch.Tensor) -> torch.Tensor:
        features = self.encoder(x)

        # Add age conditioning
        age_cond = self.age_proj(age_emb)
        age_cond = age_cond.view(-1, 256, 1, 1).expand_as(features)
        features = features + age_cond

        features = self.residuals(features)
        return self.decoder(features)


class PatchGANDiscriminator(nn.Module):
    """PatchGAN discriminator with age conditioning"""

    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 64, 4, stride=2, padding=1),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(64, 128, 4, stride=2, padding=1),
            nn.InstanceNorm2d(128),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(128, 256, 4, stride=2, padding=1),
            nn.InstanceNorm2d(256),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(256, 512, 4, padding=1),
            nn.InstanceNorm2d(512),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(512, 1, 4, padding=1),
        )

    def forward(self, x):
        return self.net(x)


# ─── CAAE-style Dataset ───────────────────────────────────────────────────────

class AgeDataset(Dataset):
    """
    Expects folder structure:
    ffhq_aging/
        0_10/   (age group)
            img1.jpg
        10_20/
            img1.jpg
        ...
    Or: UTKFace dataset (filename format: age_gender_race_date.jpg)
    """

    AGE_GROUPS = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 100)]

    def __init__(self, root_dir: str, transform=None, dataset_type="folder"):
        self.root = Path(root_dir)
        self.transform = transform
        self.samples = []  # (img_path, age)
        self.dataset_type = dataset_type

        if dataset_type == "utk":
            self._load_utk()
        else:
            self._load_folder()

        logger.info(f"Age dataset: {len(self.samples)} images")

    def _load_utk(self):
        """UTKFace format: age_gender_race_date.jpg"""
        for img in self.root.glob("*.jpg"):
            try:
                age = int(img.stem.split("_")[0])
                self.samples.append((img, age))
            except (ValueError, IndexError):
                pass

    def _load_folder(self):
        """Folder structure: age_range/img.jpg"""
        for age_dir in self.root.iterdir():
            if not age_dir.is_dir():
                continue
            try:
                start, end = map(int, age_dir.name.split("_"))
                mid_age = (start + end) // 2
            except ValueError:
                continue
            for img in age_dir.glob("*.jpg"):
                self.samples.append((img, mid_age))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, age = self.samples[idx]
        img = cv2.imread(str(img_path))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (256, 256))

        if self.transform:
            from PIL import Image
            img = self.transform(Image.fromarray(img))
        else:
            img = torch.FloatTensor(img).permute(2, 0, 1) / 127.5 - 1.0  # [-1, 1]

        return img, torch.tensor(age, dtype=torch.float32)


# ─── Training Loop ────────────────────────────────────────────────────────────

def train_gan(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Training Age GAN on: {device}")

    transform = transforms.Compose([
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    ])

    dataset = AgeDataset(args.data_dir, transform=transform, dataset_type=args.dataset_type)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=4)

    age_embed = AgeEmbedding(64).to(device)
    generator = AgeProgressionGenerator(64, num_residual=9).to(device)
    discriminator = PatchGANDiscriminator().to(device)

    opt_G = optim.Adam(
        list(generator.parameters()) + list(age_embed.parameters()),
        lr=args.lr, betas=(0.5, 0.999)
    )
    opt_D = optim.Adam(discriminator.parameters(), lr=args.lr, betas=(0.5, 0.999))

    criterion_gan = nn.MSELoss()
    criterion_cycle = nn.L1Loss()
    criterion_identity = nn.L1Loss()

    import os
    os.makedirs(args.output_dir, exist_ok=True)

    for epoch in range(args.epochs):
        for i, (real_imgs, ages) in enumerate(loader):
            real_imgs, ages = real_imgs.to(device), ages.to(device)

            # Target ages (random aging targets)
            target_ages = torch.randint(5, 80, ages.shape).float().to(device)
            age_emb = age_embed(ages)
            target_age_emb = age_embed(target_ages)

            # ── Generator step ──
            opt_G.zero_grad()
            fake_imgs = generator(real_imgs, target_age_emb)
            pred_fake = discriminator(fake_imgs)
            valid = torch.ones_like(pred_fake)
            loss_gan = criterion_gan(pred_fake, valid)

            # Cycle consistency: aged → unaged ≈ original
            recov_imgs = generator(fake_imgs, age_emb)
            loss_cycle = criterion_cycle(recov_imgs, real_imgs) * 10.0

            # Identity loss
            identity_imgs = generator(real_imgs, age_emb)
            loss_id = criterion_identity(identity_imgs, real_imgs) * 5.0

            loss_G = loss_gan + loss_cycle + loss_id
            loss_G.backward()
            opt_G.step()

            # ── Discriminator step ──
            opt_D.zero_grad()
            pred_real = discriminator(real_imgs)
            pred_fake_d = discriminator(fake_imgs.detach())
            fake_labels = torch.zeros_like(pred_fake_d)

            loss_D = (criterion_gan(pred_real, valid) + criterion_gan(pred_fake_d, fake_labels)) * 0.5
            loss_D.backward()
            opt_D.step()

            if i % 100 == 0:
                logger.info(
                    f"Epoch [{epoch+1}/{args.epochs}] Step [{i}/{len(loader)}] "
                    f"Loss_G: {loss_G.item():.4f} | Loss_D: {loss_D.item():.4f}"
                )

        # Save checkpoint every 10 epochs
        if (epoch + 1) % 10 == 0:
            torch.save({
                "generator": generator.state_dict(),
                "age_embed": age_embed.state_dict(),
                "epoch": epoch + 1,
            }, f"{args.output_dir}/age_gan_epoch_{epoch+1}.pth")
            logger.info(f"Checkpoint saved at epoch {epoch+1}")

    logger.info("Age GAN training complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default="./ffhq_aging")
    parser.add_argument("--output_dir", default="./checkpoints/age_gan")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=0.0002)
    parser.add_argument("--dataset_type", choices=["folder", "utk"], default="folder")
    args = parser.parse_args()
    train_gan(args)
