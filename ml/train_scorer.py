"""
Phase 2 — Fine-tune sentence-transformers/all-MiniLM-L6-v2 as a relevance scorer.

Architecture:
  - Base: all-MiniLM-L6-v2 (384-dim sentence embeddings)
  - Head: Linear(384, 1) — regression, output clamped to [0, 1]
  - Loss: MSE
  - Metric: Pearson correlation (target > 0.85)

The trained model is saved locally at ml/checkpoints/ and then pushed to HuggingFace Hub.

Usage:
  cd NeonGrad/
  pip install -r ml/requirements.txt
  python ml/generate_dataset.py    # generate data first
  python ml/train_scorer.py
  python ml/train_scorer.py --push-to-hub YOUR_HF_USERNAME/neongrad-relevance-scorer

Args:
  --push-to-hub REPO_ID   Push final model to HuggingFace Hub after training
  --epochs N              Number of training epochs (default: 10)
  --batch-size N          Batch size (default: 32)
  --lr FLOAT              Learning rate (default: 2e-5)
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from scipy.stats import pearsonr
from sentence_transformers import SentenceTransformer
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

DATASET_DIR = Path(__file__).parent / "dataset"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)

BEST_MODEL_PATH = CHECKPOINT_DIR / "best_model"
FINAL_MODEL_PATH = CHECKPOINT_DIR / "final_model"


# ─── Dataset ─────────────────────────────────────────────────────────────────

class CVJDDataset(Dataset):
    """Dataset of (cv_summary, jd_summary, relevance_score) triplets."""

    def __init__(self, path: Path):
        self.samples: list[dict] = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    self.samples.append(json.loads(line))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict:
        s = self.samples[idx]
        return {
            "text": s["cv_summary"] + " [SEP] " + s["jd_summary"],
            "label": float(s["relevance_score"]),
        }


def collate_fn(batch: list[dict]) -> tuple[list[str], torch.Tensor]:
    texts = [item["text"] for item in batch]
    labels = torch.tensor([item["label"] for item in batch], dtype=torch.float32)
    return texts, labels


# ─── Model ───────────────────────────────────────────────────────────────────

class RelevanceScorerModel(nn.Module):
    """Sentence transformer + linear regression head."""

    def __init__(self, base_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        super().__init__()
        self.encoder = SentenceTransformer(base_model_name)
        embedding_dim = self.encoder.get_sentence_embedding_dimension()
        self.regression_head = nn.Sequential(
            nn.Linear(embedding_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(128, 1),
            nn.Sigmoid(),  # output in [0, 1]
        )

    def forward(self, texts: list[str]) -> torch.Tensor:
        # SentenceTransformer handles tokenisation and pooling
        embeddings = self.encoder.encode(
            texts,
            convert_to_tensor=True,
            show_progress_bar=False,
        )
        return self.regression_head(embeddings).squeeze(-1)

    def predict(self, cv_text: str, jd_text: str) -> float:
        """Convenience method for single inference."""
        self.eval()
        with torch.no_grad():
            text = cv_text + " [SEP] " + jd_text
            score = self.forward([text])
        return float(score.item())

    def batch_predict(self, cv_text: str, jd_texts: list[str]) -> list[float]:
        """Score one CV against multiple JDs."""
        self.eval()
        with torch.no_grad():
            texts = [cv_text + " [SEP] " + jd for jd in jd_texts]
            scores = self.forward(texts)
        return scores.tolist()


# ─── Training loop ───────────────────────────────────────────────────────────

def train(
    epochs: int = 10,
    batch_size: int = 32,
    lr: float = 2e-5,
    push_to_hub: str | None = None,
) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Data
    train_path = DATASET_DIR / "train.jsonl"
    val_path = DATASET_DIR / "val.jsonl"
    if not train_path.exists():
        raise FileNotFoundError(
            f"Training data not found at {train_path}.\n"
            "Run: python ml/generate_dataset.py first."
        )

    train_dataset = CVJDDataset(train_path)
    val_dataset = CVJDDataset(val_path)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)
    print(f"Train: {len(train_dataset)} samples | Val: {len(val_dataset)} samples")

    # Model
    model = RelevanceScorerModel()
    model.to(device)

    # Only train the regression head first (faster convergence), then unfreeze encoder
    for param in model.encoder.parameters():
        param.requires_grad = False

    optimizer = torch.optim.AdamW(model.regression_head.parameters(), lr=lr * 10)
    criterion = nn.MSELoss()

    best_pearson = -1.0
    history = {"train_loss": [], "val_loss": [], "val_pearson": []}

    print(f"\nPhase 1: Training regression head only (encoder frozen) — 3 epochs")
    for epoch in range(1, 4):
        model.train()
        train_loss = _run_epoch(model, train_loader, criterion, optimizer, device, train=True)
        val_loss, val_pearson = _run_eval(model, val_loader, criterion, device)
        _log_epoch(epoch, train_loss, val_loss, val_pearson, history)

        if val_pearson > best_pearson:
            best_pearson = val_pearson
            model.encoder.save(str(BEST_MODEL_PATH / "encoder"))
            torch.save(model.regression_head.state_dict(), BEST_MODEL_PATH / "regression_head.pt")

    print(f"\nPhase 2: Fine-tuning full model (encoder unfrozen) — {epochs} epochs")
    for param in model.encoder.parameters():
        param.requires_grad = True
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = _run_epoch(model, train_loader, criterion, optimizer, device, train=True)
        val_loss, val_pearson = _run_eval(model, val_loader, criterion, device)
        _log_epoch(epoch + 3, train_loss, val_loss, val_pearson, history)
        scheduler.step()

        if val_pearson > best_pearson:
            best_pearson = val_pearson
            BEST_MODEL_PATH.mkdir(parents=True, exist_ok=True)
            model.encoder.save(str(BEST_MODEL_PATH / "encoder"))
            torch.save(model.regression_head.state_dict(), BEST_MODEL_PATH / "regression_head.pt")
            print(f"  ✅ New best Pearson: {best_pearson:.4f} — checkpoint saved")

    # Save final model
    FINAL_MODEL_PATH.mkdir(parents=True, exist_ok=True)
    model.encoder.save(str(FINAL_MODEL_PATH / "encoder"))
    torch.save(model.regression_head.state_dict(), FINAL_MODEL_PATH / "regression_head.pt")

    # Save training history
    with open(CHECKPOINT_DIR / "history.json", "w") as f:
        json.dump(history, f, indent=2)

    print(f"\n{'='*50}")
    print(f"Training complete!")
    print(f"Best val Pearson: {best_pearson:.4f}  (target: > 0.85)")
    print(f"Best checkpoint:  {BEST_MODEL_PATH}")
    print(f"Final checkpoint: {FINAL_MODEL_PATH}")

    if push_to_hub:
        _push_to_hub(model, push_to_hub, best_pearson)


def _run_epoch(model, loader, criterion, optimizer, device, train: bool) -> float:
    total_loss = 0.0
    for texts, labels in tqdm(loader, leave=False):
        labels = labels.to(device)
        if train:
            optimizer.zero_grad()
        preds = model(texts)
        loss = criterion(preds, labels)
        if train:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        total_loss += loss.item()
    return total_loss / len(loader)


def _run_eval(model, loader, criterion, device) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    all_preds, all_labels = [], []
    with torch.no_grad():
        for texts, labels in loader:
            labels = labels.to(device)
            preds = model(texts)
            total_loss += criterion(preds, labels).item()
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())
    pearson, _ = pearsonr(all_preds, all_labels)
    return total_loss / len(loader), float(pearson)


def _log_epoch(epoch, train_loss, val_loss, val_pearson, history):
    history["train_loss"].append(train_loss)
    history["val_loss"].append(val_loss)
    history["val_pearson"].append(val_pearson)
    print(f"  Epoch {epoch:2d} | train_loss={train_loss:.4f} | val_loss={val_loss:.4f} | pearson={val_pearson:.4f}")


def _push_to_hub(model: RelevanceScorerModel, repo_id: str, best_pearson: float) -> None:
    """Push the best checkpoint encoder + head to HuggingFace Hub."""
    from huggingface_hub import HfApi, create_repo

    print(f"\nPushing to HuggingFace Hub: {repo_id}")
    create_repo(repo_id, exist_ok=True, private=False)

    # Push the sentence-transformer encoder
    best_encoder_path = str(BEST_MODEL_PATH / "encoder")
    from sentence_transformers import SentenceTransformer as ST
    encoder = ST(best_encoder_path)
    encoder.push_to_hub(repo_id)

    # Upload the regression head separately
    api = HfApi()
    api.upload_file(
        path_or_fileobj=str(BEST_MODEL_PATH / "regression_head.pt"),
        path_in_repo="regression_head.pt",
        repo_id=repo_id,
    )

    # Upload a model card
    model_card = f"""---
