"""
NeonGrad Job Ranking Agent — Phase 2.

LangGraph pipeline (order matters — score FIRST, then call Groq only for top jobs):
  load_profile
    → fetch_unranked_jobs
      → score_jobs_raw        (sentence-transformer on raw JD text — zero API calls)
        → extract_top_jds     (Groq JD extraction for top 50 only, with retry backoff)
          → analyze_gaps      (Groq gap analysis for top 50, with retry backoff)
            → assign_strategies
              → store_rankings

Why this order?
  Scoring 500 jobs with a local model takes ~5s.
  Groq free tier is 6000 TPM / 30 RPM.
  Extracting JDs for all 500 jobs would need ~480 Groq calls and hit the limit every time.
  By scoring first we cut Groq calls to ≤50 — well within free tier.

Triggered by:
  POST /api/jobs/rank  → run_ranking(user_id)
  Daily APScheduler    → run_ranking_all_users()
"""

import json
import os
import time
from typing import TypedDict

from groq import Groq
from langgraph.graph import END, StateGraph

from models.scorer import get_scorer
from tools.supabase_client import get_supabase

# ─── State ───────────────────────────────────────────────────────────────────

class RankingState(TypedDict):
    user_id: str
    profile: dict
    cv_text: str
    unranked_jobs: list[dict]
    scored_jobs: list[dict]   # all jobs with relevance_score, sorted desc
    rankings: list[dict]      # final DB rows
    error: str | None


# ─── Constants ───────────────────────────────────────────────────────────────

TOP_N_FOR_GROQ = 50       # only call Groq for these jobs
GROQ_RETRY_ATTEMPTS = 4   # number of retries on 429
GROQ_RETRY_BASE_SLEEP = 4 # seconds — doubles each retry


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_groq() -> Groq:
    return Groq(api_key=os.environ["GROQ_API_KEY"])


def _cv_to_text(profile: dict) -> str:
    """Flatten structured CV into a plain-text summary for the scorer."""
    cv = profile.get("cv_structured") or {}
    parts = []
    if summary := cv.get("summary"):
        parts.append(summary)
    if skills := cv.get("skills"):
        parts.append("Skills: " + ", ".join(skills[:30]))
    if experience := cv.get("experience"):
        for exp in experience[:4]:
            role = exp.get("title", "")
            company = exp.get("company", "")
            desc = exp.get("description", "")
            parts.append(f"{role} at {company}. {desc}"[:200])
    if education := cv.get("education"):
        for edu in education[:2]:
            parts.append(f"{edu.get('degree', '')} at {edu.get('institution', '')}")
    return " | ".join(parts) or (profile.get("cv_raw_text") or "")[:1500]


def _groq_call_with_retry(groq: Groq, prompt: str, max_tokens: int = 350) -> str | None:
    """
    Call Groq with exponential backoff on 429 rate limit errors.
    Returns the response text or None if all retries fail.
    """
    sleep = GROQ_RETRY_BASE_SLEEP
    for attempt in range(GROQ_RETRY_ATTEMPTS):
        try:
            resp = groq.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit_exceeded" in err:
                if attempt < GROQ_RETRY_ATTEMPTS - 1:
                    print(f"  [groq] Rate limited — sleeping {sleep}s (attempt {attempt + 1}/{GROQ_RETRY_ATTEMPTS})")
                    time.sleep(sleep)
                    sleep *= 2
                else:
                    print(f"  [groq] Rate limit, all retries exhausted.")
            else:
                print(f"  [groq] Error: {e}")
                break
    return None


def _parse_json_response(text: str | None) -> dict | None:
    """Strip markdown fences and parse JSON, return None on failure."""
    if not text:
        return None
    try:
        t = text.strip()
        if t.startswith("```"):
            t = t.split("```")[1]
            if t.startswith("json"):
                t = t[4:]
        return json.loads(t.strip())
    except json.JSONDecodeError:
        return None


# ─── LangGraph nodes ─────────────────────────────────────────────────────────

def load_profile(state: RankingState) -> RankingState:
    """Node 1: Load user profile from Supabase."""
    supabase = get_supabase()
    result = (
        supabase.table("profiles")
        .select("*")
        .eq("id", state["user_id"])
        .single()
        .execute()
    )
    if not result.data:
        return {**state, "error": f"No profile for user {state['user_id']}"}
    profile = result.data
    print(f"[ranking] Profile loaded for user {state['user_id'][:8]}...")
    return {**state, "profile": profile, "cv_text": _cv_to_text(profile)}


