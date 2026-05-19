from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from tools.cv_parser import parse_cv, extract_cv_structure
from tools.supabase_client import get_supabase, get_user_id_from_request

router = APIRouter()


class PreferencesUpdate(BaseModel):
    target_roles: Optional[List[str]] = None
    target_locations: Optional[List[str]] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    experience_level: Optional[str] = None
    excluded_companies: Optional[List[str]] = None


@router.post("/cv")
async def upload_cv(request: Request, file: UploadFile = File(...)):
    """
    Accept PDF or DOCX, extract raw text, run Groq structured extraction,
    and store both in the profiles table.
    """
    if file.content_type not in (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    user_id = get_user_id_from_request(request)
    content = await file.read()
    raw_text = parse_cv(content, file.content_type)

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from the CV.")

    structured = await extract_cv_structure(raw_text)

    supabase = get_supabase()
    supabase.table("profiles").upsert(
        {
            "id": user_id,
            "cv_raw_text": raw_text,
            "cv_structured": structured,
        }
    ).execute()

    return {
        "status": "parsed",
        "char_count": len(raw_text),
        "cv_structured": structured,
    }


@router.put("/preferences")
async def update_preferences(request: Request, data: PreferencesUpdate):
    """Update job search preferences for the current user."""
    user_id = get_user_id_from_request(request)
    supabase = get_supabase()

    update_payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_payload:
        raise HTTPException(status_code=400, detail="No fields to update.")

    supabase.table("profiles").upsert({"id": user_id, **update_payload}).execute()
    return {"status": "updated", "fields": list(update_payload.keys())}


@router.get("")
async def get_profile(request: Request):
    """Fetch the current user's full profile."""
    user_id = get_user_id_from_request(request)
    supabase = get_supabase()

    result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found. Complete onboarding first.")
    return result.data
