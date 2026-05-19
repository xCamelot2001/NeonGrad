"""
Fine-tuned relevance scorer — Phase 2.
Loads the fine-tuned sentence-transformer from HuggingFace Hub.
Stub is here so the import chain doesn't break in Phase 1.
"""

class RelevanceScorer:
    """Placeholder until the model is trained and uploaded in Phase 2."""

    def score(self, cv_text: str, jd_text: str) -> float:
        raise NotImplementedError("Scorer is implemented in Phase 2.")
