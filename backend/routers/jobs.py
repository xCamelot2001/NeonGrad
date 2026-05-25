from fastapi import APIRouter, HTTPException, Request
from tools.supabase_client import get_supabase, get_user_id_from_request
from agents.discovery_agent import run_discovery
from agents.ranking_agent import run_ranking

router = APIRouter()


@router.post("/rank")
async def rank_jobs(request: Request):
    """
    Trigger the Job Ranking Agent for the current user.
    Scores all unranked jobs with the sentence-transformer model,
    runs gap analysis via Groq for the top 50, and stores results
    in job_rankings. Called after discovery or when the user clicks
    "Rank Jobs" on the dashboard.
    """
    user_id = get_user_id_from_request(request)
    result = await run_ranking(user_id)
    return result


@router.post("/discover")
async def discover_jobs(request: Request):
    """
    Trigger the Job Discovery Agent for the current user.
    Runs synchronously so the caller can refresh the job list immediately after.
    """
    user_id = get_user_id_from_request(request)
    result = await run_discovery(user_id)
    return {"status": "done", "user_id": user_id, **result}


@router.get("/ranked")
async def get_ranked_jobs(request: Request, skip_strategy: str = "skip"):
    """
    Return all ranked jobs for the current user, sorted by relevance score.
    Falls back to raw jobs from the jobs table if no rankings exist yet (pre-Phase 2).
    """
    user_id = get_user_id_from_request(request)
    supabase = get_supabase()

    # Try rankings first (Phase 2+) — no limit, return everything
    rankings_result = (
        supabase.table("job_rankings")
        .select("*, jobs(*)")
        .eq("user_id", user_id)
        .order("relevance_score", desc=True)
        .execute()
    )

    if rankings_result.data:
        jobs = []
        for row in rankings_result.data:
            job_data = row.pop("jobs", {}) or {}
            jobs.append({
                "job_id": row["job_id"],
                "title": job_data.get("title"),
                "company": job_data.get("company"),
                "location": job_data.get("location"),
                "url": job_data.get("url"),
                "relevance_score": row.get("relevance_score", 0),
                "strategy": row.get("strategy"),
                "strategy_reasoning": row.get("strategy_reasoning"),
                "gap_analysis": row.get("gap_analysis"),
            })
        return {"jobs": jobs, "count": len(jobs)}

    # Phase 1 fallback — show raw jobs unranked (return all stored jobs)
    raw_result = (
        supabase.table("jobs")
        .select("*")
        .order("fetched_at", desc=True)
        .execute()
    )

    jobs = []
    for job in raw_result.data or []:
        jobs.append({
            "job_id": job["id"],
            "title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "url": job.get("url"),
            "relevance_score": None,
            "strategy": "unranked",
            "strategy_reasoning": "Ranking engine coming in Phase 2.",
            "gap_analysis": None,
        })

    return {"jobs": jobs, "count": len(jobs)}


@router.get("/{job_id}")
async def get_job(request: Request, job_id: str):
    """Return a single job with the current user's ranking data."""
    user_id = get_user_id_from_request(request)
    supabase = get_supabase()

    job_result = supabase.table("jobs").select("*").eq("id", job_id).execute()
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found.")

    # Use limit(1) instead of .single() so 0 rows doesn't raise PGRST116
    ranking_result = (
        supabase.table("job_rankings")
        .select("*")
        .eq("job_id", job_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    ranking_data = ranking_result.data[0] if ranking_result.data else {}

    return {
        **job_result.data[0],
        **ranking_data,
    }