def fetch_unranked_jobs(state: RankingState) -> RankingState:
    """Node 2: Fetch jobs not yet ranked for this user."""
    if state.get("error"):
        return state
    supabase = get_supabase()
    user_id = state["user_id"]

    ranked_result = (
        supabase.table("job_rankings")
        .select("job_id")
        .eq("user_id", user_id)
        .execute()
    )
    already_ranked = {r["job_id"] for r in (ranked_result.data or [])}

    jobs_result = (
        supabase.table("jobs")
        .select("*")
        .order("fetched_at", desc=True)
        .limit(500)
        .execute()
    )
    all_jobs = jobs_result.data or []
    unranked = [j for j in all_jobs if j["id"] not in already_ranked]

    print(f"[ranking] {len(unranked)} unranked jobs (of {len(all_jobs)} total)")
    return {**state, "unranked_jobs": unranked}


def score_jobs_raw(state: RankingState) -> RankingState:
    """
    Node 3: Score all unranked jobs using the sentence-transformer.
    Uses raw JD text — no Groq calls. Fast (≈5s for 500 jobs on CPU).
    Returns jobs sorted by relevance_score descending.
    """
    if state.get("error") or not state.get("unranked_jobs"):
        return state

    scorer = get_scorer()
    cv_text = state["cv_text"]
    jobs = state["unranked_jobs"]

    # Build a representative text for each job from what we already have
    jd_texts = []
    for job in jobs:
        raw = (job.get("jd_raw") or "")[:600]
        title = job.get("title", "")
        company = job.get("company", "")
        jd_texts.append(f"{title} at {company}. {raw}")

    print(f"[ranking] Scoring {len(jobs)} jobs with sentence-transformer...")
    BATCH = 64
    all_scores: list[float] = []
    for i in range(0, len(jd_texts), BATCH):
        batch_scores = scorer.batch_score(cv_text, jd_texts[i: i + BATCH])
        all_scores.extend(batch_scores)

    scored = [
        {**job, "relevance_score": round(score, 4)}
        for job, score in zip(jobs, all_scores)
    ]
    scored.sort(key=lambda j: j["relevance_score"], reverse=True)

    print(f"[ranking] Done. Top score: {scored[0]['relevance_score']:.3f}  "
          f"Median: {scored[len(scored)//2]['relevance_score']:.3f}")
    return {**state, "scored_jobs": scored}


def extract_top_jds(state: RankingState) -> RankingState:
    """
    Node 4: Extract jd_structured for the top N jobs only.
    Groq calls limited to TOP_N_FOR_GROQ — well within free tier.
    Adds a 1.5s inter-call delay to respect TPM limits.
    """
    if state.get("error") or not state.get("scored_jobs"):
        return state

    groq = _get_groq()
    jobs = state["scored_jobs"]
    top_jobs = jobs[:TOP_N_FOR_GROQ]
    needs_extraction = [j for j in top_jobs if not j.get("jd_structured")]

    if not needs_extraction:
        print(f"[ranking] JD structures already present for top {len(top_jobs)} jobs — skipping extraction.")
        return state

    print(f"[ranking] Extracting JD structure for {len(needs_extraction)} top jobs (with rate-limit backoff)...")
    supabase = get_supabase()

    for i, job in enumerate(needs_extraction):
        jd_raw = (job.get("jd_raw") or "")[:2000]
        if not jd_raw.strip():
            job["jd_structured"] = {"required_skills": [], "nice_to_haves": [], "seniority": "unknown", "tech_stack": []}
            continue

        prompt = (
            "Extract structured information from this job description.\n"
            "Return ONLY valid JSON with exactly these keys (no markdown, no extra text):\n"
            '  "required_skills" — array of skills explicitly required for the role\n'
            '  "nice_to_haves"   — array of preferred but optional skills\n'
            '  "seniority"       — one of: junior, mid, senior, staff\n'
            '  "tech_stack"      — array of specific tools/frameworks/languages mentioned\n\n'
            "Example of the JSON format (with placeholder values — extract REAL values from the JD):\n"
            '{"required_skills": ["communication", "data analysis"], '
            '"nice_to_haves": ["project management"], '
            '"seniority": "mid", '
            '"tech_stack": ["SQL", "Excel"]}\n\n'
            "Job description:\n" + jd_raw
        )
        text = _groq_call_with_retry(groq, prompt, max_tokens=400)
        parsed = _parse_json_response(text)
        job["jd_structured"] = parsed or {
            "required_skills": [], "nice_to_haves": [], "seniority": "unknown", "tech_stack": []
        }

        # Persist to jobs table so we don't re-extract next time
        supabase.table("jobs").update(
            {"jd_structured": job["jd_structured"]}
        ).eq("id", job["id"]).execute()

        # Respect TPM: ~400 tokens/call, limit 6000/min → max 15 calls/min → 4s apart
        # Use 2s here since we already built in retry backoff above
        if i < len(needs_extraction) - 1:
            time.sleep(2.0)

    print(f"[ranking] JD extraction complete.")
    return state


