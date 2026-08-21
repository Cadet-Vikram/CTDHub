"""
Model Evaluation Script
Evaluates face recognition model on verification pairs.

Metrics:
- Accuracy @ threshold
- FAR (False Accept Rate)
- FRR (False Reject Rate)
- ROC-AUC
- Best threshold finding
"""

import torch
import numpy as np
import json
import argparse
import logging
from pathlib import Path
from sklearn.metrics import roc_auc_score, roc_curve
import matplotlib.pyplot as plt
import cv2
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_model(checkpoint_path: str, embedding_size: int = 512):
    from train_arcface import FaceEmbeddingNet
    model = FaceEmbeddingNet(embedding_size)
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    if "model_state" in ckpt:
        model.load_state_dict(ckpt["model_state"])
    else:
        model.load_state_dict(ckpt)
    model.eval()
    return model


def extract_embedding(model, img_path: str, device) -> np.ndarray:
    img = cv2.imread(img_path)
    if img is None:
        return None
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (112, 112))
    tensor = torch.FloatTensor(img).permute(2, 0, 1).unsqueeze(0) / 127.5 - 1.0
    tensor = tensor.to(device)
    with torch.no_grad():
        emb = model(tensor)
    return emb.squeeze().cpu().numpy()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def evaluate(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(args.checkpoint, args.embedding_size).to(device)

    with open(args.pairs_file) as f:
        pairs = json.load(f)

    similarities, labels = [], []

    for pair in tqdm(pairs, desc="Evaluating"):
        emb1 = extract_embedding(model, pair["img1"], device)
        emb2 = extract_embedding(model, pair["img2"], device)

        if emb1 is None or emb2 is None:
            continue

        sim = cosine_similarity(emb1, emb2)
        similarities.append(sim)
        labels.append(1 if pair["same_person"] else 0)

    similarities = np.array(similarities)
    labels = np.array(labels)

    # ROC Analysis
    auc = roc_auc_score(labels, similarities)
    fpr, tpr, thresholds = roc_curve(labels, similarities)

    # Best threshold (EER point)
    fnr = 1 - tpr
    eer_idx = np.nanargmin(np.abs(fnr - fpr))
    best_threshold = thresholds[eer_idx]
    eer = (fpr[eer_idx] + fnr[eer_idx]) / 2

    # Accuracy at best threshold
    preds = (similarities >= best_threshold).astype(int)
    accuracy = (preds == labels).mean()

    # At common thresholds
    results = {}
    for thresh in [0.5, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        preds_t = (similarities >= thresh).astype(int)
        acc = (preds_t == labels).mean()
        tp = ((preds_t == 1) & (labels == 1)).sum()
        fp = ((preds_t == 1) & (labels == 0)).sum()
        fn = ((preds_t == 0) & (labels == 1)).sum()
        tn = ((preds_t == 0) & (labels == 0)).sum()
        far = fp / (fp + tn + 1e-10)
        frr = fn / (fn + tp + 1e-10)
        results[thresh] = {"accuracy": acc, "FAR": far, "FRR": frr}

    logger.info(f"\n{'='*50}")
    logger.info(f"EVALUATION RESULTS")
    logger.info(f"{'='*50}")
    logger.info(f"Total pairs evaluated: {len(labels)}")
    logger.info(f"Positive pairs: {labels.sum()}, Negative pairs: {(1-labels).sum()}")
    logger.info(f"\nROC-AUC: {auc:.4f}")
    logger.info(f"EER: {eer:.4f} at threshold {best_threshold:.4f}")
    logger.info(f"Accuracy @ EER threshold: {accuracy:.4f}")
    logger.info(f"\nThreshold Analysis:")
    logger.info(f"{'Thresh':>8} {'Accuracy':>10} {'FAR':>10} {'FRR':>10}")
    for t, r in results.items():
        logger.info(f"{t:>8.2f} {r['accuracy']:>10.4f} {r['FAR']:>10.4f} {r['FRR']:>10.4f}")

    # Save plot
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, 'b-', label=f'ROC (AUC={auc:.3f})')
    plt.plot([0, 1], [0, 1], 'r--')
    plt.scatter([fpr[eer_idx]], [tpr[eer_idx]], s=100, c='red', label=f'EER={eer:.3f}')
    plt.xlabel("False Accept Rate")
    plt.ylabel("True Accept Rate")
    plt.title("Face Verification ROC Curve")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(f"{args.output_dir}/roc_curve.png", dpi=150, bbox_inches='tight')
    logger.info(f"\nROC curve saved to {args.output_dir}/roc_curve.png")

    report = {"auc": float(auc), "eer": float(eer), "best_threshold": float(best_threshold), "accuracy_at_eer": float(accuracy), "threshold_analysis": {str(k): {kk: float(vv) for kk, vv in v.items()} for k, v in results.items()}}
    with open(f"{args.output_dir}/eval_report.json", "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--pairs_file", required=True)
    parser.add_argument("--output_dir", default="./eval_results")
    parser.add_argument("--embedding_size", type=int, default=512)
    args = parser.parse_args()

    import os
    os.makedirs(args.output_dir, exist_ok=True)
    evaluate(args)
