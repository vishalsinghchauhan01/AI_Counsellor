#!/usr/bin/env python3
"""
Cleanup script to fix existing PostgreSQL data:
1. Delete all 191 colleges from database
2. Allows clean re-scrape with improved name cleaning, city extraction, fees extraction
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.schema import get_all_colleges
from rag.vector_store import get_conn

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def cleanup_colleges():
    """Delete all colleges to prepare for fresh scrape with improved extraction."""
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            # Get current count
            cur.execute("SELECT COUNT(*) FROM colleges;")
            old_count = cur.fetchone()[0]
            print(f"[CLEANUP] Found {old_count} colleges in database")

            # Delete all colleges
            cur.execute("DELETE FROM colleges;")
            conn.commit()

            # Verify
            cur.execute("SELECT COUNT(*) FROM colleges;")
            new_count = cur.fetchone()[0]
            print(f"[SUCCESS] Deleted all colleges. Current count: {new_count}")

    finally:
        conn.close()


def cleanup_vectors():
    """Clear all vectors from pgvector table."""
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            # Check current count
            cur.execute("SELECT COUNT(*) FROM ai_counsellor_vectors;")
            old_count = cur.fetchone()[0]
            print(f"[CLEANUP] Found {old_count} vectors in ai_counsellor_vectors")

            # Delete all vectors
            cur.execute("DELETE FROM ai_counsellor_vectors;")
            conn.commit()

            # Verify
            cur.execute("SELECT COUNT(*) FROM ai_counsellor_vectors;")
            new_count = cur.fetchone()[0]
            print(f"[SUCCESS] Deleted all vectors. Current count: {new_count}")

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("CLEANUP SCRIPT: Prepare for fresh scrape")
    print("=" * 60)
    print()

    print("Step 1: Clean colleges table...")
    cleanup_colleges()
    print()

    print("Step 2: Clean vectors table...")
    cleanup_vectors()
    print()

    print("=" * 60)
    print("[DONE] Cleanup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Run: python -m scraper.pipeline")
    print("2. Run: python -m rag.ingest")
    print()
    print("This will re-scrape all colleges with improved:")
    print("  - College name cleaning (removes course/ranking/fees junk)")
    print("  - City extraction (from college names)")
    print("  - Full course fees (total, not annual)")
    print("=" * 60)
