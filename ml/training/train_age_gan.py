"""
Age Progression GAN — Full Training Script
==========================================
Architecture: Encoder-Residual-Decoder Generator + PatchGAN Discriminator
Loss: Adversarial + Cycle-Consistency + Identity + Age Classification

Usage:
    python train_age_gan.py --config ../configs/age_gan_config.yaml
    python train_age_gan.py --data_dir ./data/utk_aligned --epochs 100
    python train_age_gan.py --config ../configs/age_gan_config.yaml --resume ./checkpoints/age_gan/epoch_050.pth
"""

import os
import json
import time
import logging
import argparse
import itertools
from pathlib import Path
from typing import Optional

import numpy as np
import cv2
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Generator Components
# ══════════════════════════════════════════════════════════════════════════════

class AgeEncoder(nn.Module):
    """Maps scalar age → 64-dim conditioning vector"""

    def __init__(self, dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(1, 32), nn.ReLU(),
            nn.Linear(32, dim), nn.ReLU(),
        )

    def forward(self, age: torch.Tensor) -> torch.Tensor:
        return self.net((age.float() / 100.0).unsqueeze(1))


class AdaptiveInstanceNorm(nn.Module):
    """AdaIN: inject age conditioning into feature maps"""

    def __init__(self, num_features: int, age_dim: int = 64):
        super().__init__()
        self.norm  = nn.InstanceNorm2d(num_features, affine=False)
        self.scale = nn.Linear(age_dim, num_features)
        self.shift = nn.Linear(age_dim, num_features)

    def forward(self, x: torch.Tensor, age_emb: torch.Tensor) -> torch.Tensor:
        B, C, H, W = x.shape
        scale = self.scale(age_emb).view(B, C, 1, 1)
        shift = self.shift(age_emb).view(B, C, 1, 1)
        return self.norm(x) * (1 + scale) + shift


class ResBlockAdaIN(nn.Module):
    """Residual block with AdaIN conditioning"""

    def __init__(self, channels: int, age_dim: int = 64):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1)
        self.adain1 = AdaptiveInstanceNorm(channels, age_dim)
        self.adain2 = AdaptiveInstanceNorm(channels, age_dim)
        self.relu   = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor, age_emb: torch.Tensor) -> torch.Tensor:
        res = self.relu(self.adain1(self.conv1(x), age_emb))
        res = self.adain2(self.conv2(res), age_emb)
        return x + res


class AgeProgressionGenerator(nn.Module):
    """
    Full generator: image + target_age → age-progressed image
    Architecture: Encoder → AdaIN Residual Blocks → Decoder
    """

    def __init__(self, n_residual: int = 9, age_dim: int = 64):
        super().__init__()
        self.age_encoder = AgeEncoder(age_dim)

        # Encoder: 3 → 256 channels
        self.enc = nn.Sequential(
            nn.ReflectionPad2d(3),
            nn.Conv2d(3, 64, 7), nn.InstanceNorm2d(64), nn.ReLU(True),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.InstanceNorm2d(128), nn.ReLU(True),
            nn.Conv2d(128, 256, 3, stride=2, padding=1),
            nn.InstanceNorm2d(256), nn.ReLU(True),
        )

        # Age-conditioned residual blocks
        self.res_blocks = nn.ModuleList(
            [ResBlockAdaIN(256, age_dim) for _ in range(n_residual)]
        )

        # Decoder: 256 → 3 channels
        self.dec = nn.Sequential(
            nn.ConvTranspose2d(256, 128, 3, stride=2, padding=1, output_padding=1),
            nn.InstanceNorm2d(128), nn.ReLU(True),
            nn.ConvTranspose2d(128, 64, 3, stride=2, padding=1, output_padding=1),
            nn.InstanceNorm2d(64), nn.ReLU(True),
            nn.ReflectionPad2d(3),
            nn.Conv2d(64, 3, 7),
            nn.Tanh(),
        )

    def forward(self, img: torch.Tensor, target_age: torch.Tensor) -> torch.Tensor:
        age_emb = self.age_encoder(target_age)
        feat    = self.enc(img)
        for block in self.res_blocks:
            feat = block(feat, age_emb)
        return self.dec(feat)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Discriminator
