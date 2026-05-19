from fastapi import APIRouter, HTTPException, Request
from tools.supabase_client import get_supabase, get_user_id_from_request
from agents.discovery_agent import run_discovery

router = APIRouter()


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
async def get_ranked_jobs(request: Request, limit: int = 20, skip_strategy: str = "skip"):
    """
    Return ranked jobs for the current user.
    Falls back to raw jobs from the jobs table if no rankings exist yet (pre-Phase 2).
    """
    user_id = get_user_id_from_request(request)
    supabase = get_supabase()

    # Try rankings first (Phase 2+)
    rankings_result = (
        supabase.table("job_rankings")
        .select("*, jobs(*)")
        .eq("user_id", user_id)
        .order("relevance_score", desc=True)
        .limit(limit)
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
        .limit(200)
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

    job_result = supabase.table("jobs").select("*").eq("id", job_id).single().execute()
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found.")

    ranking_result = (
        supabase.table("job_rankings")
        .select("*")
        .eq("job_id", job_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )

    return {
        **job_result.data,
        **(ranking_result.data or {}),
    }
