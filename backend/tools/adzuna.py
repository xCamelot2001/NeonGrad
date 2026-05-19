"""
Adzuna API wrapper.
Docs: https://developer.adzuna.com/docs/search

Free tier: 250 requests/day.
Each search call returns up to 50 results per page.
"""
import os
import httpx
from typing import Optional


ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"


async def search_jobs(
    role: str,
    location: str,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    results_per_page: int = 50,
    page: int = 1,
    country: str = "gb",
) -> list[dict]:
    """
    Search Adzuna for jobs matching a role + location.
    Returns a list of raw job dicts normalised for our schema.
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    api_key = os.getenv("ADZUNA_API_KEY")
    country = os.getenv("ADZUNA_COUNTRY", country)

    if not app_id or not api_key:
        raise RuntimeError("ADZUNA_APP_ID and ADZUNA_API_KEY must be set in .env")

    params: dict = {
        "app_id": app_id,
        "app_key": api_key,
        "results_per_page": 50,  # max per page; free tier limits requests (250/day), not results
        "what": role,
        "where": location,
    }
    if salary_min:
        params["salary_min"] = salary_min
    if salary_max:
        params["salary_max"] = salary_max

    url = f"{ADZUNA_BASE}/{country}/search/{page}"

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    return [_normalise(job) for job in data.get("results", [])]


def _normalise(raw: dict) -> dict:
    """Map Adzuna response fields to our jobs table schema."""
    salary_min = raw.get("salary_min")
    salary_max = raw.get("salary_max")

    return {
        "source": "adzuna",
        "external_id": str(raw["id"]),
        "title": raw.get("title", "").strip(),
        "company": raw.get("company", {}).get("display_name", "Unknown"),
        "location": raw.get("location", {}).get("display_name", ""),
        "salary_min": int(salary_min) if salary_min else None,
        "salary_max": int(salary_max) if salary_max else None,
        "jd_raw": raw.get("description", ""),
        "url": raw.get("redirect_url", ""),
        "posted_at": raw.get("created"),
    }