# ══════════════════════════════════════════════════════════════════════════════

class PatchGANDiscriminator(nn.Module):
    """
    70×70 PatchGAN: classifies overlapping image patches as real/fake.
    More effective than full-image discriminator for texture/detail.
    """

    def __init__(self, n_layers: int = 3):
        super().__init__()
        layers = [
            nn.Conv2d(3, 64, 4, stride=2, padding=1),
            nn.LeakyReLU(0.2, inplace=True),
        ]
        ch = 64
        for _ in range(n_layers - 1):
            layers += [
                nn.Conv2d(ch, ch * 2, 4, stride=2, padding=1),
                nn.InstanceNorm2d(ch * 2),
                nn.LeakyReLU(0.2, inplace=True),
            ]
            ch *= 2
        layers += [
            nn.Conv2d(ch, ch * 2, 4, padding=1),
            nn.InstanceNorm2d(ch * 2),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv2d(ch * 2, 1, 4, padding=1),
        ]
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Dataset
# ══════════════════════════════════════════════════════════════════════════════

class AgeDataset(Dataset):
    """
    UTKFace or folder-organised age dataset.
    UTK format: age_gender_race_datetime.jpg
    Folder format: 0_10/img.jpg, 10_20/img.jpg, ...
    """

    AGE_GROUPS = {"0_10":(0,10),"10_20":(10,20),"20_30":(20,30),
                  "30_40":(30,40),"40_50":(40,50),"50_60":(50,60),"60_100":(60,100)}

    def __init__(self, root: str, dataset_type: str = "utk",
                 transform=None, img_size: int = 256):
        self.root         = Path(root)
        self.transform    = transform
        self.img_size     = img_size
        self.samples      = []   # [(path, age_float)]

        if dataset_type == "utk":
            self._load_utk()
        else:
            self._load_folders()

        logger.info(f"Age dataset: {len(self.samples)} images")
        if not self.samples:
            logger.warning("No images found! Check your data directory.")

    def _load_utk(self):
        for p in self.root.glob("*.jpg"):
            try:
                age = int(p.stem.split("_")[0])
                if 0 <= age <= 100:
                    self.samples.append((p, float(age)))
            except (ValueError, IndexError):
                pass

    def _load_folders(self):
        for age_dir in self.root.iterdir():
            if not age_dir.is_dir() or age_dir.name not in self.AGE_GROUPS:
                continue
            lo, hi = self.AGE_GROUPS[age_dir.name]
            mid    = float((lo + hi) / 2)
            for img in age_dir.glob("*.jpg"):
                self.samples.append((img, mid))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, age = self.samples[idx]
        img = cv2.imread(str(path))
        if img is None:
            img = np.zeros((self.img_size, self.img_size, 3), np.uint8)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        if self.transform:
            from PIL import Image
            img = self.transform(Image.fromarray(img))
        else:
            img = cv2.resize(img, (self.img_size, self.img_size))
            img = torch.FloatTensor(img).permute(2, 0, 1) / 127.5 - 1.0

        return img, torch.tensor(age, dtype=torch.float32)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Loss Functions
# ══════════════════════════════════════════════════════════════════════════════

class GANLosses:
    def __init__(self, device):
        self.device    = device
        self.mse       = nn.MSELoss()
        self.l1        = nn.L1Loss()

    def adversarial(self, pred: torch.Tensor, is_real: bool) -> torch.Tensor:
        target = torch.ones_like(pred) if is_real else torch.zeros_like(pred)
        return self.mse(pred, target)

    def cycle(self, recovered: torch.Tensor, original: torch.Tensor) -> torch.Tensor:
        return self.l1(recovered, original)

    def identity(self, same_age_out: torch.Tensor, original: torch.Tensor) -> torch.Tensor:
        return self.l1(same_age_out, original)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Sample Saving (visual progress during training)
# ══════════════════════════════════════════════════════════════════════════════

