"""
Job Discovery Agent — Phase 1 implementation.

Reads a user's preferences, queries Adzuna for each (role × location) pair,
deduplicates against existing jobs, and stores new ones.

JD structure extraction (Groq) is deferred to Phase 2 — running it here
adds 50+ sequential API calls for a full batch and hangs the request.
"""
from tools.supabase_client import get_supabase
from tools.adzuna import search_jobs


async def run_discovery(user_id: str) -> dict:
    """
    Main entry point for the discovery agent.
    Called synchronously from POST /api/jobs/discover.
    """
    supabase = get_supabase()

    # 1. Load user preferences
    profile_result = (
        supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    )
    if not profile_result.data:
        print(f"[discovery] No profile found for user {user_id} — skipping.")
        return {"status": "no_profile"}

    profile = profile_result.data
    target_roles: list[str] = profile.get("target_roles") or ["Software Engineer"]
    target_locations: list[str] = profile.get("target_locations") or ["London"]
    salary_min: int | None = profile.get("salary_min")
    salary_max: int | None = profile.get("salary_max")

    # 2. Fetch existing external IDs to deduplicate
    existing_result = supabase.table("jobs").select("source, external_id").execute()
    existing_keys = {
        (r["source"], r["external_id"]) for r in (existing_result.data or [])
    }

    # 3. Search Adzuna for each role × location pair, paginating up to 5 pages
    MAX_PAGES = 5
    new_jobs = []
    for role in target_roles:
        for location in target_locations:
            for page in range(1, MAX_PAGES + 1):
                try:
                    results = await search_jobs(
                        role=role,
                        location=location,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        page=page,
                    )
                    if not results:
                        break  # no more results for this role/location
                    added = 0
                    for job in results:
                        key = (job["source"], job["external_id"])
                        if key not in existing_keys:
                            new_jobs.append(job)
                            existing_keys.add(key)
                            added += 1
                    print(f"[discovery] Page {page} — {role} in {location}: {len(results)} fetched, {added} new")
                    if len(results) < 50:
                        break  # fewer than a full page means no more results
                except Exception as e:
                    print(f"[discovery] Adzuna error for {role} in {location} page {page}: {e}")
                    break

    if not new_jobs:
        print(f"[discovery] No new jobs found for user {user_id}.")
        return {"status": "no_new_jobs"}

    # 4. Upsert new jobs to DB (on_conflict ignore handles race conditions)
    try:
        supabase.table("jobs").upsert(
            new_jobs, on_conflict="source,external_id", ignore_duplicates=True
        ).execute()
    except Exception as e:
        print(f"[discovery] DB insert error: {e}")
        return {"status": "db_error", "error": str(e)}

    print(f"[discovery] Stored {len(new_jobs)} new jobs for user {user_id}.")
    return {"status": "done", "new_jobs": len(new_jobs)}