def _match_skills(cv_structured: dict, jd_structured: dict) -> tuple[list[str], list[str]]:
    """
    Deterministic skill matching in Python — no LLM involved.

    Strategy (checked in order, first match wins):
      1. Case-insensitive exact match             "TensorFlow" == "tensorflow"
      2. Normalised token match                   "scikit learn" ≈ "scikit-learn"
      3. One is a substring of the other          "AWS" in "AWS SageMaker"
      4. Known alias pairs                        "AWS" ↔ "Amazon Web Services"

    Also searches CV experience descriptions so skills mentioned in bullet points
    (but not listed in the skills array) are picked up.
    """
    # Common aliases — extend this list freely
    ALIASES: list[set[str]] = [
        {"aws", "amazon web services", "amazon aws"},
        {"gcp", "google cloud", "google cloud platform"},
        {"azure", "microsoft azure"},
        {"ml", "machine learning"},
        {"dl", "deep learning"},
        {"nlp", "natural language processing"},
        {"cv", "computer vision"},
        {"pytorch", "torch"},
        {"tf", "tensorflow"},
        {"sk", "sklearn", "scikit-learn", "scikit learn"},
        {"hf", "huggingface", "hugging face"},
        {"llm", "large language model", "large language models"},
        {"genai", "generative ai"},
        {"k8s", "kubernetes"},
        {"js", "javascript"},
        {"ts", "typescript"},
        {"node", "node.js", "nodejs"},
        {"react", "reactjs", "react.js"},
        {"pg", "postgres", "postgresql"},
        {"mongo", "mongodb"},
        {"ci/cd", "ci cd", "continuous integration"},
        {"oop", "object oriented", "object-oriented"},
        {"rest", "rest api", "restful"},
    ]

    def _norm(s: str) -> str:
        return s.lower().replace("-", " ").replace("_", " ").replace(".", " ").strip()

    # Build a rich set of candidate "tokens" from CV
    cv_skills_raw: list[str] = cv_structured.get("skills") or []
    cv_tokens: set[str] = {_norm(s) for s in cv_skills_raw}

    # Also pull terms out of experience descriptions (picks up skills in bullet points)
    for exp in (cv_structured.get("experience") or []):
        for field in ("description", "title", "technologies"):
            text = exp.get(field) or ""
            # Add individual words and bigrams from descriptions
            words = _norm(text).split()
            cv_tokens.update(words)
            cv_tokens.update(" ".join(words[i:i+2]) for i in range(len(words)-1))

    def _cv_has(skill: str) -> bool:
        norm_skill = _norm(skill)

        # 1. Exact normalised match
        if norm_skill in cv_tokens:
            return True

        # 2. Substring in either direction
        if any(norm_skill in t or t in norm_skill for t in cv_tokens if len(t) > 2):
            return True

        # 3. Alias lookup
        for alias_group in ALIASES:
            if norm_skill in alias_group:
                if alias_group & cv_tokens:
                    return True
                # Also check substring against aliases
                if any(a in t or t in a for a in alias_group for t in cv_tokens if len(t) > 2):
                    return True

        return False

    required = jd_structured.get("required_skills") or []
    stack    = jd_structured.get("tech_stack") or []
    # Deduplicate while preserving order
    seen: set[str] = set()
    all_required: list[str] = []
    for s in required + stack:
        if s.lower() not in seen:
            seen.add(s.lower())
            all_required.append(s)

    matched  = [s for s in all_required if _cv_has(s)]
    missing  = [s for s in all_required if not _cv_has(s)]
    return matched, missing