def save_samples(generator, sample_imgs, sample_ages, epoch, sample_dir, device):
    """Save side-by-side original → aged comparison images"""
    sample_dir = Path(sample_dir)
    sample_dir.mkdir(parents=True, exist_ok=True)

    generator.eval()
    target_ages = [10.0, 20.0, 40.0, 60.0]

    with torch.no_grad():
        imgs = sample_imgs[:4].to(device)
        orig_ages = sample_ages[:4].to(device)

        rows = []
        for ta in target_ages:
            t_age  = torch.full((len(imgs),), ta, dtype=torch.float32, device=device)
            faked  = generator(imgs, t_age)
            # Denormalise: [-1,1] → [0,255]
            imgs_np = ((imgs.cpu().permute(0,2,3,1).numpy() + 1) * 127.5).clip(0,255).astype(np.uint8)
            fake_np = ((faked.cpu().permute(0,2,3,1).numpy() + 1) * 127.5).clip(0,255).astype(np.uint8)
            row = np.concatenate([np.concatenate([imgs_np[i], fake_np[i]], axis=1)
                                  for i in range(len(imgs))], axis=1)
            rows.append(row)

        grid = np.concatenate(rows, axis=0)
        grid_bgr = cv2.cvtColor(grid, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(sample_dir / f"epoch_{epoch:04d}.jpg"), grid_bgr)

    generator.train()


# ══════════════════════════════════════════════════════════════════════════════
# 6. Training Loop
# ══════════════════════════════════════════════════════════════════════════════

