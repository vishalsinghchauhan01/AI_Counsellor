"""
Admin API endpoints for reseeding data and status monitoring.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks

router = APIRouter()

_status = {"reseeding": False, "last_reseed": None}


@router.post("/reseed")
async def reseed_from_json(background_tasks: BackgroundTasks):
    """
    Force re-seed all data from JSON files into PostgreSQL + re-ingest vectors.
    Use this after updating the JSON files in /data/ to refresh the database
    without needing to restart the server.
    """
    if _status.get("reseeding"):
        raise HTTPException(status_code=409, detail="A reseed is already running")
    _status["reseeding"] = True

    async def _run_reseed():
        try:
            from db.schema import seed_from_json
            from rag.ingest import ingest_all_data
            from rag.vector_store import get_conn
            from pathlib import Path

            # Drop and recreate colleges table for clean state
            conn = get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("DROP TABLE IF EXISTS colleges CASCADE;")
                conn.commit()
            finally:
                conn.close()

            from db.schema import init_tables
            init_tables()

            # Seed from JSON
            data_dir = Path(__file__).resolve().parent.parent.parent / "data"
            seed_from_json(data_dir)

            # Re-ingest vectors
            ingest_all_data()

            _status["last_reseed"] = {"status": "success"}
        except Exception as e:
            _status["last_reseed"] = {"status": "error", "message": str(e)}
        finally:
            _status["reseeding"] = False

    background_tasks.add_task(_run_reseed)
    return {
        "status": "started",
        "message": "Re-seeding from JSON + re-ingesting vectors in background. Check /api/admin/reseed/status for progress.",
    }


@router.get("/reseed/status")
async def get_reseed_status():
    """Check reseed progress."""
    return {
        "reseeding": _status.get("reseeding", False),
        "last_result": _status.get("last_reseed"),
    }
