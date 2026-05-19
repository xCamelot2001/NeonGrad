from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from tools.supabase_client import get_supabase, get_user_id_from_request
import json
import asyncio

router = APIRouter()


class CreateApplication(BaseModel):
    job_id: str


class StatusUpdate(BaseModel):
    status: str


VALID_STATUSES = {"not_applied", "applied", "interviewing", "offer", "rejected"}


@router.post("")
async def create_application(request: Request, data: CreateApplication):
    """Create a new application record for a job."""
    user_id = get_user_id_from_request(request)
    supabase = get_supabase()

    existing = (
        supabase.table("applications")
        .select("id")
        .eq("user_id", user_id)
        .eq("job_id", data.job_id)
        .execute()
    )
    if existing.data:
        return {"id": existing.data[0]["id"], "status": "existing"}

    result = supabase.table("applications").insert(
        {"user_id": user_id, "job_id": data.job_id, "status": "not_applied"}
    ).execute()

    return {"id": result.data[0]["id"], "status": "created"}


@router.get("")
async def list_applications(request: Request):
    """List all applications for the current user with job details."""
    user_id = get_user_id_from_request(request)
    supabase = get_supabase()

    result = (
        supabase.table("applications")
        .select("*, jobs(title, company, location)")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )

    applications = []
    for row in result.data or []:
        job_data = row.pop("jobs", {}) or {}
        applications.append({**row, "job": job_data})

    return {"applications": applications}


@router.get("/{application_id}")
async def get_application(request: Request, application_id: str):
    """Get a single application with job details."""
    user_id = get_user_id_from_request(request)
    supabase = get_supabase()

    result = (
        supabase.table("applications")
        .select("*, jobs(*)")
        .eq("id", application_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Application not found.")

    row = result.data
    job_data = row.pop("jobs", {}) or {}
    return {**row, "job": job_data}


@router.put("/{application_id}/status")
async def update_status(request: Request, application_id: str, data: StatusUpdate):
    """Update application status."""
    if data.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {VALID_STATUSES}")

    user_id = get_user_id_from_request(request)
    supabase = get_supabase()

    supabase.table("applications").update(
        {"status": data.status}
    ).eq("id", application_id).eq("user_id", user_id).execute()

    return {"status": "updated", "new_status": data.status}


@router.get("/{application_id}/tailor")
async def tailor_application(request: Request, application_id: str):
    """
    SSE endpoint — streams the tailoring agent's progress in real time.
    Phase 3 will implement the full LangGraph tailoring agent.
    """
    user_id = get_user_id_from_request(request)
    supabase = get_supabase()

    app_result = (
        supabase.table("applications")
        .select("*, jobs(*)")
        .eq("id", application_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not app_result.data:
        raise HTTPException(status_code=404, detail="Application not found.")

    async def event_stream():
        steps = [
            "🔍 Researching company…",
            "📄 Analysing job description…",
            "✏️  Tailoring CV bullet points…",
            "💌 Writing cover letter…",
            "⚖️  Judge loop: checking quality…",
            "✅ Documents ready!",
        ]
        for step in steps:
            yield f"data: {json.dumps({'type': 'log', 'message': step})}\n\n"
            await asyncio.sleep(1.2)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
