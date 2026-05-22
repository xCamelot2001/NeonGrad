"""
NeonGrad daily job scheduler — Phase 2.

Runs discover → rank for all users every day at 06:00 UTC.
APScheduler is started on FastAPI startup and stopped on shutdown.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from agents.discovery_agent import run_discovery
from agents.ranking_agent import run_ranking_all_users
from tools.supabase_client import get_supabase

logger = logging.getLogger("neongrad.scheduler")

scheduler = AsyncIOScheduler(timezone="UTC")


async def _daily_pipeline() -> None:
    """
    Daily pipeline: discover fresh jobs for all users, then re-rank.
    Runs at 06:00 UTC — staggered so users have fresh rankings by morning.
    """
    logger.info("[scheduler] Starting daily pipeline...")
    supabase = get_supabase()

    # 1. Run discovery for each user
    profiles_result = supabase.table("profiles").select("id").execute()
    user_ids = [row["id"] for row in (profiles_result.data or [])]
    logger.info(f"[scheduler] Discovering jobs for {len(user_ids)} users")

    for user_id in user_ids:
        try:
            result = await run_discovery(user_id)
            new_jobs = result.get("new_jobs", 0)
            logger.info(f"[scheduler] Discovery done for {user_id[:8]}...: {new_jobs} new jobs")
        except Exception as e:
            logger.error(f"[scheduler] Discovery failed for {user_id[:8]}: {e}")

    # 2. Rank all users (processes only newly discovered, unranked jobs)
    logger.info("[scheduler] Starting ranking pass...")
    try:
        await run_ranking_all_users()
    except Exception as e:
        logger.error(f"[scheduler] Ranking failed: {e}")

    logger.info("[scheduler] Daily pipeline complete.")


def start_scheduler() -> None:
    """Register jobs and start the scheduler. Called on FastAPI startup."""
    scheduler.add_job(
        _daily_pipeline,
        trigger=CronTrigger(hour=6, minute=0),
        id="daily_pipeline",
        name="Daily discover + rank",
        replace_existing=True,
        misfire_grace_time=3600,  # run even if up to 1 hour late
    )
    scheduler.start()
    logger.info("[scheduler] APScheduler started — daily pipeline at 06:00 UTC")


def stop_scheduler() -> None:
    """Stop the scheduler gracefully. Called on FastAPI shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[scheduler] APScheduler stopped.")