def analyze_gaps(state: RankingState) -> RankingState:
    """
    Node 5: Gap analysis for top N jobs.

    Skill matching is done deterministically in Python (_match_skills).
    Groq is only used for the one-sentence qualitative summary + gap_severity,
    which halves token usage and eliminates false negatives on skill matching.
    """
    if state.get("error") or not state.get("scored_jobs"):
        return state

    groq = _get_groq()
    cv_structured = state["profile"].get("cv_structured") or {}
    jobs = state["scored_jobs"]
    top_jobs = jobs[:TOP_N_FOR_GROQ]
    rest = jobs[TOP_N_FOR_GROQ:]

    cv_exp = cv_structured.get("experience") or []
    cv_exp_text = "; ".join(
        f"{e.get('title')} at {e.get('company')}" for e in cv_exp[:3]
    )

    print(f"[ranking] Running gap analysis for top {len(top_jobs)} jobs...")

    for i, job in enumerate(top_jobs):
        jd_structured = job.get("jd_structured") or {}
        required = jd_structured.get("required_skills") or []
        stack    = jd_structured.get("tech_stack") or []
        seniority = jd_structured.get("seniority", "unknown")

        if not required and not stack:
            job["gap_analysis"] = {
                "matched_skills": [], "missing_skills": [],
                "gap_severity": "unknown",
                "summary": "Gap analysis unavailable — no structured skills found in JD.",
            }
            continue

        # --- Deterministic skill matching (Python, no API) ---
        matched, missing = _match_skills(cv_structured, jd_structured)

        # --- Groq: qualitative summary + gap severity only ---
        prompt = (
            f"A candidate is applying for '{job.get('title', '')}' (seniority: {seniority}).\n"
            f"Candidate experience: {cv_exp_text or 'not specified'}\n"
            f"Skills they HAVE that match: {', '.join(matched[:12]) or 'none identified'}\n"
            f"Skills they are MISSING: {', '.join(missing[:12]) or 'none'}\n\n"
            "Based only on the above, provide:\n"
            '- gap_severity: "none" (0 missing), "low" (1-2 missing), "medium" (3-4), "high" (5+)\n'
            "- summary: one sentence assessing overall fit\n\n"
            'Respond with ONLY valid JSON: {"gap_severity": "low", "summary": "..."}'
        )
        text = _groq_call_with_retry(groq, prompt, max_tokens=120)
        parsed = _parse_json_response(text) or {}

        job["gap_analysis"] = {
            "matched_skills": matched,
            "missing_skills": missing,
            "gap_severity": parsed.get("gap_severity", "low" if len(missing) <= 2 else "medium"),
            "summary": parsed.get("summary", f"{len(matched)} skills matched, {len(missing)} gaps identified."),
        }

        if i < len(top_jobs) - 1:
            time.sleep(2.0)

    # Jobs outside top N: still run Python matching (free), skip Groq summary
    for job in rest:
        jd_structured = job.get("jd_structured") or {}
        if jd_structured.get("required_skills") or jd_structured.get("tech_stack"):
            matched, missing = _match_skills(cv_structured, jd_structured)
            n_miss = len(missing)
            job["gap_analysis"] = {
                "matched_skills": matched,
                "missing_skills": missing,
                "gap_severity": "none" if n_miss == 0 else "low" if n_miss <= 2 else "medium" if n_miss <= 4 else "high",
                "summary": f"{len(matched)} skills matched, {n_miss} gaps identified.",
            }
        else:
            job["gap_analysis"] = {
                "matched_skills": [], "missing_skills": [],
                "gap_severity": "unknown",
                "summary": "No structured JD data available for this job.",
            }

    print("[ranking] Gap analysis complete.")
    return state


