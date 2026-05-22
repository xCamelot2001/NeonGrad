"""
NeonGrad Relevance Scorer — production inference wrapper.

Loads the fine-tuned model from HuggingFace Hub (SCORER_MODEL_ID in backend/.env).
Falls back gracefully to the base all-MiniLM-L6-v2 if the fine-tuned model isn't
available yet (useful during early Phase 2 before training is complete).

Usage:
    from models.scorer import get_scorer
    scorer = get_scorer()
    score = scorer.score(cv_text, jd_text)          # 0.0–1.0
    scores = scorer.batch_score(cv_text, jd_texts)  # list[float]
"""

import os
import threading
from pathlib import Path
from functools import lru_cache

import torch
import torch.nn as nn

# Lazy import — sentence-transformers is ~200MB, only load when first used
_sentence_transformers = None

def _get_st():
    global _sentence_transformers
    if _sentence_transformers is None:
        from sentence_transformers import SentenceTransformer as ST
        _sentence_transformers = ST
    return _sentence_transformers


BASE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Head architecture must match ml/train_scorer.py exactly
def _build_head() -> nn.Sequential:
    return nn.Sequential(
        nn.Linear(EMBEDDING_DIM, 128),
        nn.ReLU(),
        nn.Dropout(0.1),
        nn.Linear(128, 1),
        nn.Sigmoid(),
    )


class RelevanceScorer:
    """
    Sentence-transformer + linear regression head for CV–JD relevance scoring.

    Score semantics:
        0.75–1.0  strong_match  — near-perfect fit
        0.50–0.74 decent        — good fit, minor gaps
        0.30–0.49 stretch       — relevant but notable gaps
        0.00–0.29 skip          — poor fit
    """

    def __init__(self, model_id: str | None = None):
        self._device = torch.device("cpu")  # CPU inference is fine for batch of ~200 jobs
        self._encoder = None
        self._head = None
        self._model_id = model_id or os.getenv("SCORER_MODEL_ID") or BASE_MODEL
        self._load_lock = threading.Lock()
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:
                return
            ST = _get_st()
            print(f"[scorer] Loading encoder from '{self._model_id}'...")
            self._encoder = ST(self._model_id)

            # Try to load the fine-tuned regression head from HuggingFace
            self._head = _build_head()
            head_loaded = False
            if self._model_id != BASE_MODEL:
                try:
                    from huggingface_hub import hf_hub_download
                    head_path = hf_hub_download(
                        repo_id=self._model_id,
                        filename="regression_head.pt",
                    )
                    self._head.load_state_dict(
                        torch.load(head_path, map_location=self._device)
                    )
                    head_loaded = True
                    print(f"[scorer] ✅ Fine-tuned head loaded from '{self._model_id}'")
                except Exception as e:
                    print(f"[scorer] ⚠️  Could not load regression head: {e}")
                    print(f"[scorer]    Falling back to untrained head (cosine sim only)")

            if not head_loaded:
                print(f"[scorer] Using base encoder '{self._model_id}' with cosine similarity fallback.")
                # When head is untrained, score via cosine similarity instead
                self._use_cosine_fallback = True
            else:
                self._use_cosine_fallback = False

            self._head.to(self._device)
            self._head.eval()
            self._loaded = True

    def score(self, cv_text: str, jd_text: str) -> float:
        """Score a single CV–JD pair. Returns float in [0, 1]."""
        return self.batch_score(cv_text, [jd_text])[0]

    def batch_score(self, cv_text: str, jd_texts: list[str]) -> list[float]:
        """
        Score one CV against a list of JDs.
        More efficient than calling score() in a loop.
        """
        self._ensure_loaded()

        if self._use_cosine_fallback:
            return self._cosine_batch(cv_text, jd_texts)

        # Concatenate CV + JD with separator (matches training format)
        texts = [cv_text + " [SEP] " + jd for jd in jd_texts]
        with torch.no_grad():
            embeddings = self._encoder.encode(
                texts,
                convert_to_tensor=True,
                show_progress_bar=False,
                device=str(self._device),
            )
            preds = self._head(embeddings).squeeze(-1)

        scores = preds.cpu().tolist()
        # Handle single-item tensor (squeeze may have made it a scalar)
        if isinstance(scores, float):
            scores = [scores]
        return scores

    def _cosine_batch(self, cv_text: str, jd_texts: list[str]) -> list[float]:
        """Cosine similarity fallback when regression head is unavailable."""
        all_texts = [cv_text] + jd_texts
        with torch.no_grad():
            embeddings = self._encoder.encode(
                all_texts,
                convert_to_tensor=True,
                show_progress_bar=False,
            )
        cv_emb = embeddings[0]
        jd_embs = embeddings[1:]
        cosine_sim = torch.nn.functional.cosine_similarity(
            cv_emb.unsqueeze(0), jd_embs
        )
        # Cosine similarity is in [-1, 1]; map to [0, 1]
        scores = ((cosine_sim + 1) / 2).tolist()
        if isinstance(scores, float):
            scores = [scores]
        return scores

    @staticmethod
    def score_to_strategy(score: float) -> str:
        if score >= 0.75:
            return "strong_match"
        elif score >= 0.50:
            return "decent"
        elif score >= 0.30:
            return "stretch"
        else:
            return "skip"


# Module-level singleton — instantiated once, reused across requests
_scorer_instance: RelevanceScorer | None = None
_scorer_lock = threading.Lock()


def get_scorer() -> RelevanceScorer:
    """Return the module-level scorer singleton (lazy-loaded)."""
    global _scorer_instance
    if _scorer_instance is None:
        with _scorer_lock:
            if _scorer_instance is None:
                model_id = os.getenv("SCORER_MODEL_ID") or BASE_MODEL
                _scorer_instance = RelevanceScorer(model_id=model_id)
    return _scorer_instance
