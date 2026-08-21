"""
Model Evaluation Script
========================
Computes: Accuracy, FAR, FRR, EER, ROC-AUC at multiple thresholds.
Also: finds best operating threshold + plots ROC curve.

Usage:
    python evaluate_model.py \
        --checkpoint ./checkpoints/arcface/best.pth \
        --pairs      ./data/pairs.json \
        --output_dir ./eval_results
"""

import json
import logging
import argparse
from pathlib import Path

import numpy as np
import cv2
import torch
from tqdm import tqdm
from sklearn.metrics import roc_auc_score, roc_curve

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_model(checkpoint_path: str, device):
    from train_arcface import FaceEmbeddingNet
    ckpt = torch.load(checkpoint_path, map_location=device)

    cfg = ckpt.get("config", {})
    backbone       = cfg.get("model", {}).get("backbone", "resnet50")
    embedding_size = cfg.get("model", {}).get("embedding_size", 512)

    model = FaceEmbeddingNet(backbone=backbone, embedding_size=embedding_size,
                             pretrained=False)
    state = ckpt.get("model", ckpt)  # handles both full ckpt and weights-only
    model.load_state_dict(state)
    model.eval()
    return model.to(device), embedding_size


def extract_embedding(model, img_path: str, device,
                      img_size: int = 112) -> np.ndarray:
    img = cv2.imread(img_path)
    if img is None:
        return None
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (img_size, img_size))
    t   = torch.FloatTensor(img).permute(2, 0, 1).unsqueeze(0) / 127.5 - 1.0
    with torch.no_grad():
        emb = model(t.to(device))
    return emb.squeeze().cpu().numpy()


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 1e-10 else 0.0


def evaluate(checkpoint: str, pairs_file: str, output_dir: str,
             img_size: int = 112):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Loading model from {checkpoint}")
    model, _ = load_model(checkpoint, device)

    with open(pairs_file) as f:
        pairs = json.load(f)
    logger.info(f"Evaluating {len(pairs)} pairs")

    sims, labels = [], []
    cache = {}   # path → embedding (avoid recomputing)

    for pair in tqdm(pairs, desc="Computing similarities"):
        p1, p2 = pair["img1"], pair["img2"]

        if p1 not in cache:
            cache[p1] = extract_embedding(model, p1, device, img_size)
        if p2 not in cache:
            cache[p2] = extract_embedding(model, p2, device, img_size)

        e1, e2 = cache[p1], cache[p2]
        if e1 is None or e2 is None:
            continue

        sims.append(cosine_sim(e1, e2))
        labels.append(1 if pair["same_person"] else 0)

    sims   = np.array(sims)
    labels = np.array(labels)

    # ── ROC ─────────────────────────────────────────────────────────────────
    auc             = roc_auc_score(labels, sims)
    fpr, tpr, thrs  = roc_curve(labels, sims)
    fnr             = 1 - tpr
    eer_idx         = np.nanargmin(np.abs(fnr - fpr))
    eer             = (fpr[eer_idx] + fnr[eer_idx]) / 2
    best_thresh     = float(thrs[eer_idx])

    # ── Per-threshold metrics ────────────────────────────────────────────────
    rows = []
    for t in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        preds  = (sims >= t).astype(int)
        acc    = float((preds == labels).mean())
        tp     = int(((preds == 1) & (labels == 1)).sum())
        fp     = int(((preds == 1) & (labels == 0)).sum())
        fn     = int(((preds == 0) & (labels == 1)).sum())
        tn     = int(((preds == 0) & (labels == 0)).sum())
        far    = fp / (fp + tn + 1e-10)
        frr    = fn / (fn + tp + 1e-10)
        rows.append({"threshold": t, "accuracy": round(acc, 4),
                     "FAR": round(far, 4), "FRR": round(frr, 4),
                     "TP": tp, "FP": fp, "FN": fn, "TN": tn})

    # ── Console output ───────────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 55)
    logger.info("  FACE VERIFICATION EVALUATION RESULTS")
    logger.info("=" * 55)
    logger.info(f"  Pairs evaluated : {len(labels)}")
    logger.info(f"  Positive pairs  : {labels.sum()}")
    logger.info(f"  Negative pairs  : {(1-labels).sum()}")
    logger.info(f"  ROC-AUC         : {auc:.4f}  {'✅ Excellent' if auc>0.97 else '⚠️ Keep training' if auc>0.93 else '❌ Needs more data/epochs'}")
    logger.info(f"  EER             : {eer:.4f}  (lower is better)")
    logger.info(f"  Best threshold  : {best_thresh:.4f}")
    logger.info("")
    logger.info(f"  {'Thresh':>8}  {'Accuracy':>10}  {'FAR':>8}  {'FRR':>8}")
    logger.info(f"  {'-'*46}")
    for r in rows:
        marker = " ← recommended" if abs(r["threshold"] - 0.65) < 0.01 else ""
        logger.info(f"  {r['threshold']:>8.2f}  {r['accuracy']:>10.4f}  "
                    f"{r['FAR']:>8.4f}  {r['FRR']:>8.4f}{marker}")
    logger.info("=" * 55)

    # ── Save results ─────────────────────────────────────────────────────────
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    report = {
        "roc_auc":       round(float(auc), 4),
        "eer":           round(float(eer), 4),
        "best_threshold":round(best_thresh, 4),
        "n_pairs":       len(labels),
        "threshold_analysis": rows,
    }
    with open(out / "eval_report.json", "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Report saved → {out}/eval_report.json")

    # ── ROC plot ─────────────────────────────────────────────────────────────
    try:
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        axes[0].plot(fpr, tpr, "b-", lw=2, label=f"ROC (AUC={auc:.3f})")
        axes[0].scatter([fpr[eer_idx]], [tpr[eer_idx]], s=120, c="red",
                         zorder=5, label=f"EER={eer:.3f}")
        axes[0].plot([0, 1], [0, 1], "r--", alpha=0.5)
        axes[0].set_xlabel("False Accept Rate (FAR)")
        axes[0].set_ylabel("True Accept Rate (TAR)")
        axes[0].set_title("ROC Curve")
        axes[0].legend()
        axes[0].grid(alpha=0.3)

        thresholds_plot = [r["threshold"] for r in rows]
        far_plot        = [r["FAR"]       for r in rows]
        frr_plot        = [r["FRR"]       for r in rows]
        axes[1].plot(thresholds_plot, far_plot, "r-o", label="FAR")
        axes[1].plot(thresholds_plot, frr_plot, "b-o", label="FRR")
        axes[1].axvline(x=0.65, color="green", linestyle="--", alpha=0.7,
                        label="Recommended threshold (0.65)")
        axes[1].set_xlabel("Threshold")
        axes[1].set_ylabel("Error Rate")
        axes[1].set_title("FAR vs FRR")
        axes[1].legend()
        axes[1].grid(alpha=0.3)

        plt.suptitle("Face Verification — Connecting the Dots", fontweight="bold")
        plt.tight_layout()
        plt.savefig(str(out / "roc_curve.png"), dpi=150, bbox_inches="tight")
        logger.info(f"ROC plot saved → {out}/roc_curve.png")
        plt.close()
    except ImportError:
        logger.warning("matplotlib not installed — skipping plot")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint",  required=True)
    parser.add_argument("--pairs",       required=True)
    parser.add_argument("--output_dir",  default="./eval_results")
    parser.add_argument("--img_size",    type=int, default=112)
    args = parser.parse_args()
    evaluate(args.checkpoint, args.pairs, args.output_dir, args.img_size)
