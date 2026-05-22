"""
tailoring_agent.py — Phase 3 LangGraph tailoring pipeline.

Flow:
  load_context
    → research_company   (Tavily)
    → generate_docs      (Groq: tailor CV + write cover letter)
    → judge_quality      (Groq: score 0–1, give feedback)
    → if score < 0.75 and revisions < 2 → increment_revision → generate_docs
    → store_result       (save to DB, signal SSE done)

Progress is streamed to the caller via an asyncio.Queue (one dict per event):
  {"type": "log",   "message": "..."}
  {"type": "done"}
  {"type": "error", "message": "..."}
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Optional, TypedDict

from groq import AsyncGroq
from langgraph.graph import END, StateGraph

from tools.supabase_client import get_supabase
from tools.web_search import search_company

# ── SSE queue registry ────────────────────────────────────────────────────────
# Keyed by application_id so the SSE endpoint can subscribe to progress events.
_log_queues: dict[str, asyncio.Queue] = {}


async def _log(app_id: str, message: str) -> None:
    q = _log_queues.get(app_id)
    if q:
        await q.put({"type": "log", "message": message})


# ── State ─────────────────────────────────────────────────────────────────────

class TailoringState(TypedDict):
    application_id: str
    user_id: str
    # loaded from DB
    job: dict
    profile: dict
    # generated content
    company_research: str
    tailored_cv: str
    cover_letter: str
    # judge loop
    judge_score: float
    judge_feedback: str
    revision_count: int
    # error flag
    error: Optional[str]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _groq() -> AsyncGroq:
    return AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))


def _skill_list(jd_structured: dict) -> str:
    skills = jd_structured.get("required_skills", []) or []
    tech   = jd_structured.get("tech_stack", []) or []
    combined = list(dict.fromkeys(skills + tech))   # deduplicate, preserve order
    return ", ".join(combined) if combined else "see JD"


# ── Node: load_context ────────────────────────────────────────────────────────

async def load_context(state: TailoringState) -> TailoringState:
    app_id  = state["application_id"]
    user_id = state["user_id"]
    await _log(app_id, "📂 Loading application context…")

    supabase = get_supabase()

    app_row = (
        supabase.table("applications")
        .select("*, jobs(*)")
        .eq("id", app_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not app_row.data:
        raise ValueError(f"Application {app_id} not found for user {user_id}")

    row = app_row.data
    job = row.pop("jobs", {}) or {}

    profile_row = (
        supabase.table("profiles")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )
    profile = profile_row.data or {}

    return {**state, "job": job, "profile": profile}


# ── Node: research_company ────────────────────────────────────────────────────

async def research_company(state: TailoringState) -> TailoringState:
    app_id  = state["application_id"]
    company = state["job"].get("company", "the company")
    await _log(app_id, f"🔍 Researching {company}…")

    research = await search_company(company)
    await _log(app_id, "✅ Company research complete")

    return {**state, "company_research": research}


# ── Node: generate_docs ───────────────────────────────────────────────────────

async def generate_docs(state: TailoringState) -> TailoringState:
    app_id   = state["application_id"]
    job      = state["job"]
    profile  = state["profile"]
    revision = state["revision_count"]
    feedback = state.get("judge_feedback", "")

    client = _groq()

    jd_structured = job.get("jd_structured") or {}
    skills_str    = _skill_list(jd_structured)
    jd_raw        = (job.get("jd_raw") or "")[:3000]
    cv_text       = (profile.get("cv_raw_text") or "No CV provided")

    cv_structured  = profile.get("cv_structured") or {}
    applicant_name = cv_structured.get("name", "the applicant")

    feedback_block = (
        f"\n\nJUDGE FEEDBACK (from previous attempt — address these issues):\n{feedback}"
        if feedback else ""
    )

    # ── Tailor CV ──────────────────────────────────────────────────────────
    await _log(app_id, f"✏️  {'Revising' if revision > 0 else 'Tailoring'} CV (attempt {revision + 1}/3)…")

    cv_prompt = (
        "You are an expert CV tailoring specialist. Rewrite the candidate's CV "
        "so it resonates with the target job while staying 100% truthful.\n\n"
        "ORIGINAL CV:\n"
        + cv_text
        + "\n\nJOB TITLE: "  + (job.get("title") or "")
        + "\nCOMPANY: "      + (job.get("company") or "")
        + "\n\nJOB DESCRIPTION:\n" + jd_raw
        + "\n\nKEY SKILLS / TECH STACK TO HIGHLIGHT: " + skills_str
        + feedback_block
        + "\n\nRULES:\n"
        "1. Mirror exact JD keywords naturally — don't keyword-stuff.\n"
        "2. Quantify achievements wherever possible.\n"
        "3. Lead with the most relevant sections.\n"
        "4. NEVER invent skills, jobs, or qualifications not in the original CV.\n"
        "5. Preserve all original section headers; upgrade the content inside them.\n"
        "6. Keep a professional, confident tone.\n\n"
        "Output the complete tailored CV text."
    )

    cv_resp = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": cv_prompt}],
        temperature=0.35,
        max_tokens=2048,
    )
    tailored_cv = cv_resp.choices[0].message.content.strip()

    # ── Write Cover Letter ─────────────────────────────────────────────────
    await _log(app_id, "💌 Writing cover letter…")

    cl_prompt = (
        "Write a compelling, personalised cover letter for this job application.\n\n"
        "APPLICANT: " + applicant_name
        + "\nROLE: "     + (job.get("title") or "") + " at " + (job.get("company") or "")
        + "\nLOCATION: " + (job.get("location") or "")
        + "\n\nCOMPANY RESEARCH:\n" + (state.get("company_research") or "No research available.")
        + "\n\nKEY ACHIEVEMENTS FROM TAILORED CV:\n" + tailored_cv[:2000]
        + "\n\nJOB DESCRIPTION:\n" + jd_raw
        + feedback_block
        + "\n\nWRITE EXACTLY 3 PARAGRAPHS:\n"
        "1. Opening — reference something SPECIFIC about the company from the research. "
        "Why this company, why this role. Do NOT start with 'I am writing to apply…'.\n"
        "2. Middle — 2–3 concrete examples of why you're the right fit; tie real CV "
        "achievements to JD requirements by name.\n"
        "3. Closing — enthusiasm, call to action, professional sign-off including your name.\n\n"
        "Tone: professional but warm and confident. 280–350 words total.\n"
        "Output only the cover letter text (no subject line, no metadata)."
    )

    cl_resp = await client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": cl_prompt}],
        temperature=0.45,
        max_tokens=900,
    )
    cover_letter = cl_resp.choices[0].message.content.strip()

    return {**state, "tailored_cv": tailored_cv, "cover_letter": cover_letter}


# ── Node: judge_quality ───────────────────────────────────────────────────────

async def judge_quality(state: TailoringState) -> TailoringState:
    app_id   = state["application_id"]
    revision = state["revision_count"]
    await _log(app_id, f"⚖️  Judging quality (attempt {revision + 1}/3)…")

    client = _groq()
    job           = state["job"]
    jd_structured = job.get("jd_structured") or {}
    skills_str    = _skill_list(jd_structured)

    judge_prompt = (
        "You are a strict application quality judge. Evaluate the package below.\n\n"
        "JOB: "              + (job.get("title") or "") + " at " + (job.get("company") or "")
        + "\nREQUIRED SKILLS: " + skills_str
        + "\n\nTAILORED CV (first 1400 chars):\n" + state["tailored_cv"][:1400]
        + "\n\nCOVER LETTER:\n" + state["cover_letter"]
        + "\n\nScore 0.0–1.0 across:\n"
        "• Keyword integration (required skills woven in naturally?)\n"
        "• Specificity (cover letter genuinely specific to THIS company?)\n"
        "• Coherence (consistent, compelling story?)\n"
        "• Quality (error-free, professional?)\n\n"
        "Return ONLY valid JSON — no markdown, no extra text:\n"
        '{"score": 0.87, "feedback": "One specific improvement needed."}'
    )

    try:
        resp = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0.1,
            max_tokens=150,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown code fences if the model adds them
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        parsed   = json.loads(raw)
        score    = float(parsed.get("score", 0.8))
        feedback = str(parsed.get("feedback", ""))
    except Exception:
        score    = 0.85   # assume good if JSON parse fails
        feedback = ""

    label = "✅ Excellent" if score >= 0.85 else ("👍 Good" if score >= 0.75 else "🔄 Needs revision")
    await _log(app_id, f"📊 Quality score: {score:.0%} — {label}")

    return {**state, "judge_score": score, "judge_feedback": feedback}


# ── Node: increment_revision ──────────────────────────────────────────────────

async def increment_revision(state: TailoringState) -> TailoringState:
    new_count = state["revision_count"] + 1
    app_id    = state["application_id"]
    await _log(app_id, f"🔁 Applying judge feedback, revising (pass {new_count + 1}/3)…")
    return {**state, "revision_count": new_count}


# ── Node: store_result ────────────────────────────────────────────────────────

async def store_result(state: TailoringState) -> TailoringState:
    app_id = state["application_id"]
    await _log(app_id, "💾 Saving tailored documents to database…")

    supabase = get_supabase()
    supabase.table("applications").update(
        {
            "tailored_cv_text":  state["tailored_cv"],
            "cover_letter_text": state["cover_letter"],
            "tailored_at":       datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", app_id).execute()

    await _log(app_id, "🎉 Done! Your tailored CV and cover letter are ready.")

    q = _log_queues.get(app_id)
    if q:
        await q.put({"type": "done"})

    return state


# ── Conditional edge ──────────────────────────────────────────────────────────

def _should_revise(state: TailoringState) -> str:
    if state["judge_score"] < 0.75 and state["revision_count"] < 2:
        return "revise"
    return "store"


# ── Build graph ───────────────────────────────────────────────────────────────

def _build_graph():
    g = StateGraph(TailoringState)

    g.add_node("load_context",       load_context)
    g.add_node("research_company",   research_company)
    g.add_node("generate_docs",      generate_docs)
    g.add_node("judge_quality",      judge_quality)
    g.add_node("increment_revision", increment_revision)
    g.add_node("store_result",       store_result)

    g.set_entry_point("load_context")
    g.add_edge("load_context",       "research_company")
    g.add_edge("research_company",   "generate_docs")
    g.add_edge("generate_docs",      "judge_quality")
    g.add_conditional_edges(
        "judge_quality",
        _should_revise,
        {"revise": "increment_revision", "store": "store_result"},
    )
    g.add_edge("increment_revision", "generate_docs")
    g.add_edge("store_result",       END)

    return g.compile()


_graph = _build_graph()


# ── Public entry point ────────────────────────────────────────────────────────

async def run_tailoring(
    application_id: str,
    user_id: str,
    queue: asyncio.Queue,
) -> None:
    """
    Run the full tailoring pipeline and stream progress to *queue*.
    Called by the SSE endpoint as a background asyncio task.
    """
    _log_queues[application_id] = queue
    try:
        initial: TailoringState = {
            "application_id":   application_id,
            "user_id":          user_id,
            "job":              {},
            "profile":          {},
            "company_research": "",
            "tailored_cv":      "",
            "cover_letter":     "",
            "judge_score":      0.0,
            "judge_feedback":   "",
            "revision_count":   0,
            "error":            None,
        }
        await _graph.ainvoke(initial)
    except Exception as exc:
        await queue.put({"type": "error", "message": str(exc)})
    finally:
        _log_queues.pop(application_id, None)
