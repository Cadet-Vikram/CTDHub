"""
Age Progression GAN - Training Script
Architecture: Conditional GAN with age embedding
Based on: CAAE (Conditional Adversarial Autoencoder) for face aging

Usage:
    python training/train_age_gan.py --data_dir data/raw/faces --epochs 100

Dataset recommendation: CACD (Cross-Age Celebrity Dataset) or UTKFace
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as T
from torchvision.utils import save_image
import numpy as np
from PIL import Image
import os, argparse, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
AGE_GROUPS = [
    (0, 5, "0-5"),
    (6, 12, "6-12"),
    (13, 18, "13-18"),
    (19, 30, "19-30"),
    (31, 50, "31-50"),
]
NUM_AGE_GROUPS = len(AGE_GROUPS)
LATENT_DIM = 128
IMG_SIZE = 128
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def age_to_group(age: int) -> int:
    for i, (lo, hi, _) in enumerate(AGE_GROUPS):
        if lo <= age <= hi:
            return i
    return NUM_AGE_GROUPS - 1


# ── Dataset ──────────────────────────────────────────────────────────────────

class FaceAgeDataset(Dataset):
    """
    Expected directory structure:
    data/raw/faces/
        0001/
            child_5.jpg    ← filename must contain age or use metadata CSV
            adult_30.jpg
        0002/
            ...

    Or use UTKFace format: [age]_[gender]_[race]_[date].jpg
    """
    def __init__(self, data_dir: str, transform=None):
        self.samples = []
        self.transform = transform or T.Compose([
            T.Resize((IMG_SIZE, IMG_SIZE)),
            T.ToTensor(),
            T.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
        ])

        data_path = Path(data_dir)
        for img_path in data_path.rglob("*.jpg"):
            # Try UTKFace naming convention: age_gender_race_datetime.jpg
            try:
                age = int(img_path.stem.split("_")[0])
                self.samples.append((str(img_path), age))
            except (ValueError, IndexError):
                pass

        logger.info(f"Dataset loaded: {len(self.samples)} samples from {data_dir}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, age = self.samples[idx]
        img = Image.open(img_path).convert("RGB")
        img_tensor = self.transform(img)
        age_group = torch.tensor(age_to_group(age), dtype=torch.long)
        return img_tensor, age_group


# ── Model Architecture ────────────────────────────────────────────────────────

class Encoder(nn.Module):
    """Encodes face image → latent vector"""
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 64, 4, 2, 1),   nn.LeakyReLU(0.2),
            nn.Conv2d(64, 128, 4, 2, 1), nn.BatchNorm2d(128), nn.LeakyReLU(0.2),
            nn.Conv2d(128, 256, 4, 2, 1),nn.BatchNorm2d(256), nn.LeakyReLU(0.2),
            nn.Conv2d(256, 512, 4, 2, 1),nn.BatchNorm2d(512), nn.LeakyReLU(0.2),
            nn.Flatten(),
            nn.Linear(512 * 8 * 8, LATENT_DIM),
        )

    def forward(self, x):
        return self.net(x)


class Generator(nn.Module):
    """Generates age-progressed face from latent + age embedding"""
    def __init__(self):
        super().__init__()
        self.age_embed = nn.Embedding(NUM_AGE_GROUPS, 16)
        self.fc = nn.Linear(LATENT_DIM + 16, 512 * 8 * 8)
        self.net = nn.Sequential(
            nn.ConvTranspose2d(512, 256, 4, 2, 1), nn.BatchNorm2d(256), nn.ReLU(),
            nn.ConvTranspose2d(256, 128, 4, 2, 1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.ConvTranspose2d(128, 64, 4, 2, 1),  nn.BatchNorm2d(64),  nn.ReLU(),
            nn.ConvTranspose2d(64, 3, 4, 2, 1),
            nn.Tanh(),
        )

    def forward(self, z, target_age_group):
        age_emb = self.age_embed(target_age_group)
        x = torch.cat([z, age_emb], dim=1)
        x = self.fc(x).view(-1, 512, 8, 8)
        return self.net(x)


class Discriminator(nn.Module):
    """Discriminates real vs fake + classifies age group"""
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, 4, 2, 1),   nn.LeakyReLU(0.2),
            nn.Conv2d(64, 128, 4, 2, 1), nn.BatchNorm2d(128), nn.LeakyReLU(0.2),
            nn.Conv2d(128, 256, 4, 2, 1),nn.BatchNorm2d(256), nn.LeakyReLU(0.2),
            nn.Conv2d(256, 512, 4, 2, 1),nn.BatchNorm2d(512), nn.LeakyReLU(0.2),
            nn.Flatten(),
        )
        self.real_fake = nn.Linear(512 * 8 * 8, 1)
        self.age_class = nn.Linear(512 * 8 * 8, NUM_AGE_GROUPS)

    def forward(self, x):
        feat = self.features(x)
        return self.real_fake(feat), self.age_class(feat)


# ── Training Loop ─────────────────────────────────────────────────────────────

def train(args):
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(f"{args.output_dir}/samples", exist_ok=True)

    dataset = FaceAgeDataset(args.data_dir)
    if len(dataset) == 0:
        logger.error("No training data found! Add face images to data/raw/faces/")
        logger.info("Download UTKFace dataset: https://susanqq.github.io/UTKFace/")
        return

    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=2)

    encoder = Encoder().to(DEVICE)
    generator = Generator().to(DEVICE)
    discriminator = Discriminator().to(DEVICE)

    opt_EG = optim.Adam(
        list(encoder.parameters()) + list(generator.parameters()),
        lr=args.lr, betas=(0.5, 0.999)
    )
    opt_D = optim.Adam(discriminator.parameters(), lr=args.lr, betas=(0.5, 0.999))

    adv_loss = nn.BCEWithLogitsLoss()
    age_loss = nn.CrossEntropyLoss()
    recon_loss = nn.L1Loss()

    logger.info(f"Training on {DEVICE} | {len(dataset)} samples | {args.epochs} epochs")

    for epoch in range(args.epochs):
        for batch_idx, (real_imgs, age_groups) in enumerate(loader):
            real_imgs = real_imgs.to(DEVICE)
            age_groups = age_groups.to(DEVICE)
            bs = real_imgs.size(0)

            real_labels = torch.ones(bs, 1, device=DEVICE)
            fake_labels = torch.zeros(bs, 1, device=DEVICE)

            # ── Train Discriminator ────────────────────────
            opt_D.zero_grad()
            z = encoder(real_imgs)

            # Random target age for generation
            target_ages = torch.randint(0, NUM_AGE_GROUPS, (bs,), device=DEVICE)
            fake_imgs = generator(z, target_ages)

            d_real, d_age_real = discriminator(real_imgs)
            d_fake, _           = discriminator(fake_imgs.detach())

            loss_D = (
                adv_loss(d_real, real_labels) +
                adv_loss(d_fake, fake_labels) +
                age_loss(d_age_real, age_groups)
            )
            loss_D.backward()
            opt_D.step()

            # ── Train Encoder + Generator ──────────────────
            opt_EG.zero_grad()
            z = encoder(real_imgs)
            recon = generator(z, age_groups)
            fake_prog = generator(z, target_ages)
            d_fake2, d_age_fake = discriminator(fake_prog)

            loss_EG = (
                adv_loss(d_fake2, real_labels) * 1.0 +
                age_loss(d_age_fake, target_ages) * 0.5 +
                recon_loss(recon, real_imgs) * 10.0  # Strong reconstruction
            )
            loss_EG.backward()
            opt_EG.step()

            if batch_idx % 50 == 0:
                logger.info(
                    f"Epoch [{epoch+1}/{args.epochs}] Batch [{batch_idx}/{len(loader)}] "
                    f"D_loss: {loss_D.item():.4f} EG_loss: {loss_EG.item():.4f}"
                )

        # Save samples every 10 epochs
        if (epoch + 1) % 10 == 0:
            with torch.no_grad():
                sample_z = encoder(real_imgs[:8])
                samples = []
                for ag in range(NUM_AGE_GROUPS):
                    age_t = torch.full((8,), ag, dtype=torch.long, device=DEVICE)
                    samples.append(generator(sample_z, age_t))
                grid = torch.cat(samples, dim=0)
                save_image(
                    grid * 0.5 + 0.5,
                    f"{args.output_dir}/samples/epoch_{epoch+1}.png",
                    nrow=8,
                )
            # Save checkpoint
            torch.save({
                "encoder": encoder.state_dict(),
                "generator": generator.state_dict(),
                "discriminator": discriminator.state_dict(),
                "epoch": epoch + 1,
            }, f"{args.output_dir}/checkpoint_epoch_{epoch+1}.pth")

    # Save final model
    torch.save({
        "encoder": encoder.state_dict(),
        "generator": generator.state_dict(),
    }, f"{args.output_dir}/age_progression_model.pth")
    logger.info(f"✅ Model saved to {args.output_dir}/age_progression_model.pth")


# ── Inference ─────────────────────────────────────────────────────────────────

def generate_aged_face(image_path: str, target_age: int, model_path: str) -> np.ndarray:
    """
    Given a child's photo, generate what they might look like at target_age.

    Args:
        image_path: Path to child's face image
        target_age: Age to progress to (e.g., 18 for age progression)
        model_path: Path to trained model checkpoint

    Returns:
        numpy array of generated aged face (RGB, 128x128)
    """
    transform = T.Compose([
        T.Resize((IMG_SIZE, IMG_SIZE)),
        T.ToTensor(),
        T.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    ])

    encoder = Encoder().to(DEVICE)
    generator = Generator().to(DEVICE)

    checkpoint = torch.load(model_path, map_location=DEVICE)
    encoder.load_state_dict(checkpoint["encoder"])
    generator.load_state_dict(checkpoint["generator"])
    encoder.eval()
    generator.eval()

    img = Image.open(image_path).convert("RGB")
    img_tensor = transform(img).unsqueeze(0).to(DEVICE)
    target_group = torch.tensor([age_to_group(target_age)], device=DEVICE)

    with torch.no_grad():
        z = encoder(img_tensor)
        aged = generator(z, target_group)

    # Convert to numpy
    aged_np = aged.squeeze().cpu().numpy().transpose(1, 2, 0)
    aged_np = ((aged_np * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    return aged_np


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Age Progression GAN")
    parser.add_argument("--data_dir", default="data/raw/faces", help="Path to face images (UTKFace format)")
    parser.add_argument("--output_dir", default="data/models/age_gan", help="Where to save checkpoints")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.0002)
    args = parser.parse_args()
    train(args)
