"""
Admin API endpoints for manual scrape triggers and status monitoring.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks

router = APIRouter()

# In-memory scrape status
_status = {"running": False, "last_result": None}


async def _run_pipeline():
    """Run the pipeline and update status."""
    from scraper.pipeline import run_full_pipeline
    try:
        result = await run_full_pipeline()
        _status["last_result"] = result
    except Exception as e:
        _status["last_result"] = {"status": "error", "message": str(e)}
    finally:
        _status["running"] = False


@router.post("/scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    """Manually trigger a full scrape pipeline. Runs in background."""
    if _status["running"]:
        raise HTTPException(status_code=409, detail="A scrape is already running")
    _status["running"] = True
    background_tasks.add_task(_run_pipeline)
    return {"status": "started", "message": "Scrape pipeline started in background"}


@router.get("/scrape/status")
async def get_scrape_status():
    """Check current scrape status and last result."""
    return {
        "running": _status["running"],
        "last_result": _status["last_result"],
    }


@router.get("/scrape/history")
async def get_scrape_history():
    """Return past scrape run reports."""
    from scraper.pipeline import load_run_reports
    return {"reports": load_run_reports()}