def train(cfg: dict, resume: Optional[str] = None):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Training Age GAN on: {device}")

    transform = transforms.Compose([
        transforms.Resize((cfg["model"]["image_size"], cfg["model"]["image_size"])),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    ])

    dataset = AgeDataset(
        cfg["data"]["train_dir"],
        dataset_type = cfg["data"].get("dataset_type", "utk"),
        transform    = transform,
        img_size     = cfg["model"]["image_size"],
    )
    if len(dataset) == 0:
        logger.error("Empty dataset! Add images first.")
        return

    loader = DataLoader(
        dataset,
        batch_size  = cfg["training"]["batch_size"],
        shuffle     = True,
        num_workers = cfg["training"]["num_workers"],
        drop_last   = True,
    )

    # Models
    G   = AgeProgressionGenerator(
        n_residual = cfg["model"]["generator_residual_blocks"],
        age_dim    = cfg["model"]["age_embedding_dim"],
    ).to(device)
    D   = PatchGANDiscriminator().to(device)
    losses = GANLosses(device)

    # Optimisers
    opt_G = optim.Adam(G.parameters(),
                       lr=cfg["training"]["lr_generator"],
                       betas=(cfg["training"]["beta1"],
                              cfg["training"]["beta2"]))
    opt_D = optim.Adam(D.parameters(),
                       lr=cfg["training"]["lr_discriminator"],
                       betas=(cfg["training"]["beta1"],
                              cfg["training"]["beta2"]))

    def lr_lambda(epoch):
        decay_start = cfg["training"]["decay_start_epoch"]
        n_epochs    = cfg["training"]["epochs"]
        if epoch < decay_start:
            return 1.0
        return max(0.0, 1.0 - (epoch - decay_start) / (n_epochs - decay_start))

    sched_G = optim.lr_scheduler.LambdaLR(opt_G, lr_lambda)
    sched_D = optim.lr_scheduler.LambdaLR(opt_D, lr_lambda)

    out_dir    = Path(cfg["output"]["checkpoint_dir"])
    sample_dir = Path(cfg["output"]["sample_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    start_epoch = 0
    history     = []
    w = cfg["loss_weights"]

    if resume and Path(resume).exists():
        ckpt        = torch.load(resume, map_location=device)
        G.load_state_dict(ckpt["G"])
        D.load_state_dict(ckpt["D"])
        opt_G.load_state_dict(ckpt["opt_G"])
        opt_D.load_state_dict(ckpt["opt_D"])
        start_epoch = ckpt["epoch"]
        history     = ckpt.get("history", [])
        logger.info(f"Resumed from epoch {start_epoch}")

    # Grab fixed samples for visual progress
    sample_imgs, sample_ages = next(iter(loader))

    logger.info(f"Training for {cfg['training']['epochs']} epochs | "
                f"{len(dataset)} images | batch={cfg['training']['batch_size']}")

    for epoch in range(start_epoch, cfg["training"]["epochs"]):
        G.train(); D.train()
        g_total = d_total = 0.0
        t0 = time.time()

        for real_imgs, real_ages in tqdm(loader, desc=f"GAN Ep {epoch+1}"):
            real_imgs  = real_imgs.to(device)
            real_ages  = real_ages.to(device)

            # Random target ages for this batch
            target_ages = torch.randint(5, 85, real_ages.shape, dtype=torch.float32).to(device)

            # ── Generator step ─────────────────────────────────────────────
            opt_G.zero_grad()
            aged_imgs = G(real_imgs, target_ages)

            # Adversarial loss
            loss_adv = losses.adversarial(D(aged_imgs), True) * w["adversarial"]

            # Cycle consistency: aged → re-age back to original age
            recov_imgs = G(aged_imgs, real_ages)
            loss_cyc   = losses.cycle(recov_imgs, real_imgs) * w["cycle_consistency"]

            # Identity loss: aging to same age shouldn't change much
            same_imgs  = G(real_imgs, real_ages)
            loss_id    = losses.identity(same_imgs, real_imgs) * w["identity"]

            loss_G = loss_adv + loss_cyc + loss_id
            loss_G.backward()
            opt_G.step()
            g_total += loss_G.item()

            # ── Discriminator step ─────────────────────────────────────────
            opt_D.zero_grad()
            loss_real = losses.adversarial(D(real_imgs), True)
            loss_fake = losses.adversarial(D(aged_imgs.detach()), False)
            loss_D    = (loss_real + loss_fake) * 0.5
            loss_D.backward()
            opt_D.step()
            d_total += loss_D.item()

        sched_G.step()
        sched_D.step()

        g_avg = g_total / len(loader)
        d_avg = d_total / len(loader)
        elapsed = time.time() - t0
        row = {"epoch": epoch+1, "loss_G": round(g_avg, 4),
               "loss_D": round(d_avg, 4), "time_s": round(elapsed, 1)}
        history.append(row)
        logger.info(f"Epoch {epoch+1:3d} | G={g_avg:.4f} D={d_avg:.4f} | {elapsed:.0f}s")

        save_every = cfg["output"].get("save_every_n_epochs", 10)
        if (epoch + 1) % save_every == 0:
            torch.save({
                "epoch": epoch + 1,
                "G": G.state_dict(), "D": D.state_dict(),
                "opt_G": opt_G.state_dict(), "opt_D": opt_D.state_dict(),
                "history": history,
            }, out_dir / f"epoch_{epoch+1:04d}.pth")
            save_samples(G, sample_imgs, sample_ages, epoch+1, sample_dir, device)
            logger.info(f"  Checkpoint + samples saved")

    # Final save
    torch.save({"G": G.state_dict(), "D": D.state_dict()},
               out_dir / "final.pth")
    torch.save(G.state_dict(), out_dir / "generator_final.pth")

    with open(out_dir / "training_history.json", "w") as f:
        json.dump(history, f, indent=2)

    logger.info("Age GAN training complete!")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",    default=None)
    parser.add_argument("--data_dir",  default="./data/utk_aligned")
    parser.add_argument("--output_dir",default="./checkpoints/age_gan")
    parser.add_argument("--epochs",    type=int, default=100)
    parser.add_argument("--batch_size",type=int, default=8)
    parser.add_argument("--resume",    default=None)
    args = parser.parse_args()

    if args.config:
        import yaml
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
    else:
        cfg = {
            "model": {"generator_residual_blocks": 9, "age_embedding_dim": 64, "image_size": 256},
            "loss_weights": {"adversarial": 1.0, "cycle_consistency": 10.0, "identity": 5.0},
            "training": {"epochs": args.epochs, "batch_size": args.batch_size, "num_workers": 4,
                         "lr_generator": 2e-4, "lr_discriminator": 2e-4,
                         "beta1": 0.5, "beta2": 0.999, "decay_start_epoch": 50},
            "data": {"train_dir": args.data_dir, "dataset_type": "utk", "img_size": 256},
            "output": {"checkpoint_dir": args.output_dir,
                       "sample_dir": args.output_dir + "/samples",
                       "save_every_n_epochs": 10},
        }

    train(cfg, resume=args.resume)
