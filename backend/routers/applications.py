"""
applications.py — FastAPI router for application management (Phase 3).

Endpoints:
  POST   /api/applications              — create application record
  GET    /api/applications              — list user's applications
  GET    /api/applications/{id}         — get single application
  PUT    /api/applications/{id}/status  — update status
  GET    /api/applications/{id}/tailor  — SSE: stream tailoring agent progress
  GET    /api/applications/{id}/download/{cv|cover_letter} — PDF download
"""

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from agents.tailoring_agent import run_tailoring
from tools.pdf_generator import generate_cover_letter_pdf, generate_cv_pdf
from tools.supabase_client import get_supabase, get_user_id_from_request

router = APIRouter()


class CreateApplication(BaseModel):
    job_id: str


class StatusUpdate(BaseModel):
    status: str


VALID_STATUSES = {"not_applied", "applied", "interviewing", "offer", "rejected"}


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("")
async def create_application(request: Request, data: CreateApplication):
    """Create a new application record for a job (idempotent)."""
    user_id  = get_user_id_from_request(request)
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


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_applications(request: Request):
    """List all applications for the current user with job details."""
    user_id  = get_user_id_from_request(request)
    supabase = get_supabase()

    result = (
        supabase.table("applications")
        .select("*, jobs(title, company, location, url)")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )

    applications = []
    for row in result.data or []:
        job_data = row.pop("jobs", {}) or {}
        applications.append({**row, "job": job_data})

    return {"applications": applications}


# ── Get single ────────────────────────────────────────────────────────────────

@router.get("/{application_id}")
async def get_application(request: Request, application_id: str):
    """Get a single application with full job details."""
    user_id  = get_user_id_from_request(request)
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

    row      = result.data
    job_data = row.pop("jobs", {}) or {}
    return {**row, "job": job_data}


# ── Update status ─────────────────────────────────────────────────────────────

@router.put("/{application_id}/status")
async def update_status(request: Request, application_id: str, data: StatusUpdate):
    """Update application status."""
    if data.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}",
        )

    user_id  = get_user_id_from_request(request)
    supabase = get_supabase()

    supabase.table("applications").update(
        {"status": data.status}
    ).eq("id", application_id).eq("user_id", user_id).execute()

    return {"status": "updated", "new_status": data.status}


# ── Tailoring — SSE streaming ─────────────────────────────────────────────────

@router.get("/{application_id}/tailor")
async def tailor_application(request: Request, application_id: str):
    """
    SSE endpoint that streams the LangGraph tailoring agent's progress.

    The frontend uses fetch() (not EventSource) so it can attach the Bearer token.
    Each event is a newline-delimited JSON dict:
      {"type": "log",   "message": "..."}   — progress update
      {"type": "done"}                        — all done, docs saved to DB
      {"type": "error", "message": "..."}   — something went wrong
    """
    user_id  = get_user_id_from_request(request)
    supabase = get_supabase()

    check = (
        supabase.table("applications")
        .select("id")
        .eq("id", application_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Application not found.")

    queue: asyncio.Queue = asyncio.Queue()

    async def event_stream():
        task = asyncio.create_task(run_tailoring(application_id, user_id, queue))
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=180.0)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Tailoring timed out after 3 minutes.'})}\n\n"
                    break

                yield f"data: {json.dumps(item)}\n\n"

                if item.get("type") in ("done", "error"):
                    break
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",   # disable Nginx buffering if behind a proxy
        },
    )


# ── PDF download ──────────────────────────────────────────────────────────────

@router.get("/{application_id}/download/{doc_type}")
async def download_document(request: Request, application_id: str, doc_type: str):
    """
    Download the tailored CV or cover letter as a PDF.
    doc_type must be 'cv' or 'cover_letter'.
    """
    if doc_type not in ("cv", "cover_letter"):
        raise HTTPException(status_code=400, detail="doc_type must be 'cv' or 'cover_letter'.")

    user_id  = get_user_id_from_request(request)
    supabase = get_supabase()

    result = (
        supabase.table("applications")
        .select("tailored_cv_text, cover_letter_text, jobs(title, company)")
        .eq("id", application_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Application not found.")

    row       = result.data
    job       = row.pop("jobs", {}) or {}
    job_title = job.get("title", "Role")
    company   = job.get("company", "Company")

    # Fetch applicant name from profile
    profile_row = (
        supabase.table("profiles")
        .select("cv_structured")
        .eq("id", user_id)
        .single()
        .execute()
    )
    cv_structured  = (profile_row.data or {}).get("cv_structured") or {}
    applicant_name = cv_structured.get("name", "Applicant")

    if doc_type == "cv":
        cv_text = row.get("tailored_cv_text") or ""
        if not cv_text:
            raise HTTPException(status_code=404, detail="Tailored CV not generated yet.")
        pdf_bytes = generate_cv_pdf(cv_text, job_title, company)
        filename  = f"tailored_cv_{company.replace(' ', '_')}.pdf"
    else:
        cl_text = row.get("cover_letter_text") or ""
        if not cl_text:
            raise HTTPException(status_code=404, detail="Cover letter not generated yet.")
        pdf_bytes = generate_cover_letter_pdf(cl_text, applicant_name, job_title, company)
        filename  = f"cover_letter_{company.replace(' ', '_')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