language: en
tags:
  - sentence-transformers
  - cv-matching
  - job-relevance
  - neongrad
pipeline_tag: sentence-similarity
---

# NeonGrad Relevance Scorer

Fine-tuned from `sentence-transformers/all-MiniLM-L6-v2` to predict CV–JD relevance.

## Usage

```python
from sentence_transformers import SentenceTransformer
import torch, torch.nn as nn
from huggingface_hub import hf_hub_download

encoder = SentenceTransformer("{repo_id}")
head_path = hf_hub_download(repo_id="{repo_id}", filename="regression_head.pt")
head = nn.Sequential(nn.Linear(384, 128), nn.ReLU(), nn.Dropout(0.1), nn.Linear(128, 1), nn.Sigmoid())
head.load_state_dict(torch.load(head_path, map_location="cpu"))

def score(cv_text: str, jd_text: str) -> float:
    text = cv_text + " [SEP] " + jd_text
    emb = encoder.encode([text], convert_to_tensor=True)
    return float(head(emb).squeeze().item())
```

## Performance

| Metric | Value |
|--------|-------|
| Val Pearson | {best_pearson:.4f} |
| Training data | 510 synthetic CV–JD pairs (Groq/Llama 3.1 8B) |
| Val data | 90 held-out pairs |

## Training

Fine-tuned on synthetic CV–JD pairs generated by Llama 3.1 8B via Groq API,
covering 15 job domains × 5 seniority levels across a balanced score distribution.
"""
    card_path = CHECKPOINT_DIR / "README.md"
    card_path.write_text(model_card)
    api.upload_file(
        path_or_fileobj=str(card_path),
        path_in_repo="README.md",
        repo_id=repo_id,
    )

    print(f"✅ Model pushed to https://huggingface.co/{repo_id}")
    print(f"   Update SCORER_MODEL_ID in backend/.env to: {repo_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train NeonGrad relevance scorer")
    parser.add_argument("--push-to-hub", type=str, default=None, metavar="REPO_ID",
                        help="HuggingFace repo ID to push model to, e.g. yourname/neongrad-relevance-scorer")
    parser.add_argument("--epochs", type=int, default=10, help="Fine-tuning epochs (default: 10)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate (default: 2e-5)")
    args = parser.parse_args()

    train(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        push_to_hub=args.push_to_hub,
    )
