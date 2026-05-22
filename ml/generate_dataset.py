"""
Phase 2 — Synthetic training data generation for the NeonGrad relevance scorer.

Generates (cv_summary, jd_summary, relevance_score) triplets using Groq (Llama 3.1 8B).
Scores are floats in [0.0, 1.0]:
  0.9–1.0  strong match  — skills, seniority, and domain all align
  0.6–0.8  decent match  — most requirements met, small gaps
  0.3–0.5  stretch       — relevant domain but notable gaps
  0.0–0.2  poor match    — wrong domain, seniority, or stack

Usage:
  cd NeonGrad/
  pip install -r ml/requirements.txt
  python ml/generate_dataset.py
"""

import json
import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from tqdm import tqdm

# Load env from backend/.env (where GROQ_API_KEY lives)
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
client = Groq(api_key=GROQ_API_KEY)

DATASET_DIR = Path(__file__).parent / "dataset"
DATASET_DIR.mkdir(exist_ok=True)

TRAIN_PATH = DATASET_DIR / "train.jsonl"
VAL_PATH = DATASET_DIR / "val.jsonl"

# ─── Prompt templates ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a recruitment expert generating training data for an AI job-matching model.
Generate realistic CV summaries and job description summaries, then score how well they match.
Always respond with valid JSON only — no markdown, no explanation."""

PAIR_PROMPT = """Generate a CV–JD pair with a relevance score of approximately {target_score:.1f} (range 0.0–1.0).

The pair should be for a {seniority} {domain} role.
Score guidance:
  0.9–1.0 → near-perfect match: same stack, same seniority, same domain, 90%+ skill overlap
  0.6–0.8 → good match: correct domain/seniority, 1–2 gaps (nice-to-haves, not must-haves)
  0.3–0.5 → stretch: related domain, wrong seniority OR 3–4 missing key skills
  0.0–0.2 → poor match: wrong domain, completely different stack, or overqualified/underqualified

Respond ONLY with this JSON (no markdown):
{{
  "cv_summary": "3-5 sentence summary of candidate skills, experience, and background",
  "jd_summary": "3-5 sentence summary of the job requirements, responsibilities, and ideal candidate",
  "relevance_score": {target_score:.1f},
  "reasoning": "One sentence explaining why this score was assigned"
}}"""

# ─── Domain and seniority config ─────────────────────────────────────────────

DOMAINS = [
    "Machine Learning Engineer",
    "Data Scientist",
    "Backend Software Engineer",
    "Full Stack Engineer",
    "MLOps Engineer",
    "AI Research Engineer",
    "Data Engineer",
    "NLP Engineer",
    "Computer Vision Engineer",
    "Cloud Infrastructure Engineer",
    "Frontend Engineer",
    "DevOps Engineer",
    "Product Manager",
    "UX Designer",
    "Quantitative Analyst",
]

SENIORITY_LEVELS = ["junior", "mid-level", "senior", "staff", "principal"]

# Score buckets to ensure balanced distribution
SCORE_BUCKETS = [
    (0.05, 40),   # poor match
    (0.15, 30),   # poor match
    (0.35, 40),   # stretch
    (0.50, 40),   # stretch
    (0.65, 80),   # decent
    (0.75, 80),   # decent
    (0.85, 120),  # strong
    (0.92, 100),  # strong
    (0.97, 70),   # near-perfect
]
# Total: 600 samples


def generate_pair(target_score: float, seniority: str, domain: str) -> dict | None:
    """Call Groq to generate a single CV–JD pair."""
    prompt = PAIR_PROMPT.replace("{target_score:.1f}", f"{target_score:.1f}").replace(
        "{seniority}", seniority
    ).replace("{domain}", domain)

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.85,
            max_tokens=600,
        )
        text = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)
        # Validate required keys
        for key in ("cv_summary", "jd_summary", "relevance_score"):
            if key not in data:
                return None
        # Clamp score to [0, 1]
        data["relevance_score"] = max(0.0, min(1.0, float(data["relevance_score"])))
        return data
    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"  [warn] Parse error: {e}")
        return None


def generate_all(total_target: int = 600, val_fraction: float = 0.15) -> None:
    """Generate the full dataset and write train/val splits."""
    all_samples: list[dict] = []

    print(f"Generating {total_target} CV–JD pairs using Groq (Llama 3.1 8B)...")

    for target_score, count in SCORE_BUCKETS:
        print(f"\n  Score bucket ~{target_score:.2f} — generating {count} samples")
        generated = 0
        attempts = 0
        pbar = tqdm(total=count, desc=f"  score={target_score:.2f}")

        while generated < count and attempts < count * 3:
            seniority = random.choice(SENIORITY_LEVELS)
            domain = random.choice(DOMAINS)
            pair = generate_pair(target_score, seniority, domain)
            attempts += 1

            if pair:
                pair["bucket_target"] = target_score
                all_samples.append(pair)
                generated += 1
                pbar.update(1)

            # Gentle rate limiting — Groq free tier: ~30 req/min
            time.sleep(0.1)

        pbar.close()
        print(f"  Done: {generated}/{count} generated ({attempts} attempts)")

    # Shuffle before splitting
    random.shuffle(all_samples)
    split_idx = int(len(all_samples) * (1 - val_fraction))
    train_samples = all_samples[:split_idx]
    val_samples = all_samples[split_idx:]

    # Write JSONL files
    with open(TRAIN_PATH, "w") as f:
        for sample in train_samples:
            f.write(json.dumps(sample) + "\n")

    with open(VAL_PATH, "w") as f:
        for sample in val_samples:
            f.write(json.dumps(sample) + "\n")

    print(f"\n✅ Dataset saved:")
    print(f"   Train: {len(train_samples)} samples → {TRAIN_PATH}")
    print(f"   Val:   {len(val_samples)} samples  → {VAL_PATH}")
    print(f"\nScore distribution:")
    scores = [s["relevance_score"] for s in all_samples]
    print(f"   Mean:  {sum(scores)/len(scores):.3f}")
    print(f"   Min:   {min(scores):.3f}")
    print(f"   Max:   {max(scores):.3f}")


if __name__ == "__main__":
    generate_all()
