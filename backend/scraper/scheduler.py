"""
APScheduler integration with FastAPI lifecycle.
Runs the full scraping pipeline on a weekly cron schedule.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from scraper.config import SCRAPE_CRON_DAY, SCRAPE_CRON_HOUR, SCRAPE_CRON_MINUTE, SCRAPER_ENABLED

logger = logging.getLogger("scraper.scheduler")

scheduler = AsyncIOScheduler()


async def _scheduled_scrape_job():
    """Wrapper for the scheduled pipeline run."""
    logger.info("Scheduled weekly scrape triggered")
    try:
        from scraper.pipeline import run_full_pipeline
        result = await run_full_pipeline()
        logger.info(f"Scheduled scrape completed: {result.get('status')}")
    except Exception as e:
        logger.error(f"Scheduled scrape failed: {e}")


def start_scheduler():
    """Start the APScheduler. Called from FastAPI startup."""
    if not SCRAPER_ENABLED:
        logger.info("Scraper scheduler disabled (SCRAPER_ENABLED=false)")
        return

    scheduler.add_job(
        _scheduled_scrape_job,
        trigger=CronTrigger(
            day_of_week=SCRAPE_CRON_DAY,
            hour=SCRAPE_CRON_HOUR,
            minute=SCRAPE_CRON_MINUTE,
        ),
        id="weekly_scrape",
        name="Weekly data scrape and re-ingestion",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"Scheduler started. Weekly scrape: {SCRAPE_CRON_DAY} at "
        f"{SCRAPE_CRON_HOUR:02d}:{SCRAPE_CRON_MINUTE:02d}"
    )


def stop_scheduler():
    """Stop the scheduler. Called from FastAPI shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