def assign_strategies(state: RankingState) -> RankingState:
    """Node 6: Assign strategy label from score + gap severity."""
    if state.get("error") or not state.get("scored_jobs"):
        return state

    def _strategy(score: float, gap_severity: str) -> str:
        if gap_severity == "high" and score >= 0.50:
            score = max(0.29, score - 0.25)
        if score >= 0.75:
            return "strong_match"
        elif score >= 0.50:
            return "decent"
        elif score >= 0.30:
            return "stretch"
        return "skip"

    def _reasoning(job: dict, strategy: str) -> str:
        gap = job.get("gap_analysis") or {}
        matched = gap.get("matched_skills") or []
        missing = gap.get("missing_skills") or []
        summary = gap.get("summary", "")
        score = job.get("relevance_score", 0)
        base = f"Relevance score: {score:.0%}. "
        if strategy == "strong_match":
            return base + (f"Key matches: {', '.join(matched[:3])}. " if matched else "") + summary
        elif strategy == "decent":
            return base + (f"Minor gaps: {', '.join(missing[:2])}. " if missing else "") + summary
        elif strategy == "stretch":
            return base + (f"Notable gaps: {', '.join(missing[:3])}. " if missing else "") + summary
        return base + "Poor fit — consider skipping. " + summary

    for job in state["scored_jobs"]:
        gap_severity = (job.get("gap_analysis") or {}).get("gap_severity", "unknown")
        strategy = _strategy(job["relevance_score"], gap_severity)
        job["strategy"] = strategy
        job["strategy_reasoning"] = _reasoning(job, strategy)

    return state


def store_rankings(state: RankingState) -> RankingState:
    """Node 7: Upsert all rankings to job_rankings table."""
    if state.get("error") or not state.get("scored_jobs"):
        print("[ranking] No jobs to store.")
        return {**state, "rankings": []}

    supabase = get_supabase()
    user_id = state["user_id"]
    jobs = state["scored_jobs"]

    rows = [
        {
            "user_id": user_id,
            "job_id": job["id"],
            "relevance_score": job["relevance_score"],
            "gap_analysis": job.get("gap_analysis"),
            "strategy": job.get("strategy"),
            "strategy_reasoning": job.get("strategy_reasoning"),
        }
        for job in jobs
    ]

    BATCH = 100
    for i in range(0, len(rows), BATCH):
        supabase.table("job_rankings").upsert(
            rows[i: i + BATCH], on_conflict="user_id,job_id"
        ).execute()

    print(f"[ranking] ✅ Stored {len(rows)} rankings for user {user_id[:8]}...")
    return {**state, "rankings": rows}


# ─── Graph ───────────────────────────────────────────────────────────────────

def _build_graph():
    graph = StateGraph(RankingState)
    graph.add_node("load_profile", load_profile)
    graph.add_node("fetch_unranked_jobs", fetch_unranked_jobs)
    graph.add_node("score_jobs_raw", score_jobs_raw)
    graph.add_node("extract_top_jds", extract_top_jds)
    graph.add_node("analyze_gaps", analyze_gaps)
    graph.add_node("assign_strategies", assign_strategies)
    graph.add_node("store_rankings", store_rankings)

    graph.set_entry_point("load_profile")
    graph.add_edge("load_profile", "fetch_unranked_jobs")
    graph.add_edge("fetch_unranked_jobs", "score_jobs_raw")
    graph.add_edge("score_jobs_raw", "extract_top_jds")
    graph.add_edge("extract_top_jds", "analyze_gaps")
    graph.add_edge("analyze_gaps", "assign_strategies")
    graph.add_edge("assign_strategies", "store_rankings")
    graph.add_edge("store_rankings", END)
    return graph.compile()


_ranking_graph = None

def _get_graph():
    global _ranking_graph
    if _ranking_graph is None:
        _ranking_graph = _build_graph()
    return _ranking_graph


# ─── Public API ──────────────────────────────────────────────────────────────

async def run_ranking(user_id: str) -> dict:
    """Run the full ranking pipeline for one user (async-safe via executor)."""
    graph = _get_graph()
    initial_state: RankingState = {
        "user_id": user_id,
        "profile": {},
        "cv_text": "",
        "unranked_jobs": [],
        "scored_jobs": [],
        "rankings": [],
        "error": None,
    }
    import asyncio
    loop = asyncio.get_event_loop()
    final_state = await loop.run_in_executor(None, graph.invoke, initial_state)

    if final_state.get("error"):
        return {"status": "error", "error": final_state["error"]}
    return {"status": "done", "ranked": len(final_state.get("rankings") or [])}


async def run_ranking_all_users() -> None:
    """Daily scheduled job — rank for every user with a profile."""
    import asyncio
    supabase = get_supabase()
    result = supabase.table("profiles").select("id").execute()
    user_ids = [row["id"] for row in (result.data or [])]
    print(f"[scheduler] Ranking {len(user_ids)} users...")
    for user_id in user_ids:
        try:
            await run_ranking(user_id)
        except Exception as e:
            print(f"[scheduler] Error for {user_id[:8]}: {e}")
