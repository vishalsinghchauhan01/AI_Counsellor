"""
One-time script: Drop colleges table, re-create, re-seed from updated JSON,
and re-ingest all data into the vector store.

Run from backend/:
    python reseed.py

This is needed when:
- University data structure changed (e.g., flat fees → nested fees)
- New universities were added to the JSON
- NIRF/NAAC data was added
- college_to_text() output format changed (affects vector embeddings)
"""
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("reseed")


def main():
    logger.info("=" * 60)
    logger.info("RESEED: Drop colleges → Re-create → Re-seed → Re-ingest")
    logger.info("=" * 60)

    # Step 1: Drop and recreate colleges table
    logger.info("\n[1/4] Dropping colleges table...")
    from rag.vector_store import get_conn
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS colleges CASCADE;")
        conn.commit()
        logger.info("  ✓ colleges table dropped")
    finally:
        conn.close()

    # Step 2: Recreate all tables
    logger.info("\n[2/4] Recreating tables...")
    from db.schema import init_tables
    init_tables()
    logger.info("  ✓ Tables recreated")

    # Step 3: Seed from JSON
    logger.info("\n[3/4] Seeding from uttarakhand_universities.json...")
    from db.schema import seed_from_json
    data_dir = Path(__file__).resolve().parent.parent / "data"
    seed_from_json(data_dir)
    logger.info("  ✓ Database seeded")

    # Step 4: Verify
    from db.schema import get_all_colleges
    colleges = get_all_colleges()
    logger.info(f"  ✓ {len(colleges)} universities now in PostgreSQL")

    # Step 5: Re-ingest into vector store
    logger.info("\n[4/4] Re-ingesting into vector store (this calls OpenAI for embeddings)...")
    from rag.ingest import ingest_all_data
    ingest_all_data()
    logger.info("  ✓ Vector store updated")

    logger.info("\n" + "=" * 60)
    logger.info("DONE. All data refreshed.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
