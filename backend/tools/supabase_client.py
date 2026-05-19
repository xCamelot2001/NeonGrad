"""
Supabase client singleton + auth helpers.
"""
import os
from supabase import create_client, Client
from fastapi import Request, HTTPException

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env"
            )
        _client = create_client(url, key)
    return _client


def get_user_id_from_request(request: Request) -> str:
    """
    Extract the real Supabase user ID from the Authorization header.
    The frontend sends: Authorization: Bearer <supabase_access_token>
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    token = auth[7:]
    try:
        supabase = get_supabase()
        user_response = supabase.auth.get_user(token)
        return user_response.user.id
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid auth token: {e}")
