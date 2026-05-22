"""
Phase 2 — Evaluate the fine-tuned NeonGrad relevance scorer.

Prints a benchmark table and generates a training curve plot.

Usage:
  cd NeonGrad/
  python ml/evaluate_scorer.py
  python ml/evaluate_scorer.py --checkpoint ml/checkpoints/best_model
"""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from scipy.stats import pearsonr, spearmanr
from sentence_transformers import SentenceTransformer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from torch.utils.data import DataLoader

from train_scorer import CVJDDataset, collate_fn

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"
DATASET_DIR = Path(__file__).parent / "dataset"


def load_model(checkpoint_dir: Path) -> tuple[SentenceTransformer, nn.Sequential]:
    encoder = SentenceTransformer(str(checkpoint_dir / "encoder"))
    head = nn.Sequential(
        nn.Linear(384, 128),
        nn.ReLU(),
        nn.Dropout(0.1),
        nn.Linear(128, 1),
        nn.Sigmoid(),
    )
    head.load_state_dict(torch.load(checkpoint_dir / "regression_head.pt", map_location="cpu"))
    head.eval()
    return encoder, head


def predict_all(encoder, head, loader) -> tuple[list[float], list[float]]:
    all_preds, all_labels = [], []
    with torch.no_grad():
        for texts, labels in loader:
            embeddings = encoder.encode(texts, convert_to_tensor=True, show_progress_bar=False)
            preds = head(embeddings).squeeze(-1)
            all_preds.extend(preds.tolist())
            all_labels.extend(labels.tolist())
    return all_preds, all_labels


def print_benchmark(preds: list[float], labels: list[float], split: str) -> None:
    preds_arr = np.array(preds)
    labels_arr = np.array(labels)

    pearson, p_val = pearsonr(preds_arr, labels_arr)
    spearman, s_val = spearmanr(preds_arr, labels_arr)
    mse = mean_squared_error(labels_arr, preds_arr)
    mae = mean_absolute_error(labels_arr, preds_arr)
    rmse = np.sqrt(mse)

    print(f"\n{'─'*50}")
    print(f"  {split} Set Evaluation ({len(preds)} samples)")
    print(f"{'─'*50}")
    print(f"  Pearson r        : {pearson:.4f}  (target > 0.85)")
    print(f"  Spearman ρ       : {spearman:.4f}")
    print(f"  MSE              : {mse:.4f}")
    print(f"  RMSE             : {rmse:.4f}")
    print(f"  MAE              : {mae:.4f}")
    print(f"{'─'*50}")

    if pearson > 0.85:
        print(f"  ✅ Target met! Pearson {pearson:.4f} > 0.85")
    else:
        print(f"  ⚠️  Pearson {pearson:.4f} below target (0.85). Consider more training data or epochs.")

    # Per-bucket accuracy
    buckets = [
        ("poor   (0.0–0.2)", 0.0, 0.25),
        ("stretch(0.25–0.55)", 0.25, 0.55),
        ("decent (0.55–0.8)", 0.55, 0.80),
        ("strong (0.8–1.0)", 0.80, 1.01),
    ]
    print(f"\n  Bucket-level MAE:")
    for name, lo, hi in buckets:
        mask = (labels_arr >= lo) & (labels_arr < hi)
        if mask.sum() == 0:
            continue
        bucket_mae = mean_absolute_error(labels_arr[mask], preds_arr[mask])
        print(f"    {name}: {bucket_mae:.4f}  (n={mask.sum()})")


def plot_results(preds: list[float], labels: list[float], history_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("NeonGrad Relevance Scorer — Evaluation", fontsize=14)

    # Scatter plot: predicted vs actual
    ax = axes[0]
    ax.scatter(labels, preds, alpha=0.4, s=15, c="#6366f1")
    ax.plot([0, 1], [0, 1], "r--", linewidth=1.5, label="Perfect prediction")
    ax.set_xlabel("Actual Score")
    ax.set_ylabel("Predicted Score")
    ax.set_title("Predicted vs Actual")
    ax.legend()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # Residuals
    ax = axes[1]
    residuals = np.array(preds) - np.array(labels)
    ax.scatter(labels, residuals, alpha=0.4, s=15, c="#f59e0b")
    ax.axhline(0, color="r", linestyle="--", linewidth=1.5)
    ax.set_xlabel("Actual Score")
    ax.set_ylabel("Residual (pred − actual)")
    ax.set_title("Residuals")
    ax.set_xlim(0, 1)

    # Training curves (if history exists)
    ax = axes[2]
    if history_path.exists():
        with open(history_path) as f:
            history = json.load(f)
        epochs = range(1, len(history["train_loss"]) + 1)
        ax2 = ax.twinx()
        ax.plot(epochs, history["train_loss"], label="Train Loss", color="#6366f1")
        ax.plot(epochs, history["val_loss"], label="Val Loss", color="#a78bfa")
        ax2.plot(epochs, history["val_pearson"], label="Val Pearson", color="#10b981", linestyle="--")
        ax.axhline(0, color="gray", linewidth=0.5)
        ax2.axhline(0.85, color="#10b981", linewidth=0.8, linestyle=":", label="Target (0.85)")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss (MSE)")
        ax2.set_ylabel("Pearson r")
        ax.set_title("Training Curves")
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=8)
    else:
        ax.text(0.5, 0.5, "No training history found", ha="center", va="center", transform=ax.transAxes)
        ax.set_title("Training Curves")

    plt.tight_layout()
    out_path = CHECKPOINT_DIR / "evaluation_plots.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  📊 Plots saved to {out_path}")
    plt.show()


def evaluate(checkpoint_dir: Path) -> None:
    print(f"Loading model from {checkpoint_dir}...")
    encoder, head = load_model(checkpoint_dir)

    val_path = DATASET_DIR / "val.jsonl"
    train_path = DATASET_DIR / "train.jsonl"

    if not val_path.exists():
        raise FileNotFoundError(f"Val set not found at {val_path}. Run generate_dataset.py first.")

    val_ds = CVJDDataset(val_path)
    val_loader = DataLoader(val_ds, batch_size=64, shuffle=False, collate_fn=collate_fn)
    val_preds, val_labels = predict_all(encoder, head, val_loader)
    print_benchmark(val_preds, val_labels, "Validation")

    if train_path.exists():
        train_ds = CVJDDataset(train_path)
        train_loader = DataLoader(train_ds, batch_size=64, shuffle=False, collate_fn=collate_fn)
        train_preds, train_labels = predict_all(encoder, head, train_loader)
        print_benchmark(train_preds, train_labels, "Train (sanity check)")

    plot_results(val_preds, val_labels, CHECKPOINT_DIR / "history.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate NeonGrad relevance scorer")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=CHECKPOINT_DIR / "best_model",
        help="Path to checkpoint directory (default: ml/checkpoints/best_model)",
    )
    args = parser.parse_args()
    evaluate(args.checkpoint)
