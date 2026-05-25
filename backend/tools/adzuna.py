"""
Adzuna API wrapper.
Docs: https://developer.adzuna.com/docs/search

Free tier: 250 requests/day.
Each search call returns up to 50 results per page.

Location notes:
- "Remote" is not a valid Adzuna `where` value — we omit the param so it searches country-wide.
- Non-GB locations (e.g. "Berlin", "New York") require hitting the correct country endpoint.
  LOCATION_TO_COUNTRY maps common city/country strings to Adzuna country codes.
"""
import os
import httpx
from typing import Optional


ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"

# Locations Adzuna has no `where` value for — search country-wide instead
REMOTE_ALIASES = {"remote", "work from home", "wfh", "anywhere", "worldwide", "global"}

# Map common location strings → Adzuna country codes
# Adzuna supported countries: gb, us, au, ca, de, fr, in, nl, nz, pl, ru, sg, za, br, at, be, ch, mx
LOCATION_TO_COUNTRY: dict[str, str] = {
    # United States
    "usa": "us", "us": "us", "united states": "us",
    "new york": "us", "san francisco": "us", "seattle": "us",
    "austin": "us", "boston": "us", "chicago": "us", "los angeles": "us",
    # Germany
    "germany": "de", "berlin": "de", "munich": "de", "hamburg": "de", "frankfurt": "de",
    # France
    "france": "fr", "paris": "fr", "lyon": "fr",
    # Australia
    "australia": "au", "sydney": "au", "melbourne": "au", "brisbane": "au",
    # Canada
    "canada": "ca", "toronto": "ca", "vancouver": "ca", "montreal": "ca",
    # Netherlands
    "netherlands": "nl", "amsterdam": "nl",
    # India
    "india": "in", "bangalore": "in", "mumbai": "in", "delhi": "in", "hyderabad": "in",
    # Singapore
    "singapore": "sg",
    # UK (all map to gb — the default)
    "uk": "gb", "united kingdom": "gb", "england": "gb",
    "london": "gb", "manchester": "gb", "birmingham": "gb",
    "bristol": "gb", "edinburgh": "gb", "leeds": "gb",
    "liverpool": "gb", "cambridge": "gb", "oxford": "gb",
}


def _resolve_country(location: str, default_country: str) -> str:
    """Return the Adzuna country code for a location string."""
    return LOCATION_TO_COUNTRY.get(location.lower().strip(), default_country)


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
    default_country = os.getenv("ADZUNA_COUNTRY", country)

    if not app_id or not api_key:
        raise RuntimeError("ADZUNA_APP_ID and ADZUNA_API_KEY must be set in .env")

    # Resolve the country code from the location string
    resolved_country = _resolve_country(location, default_country)

    params: dict = {
        "app_id": app_id,
        "app_key": api_key,
        "results_per_page": 50,  # max per page; free tier limits requests (250/day), not results
        "what": role,
    }

    # "Remote" and similar aliases have no Adzuna location value — omit `where` for country-wide search
    if location.lower().strip() not in REMOTE_ALIASES:
        params["where"] = location

    if salary_min:
        params["salary_min"] = salary_min
    if salary_max:
        params["salary_max"] = salary_max

    url = f"{ADZUNA_BASE}/{resolved_country}/search/{page}"

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
