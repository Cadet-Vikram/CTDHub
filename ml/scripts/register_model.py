"""
Model Registry
==============
After training, use this script to:
  1. Test a checkpoint on a sample image
  2. Copy checkpoint to backend/checkpoints/
  3. Update backend/models/face_model.py to load your weights

Usage:
    python register_model.py --checkpoint ./checkpoints/arcface/best.pth \
                             --test_image  ./sample_face.jpg \
                             --backend_dir ../../backend
"""

import os
import sys
import shutil
import json
import argparse
import logging
import numpy as np
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_checkpoint(checkpoint: str, test_image: str) -> bool:
    """Quick sanity-check: does the model produce a valid embedding?"""
    import torch
    sys.path.insert(0, str(Path(__file__).parent.parent / "training"))
    from train_arcface import FaceEmbeddingNet

    try:
        import cv2
        ckpt  = torch.load(checkpoint, map_location="cpu")
        cfg   = ckpt.get("config", {})
        emb_size = cfg.get("model", {}).get("embedding_size", 512)
        backbone = cfg.get("model", {}).get("backbone", "resnet50")

        model = FaceEmbeddingNet(backbone=backbone,
                                 embedding_size=emb_size,
                                 pretrained=False)
        model.load_state_dict(ckpt.get("model", ckpt))
        model.eval()

        img = cv2.imread(test_image)
        if img is None:
            logger.error(f"Cannot read test image: {test_image}")
            return False

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (112, 112))
        t   = torch.FloatTensor(img).permute(2,0,1).unsqueeze(0) / 127.5 - 1.0

        with torch.no_grad():
            emb = model(t)

        emb_np = emb.squeeze().numpy()
        logger.info(f"✅ Embedding shape  : {emb_np.shape}")
        logger.info(f"✅ Embedding norm   : {np.linalg.norm(emb_np):.4f} (should be ~1.0)")
        logger.info(f"✅ Min / Max        : {emb_np.min():.4f} / {emb_np.max():.4f}")
        logger.info(f"✅ Has NaN          : {np.isnan(emb_np).any()}")
        return not np.isnan(emb_np).any()

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False


def register(checkpoint: str, backend_dir: str, model_name: str = "arcface_custom"):
    """
    Copy checkpoint to backend and update face_model.py to load it.
    """
    backend    = Path(backend_dir)
    ckpt_dir   = backend / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    dest = ckpt_dir / f"{model_name}.pth"
    shutil.copy2(checkpoint, dest)
    logger.info(f"Checkpoint copied → {dest}")

    # Read config from checkpoint
    import torch
    ckpt = torch.load(checkpoint, map_location="cpu")
    cfg  = ckpt.get("config", {})
    meta = {
        "checkpoint_path": str(dest),
        "backbone":        cfg.get("model", {}).get("backbone", "resnet50"),
        "embedding_size":  cfg.get("model", {}).get("embedding_size", 512),
        "best_val_loss":   ckpt.get("best_loss"),
        "trained_epochs":  ckpt.get("epoch"),
        "num_identities":  len(ckpt.get("class_to_idx", {})),
    }

    meta_path = ckpt_dir / f"{model_name}_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info(f"Metadata saved → {meta_path}")

    # Print instructions for wiring it into face_model.py
    rel_ckpt = os.path.relpath(dest, backend)
    logger.info("")
    logger.info("=" * 60)
    logger.info("MODEL REGISTERED. To activate in the backend:")
    logger.info("")
    logger.info("Open backend/models/face_model.py → EmbeddingExtractor.load()")
    logger.info("Add this BEFORE the insightface block:")
    logger.info("")
    logger.info("    try:")
    logger.info("        import torch")
    logger.info("        import sys")
    logger.info("        sys.path.insert(0, 'ml/training')")
    logger.info("        from train_arcface import FaceEmbeddingNet")
    logger.info(f"        ckpt = torch.load('{rel_ckpt}', map_location='cpu')")
    logger.info(f"        self._model = FaceEmbeddingNet('{meta['backbone']}', {meta['embedding_size']}, pretrained=False)")
    logger.info("        self._model.load_state_dict(ckpt.get('model', ckpt))")
    logger.info("        self._model.eval()")
    logger.info("        self._type = 'custom'")
    logger.info("        self.EMBEDDING_SIZE = " + str(meta['embedding_size']))
    logger.info("        logger.info('Custom ArcFace model loaded')")
    logger.info("        return")
    logger.info("    except Exception as e:")
    logger.info("        logger.warning(f'Custom model load failed: {e}')")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint",  required=True)
    parser.add_argument("--test_image",  default=None)
    parser.add_argument("--backend_dir", default="../../backend")
    parser.add_argument("--model_name",  default="arcface_custom")
    args = parser.parse_args()

    if args.test_image:
        ok = test_checkpoint(args.checkpoint, args.test_image)
        if not ok:
            logger.error("Checkpoint test failed — not registering")
            sys.exit(1)

    register(args.checkpoint, args.backend_dir, args.model_name)
