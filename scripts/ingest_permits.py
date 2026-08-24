#!/usr/bin/env python3
"""
Ingest NYC film permits data from NYC Open Data into PostgreSQL.

Usage:
    python scripts/ingest_permits.py

Environment variables:
    DATABASE_URL: PostgreSQL connection string (default: postgresql://localhost/nyc_tv)
"""

import os
import sys
import requests
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# NYC Open Data API endpoint
NYC_PERMITS_API = "https://data.cityofnewyork.us/resource/tg4x-b46p.json"

def parse_date(date_str):
    """Parse NYC Open Data date format."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f").date()
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

def fetch_permits(limit=5000, offset=0):
    """Fetch permits from NYC Open Data API."""
    params = {
        "$limit": limit,
        "$offset": offset,
        "$order": "permit_issued_date DESC"
    }

    try:
        response = requests.get(NYC_PERMITS_API, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching permits: {e}")
        return []

def ingest_permits(db_url=None):
    """Main ingestion logic."""

    # Use DATABASE_URL env var or default
    if db_url is None:
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://localhost/nyc_tv"
        )

    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        logger.info(f"Connected to database: {db_url}")
    except Exception as e:
        logger.error(f"Could not connect to database: {e}")
        sys.exit(1)

    insert_sql = """
    INSERT INTO permits (
        event_id, production_name, permit_issued_date,
        permit_expiration_date, production_type, production_company,
        location_address, borough, zip_code, latitude, longitude, status
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (event_id) DO NOTHING;
    """

    total_ingested = 0
    total_skipped = 0
    batch_size = 500

    # Paginate through API results
    offset = 0
    while True:
        logger.info(f"Fetching permits from offset {offset}...")
        permits = fetch_permits(limit=5000, offset=offset)

        if not permits:
            logger.info("No more permits to fetch")
            break

        batch = []
        for permit in permits:
            try:
                # Map NYC Open Data fields to our schema
                row = (
                    permit.get('event_id'),
                    permit.get('production_name'),
                    parse_date(permit.get('permit_issued_date')),
                    parse_date(permit.get('permit_expiration_date')),
                    permit.get('production_type'),
                    permit.get('production_company'),
                    permit.get('location'),
                    permit.get('borough'),
                    permit.get('zip_code'),
                    float(permit.get('latitude')) if permit.get('latitude') else None,
                    float(permit.get('longitude')) if permit.get('longitude') else None,
                    permit.get('status', 'Unknown')
                )
                batch.append(row)
            except Exception as e:
                logger.warning(f"Skipped permit {permit.get('event_id')}: {e}")
                total_skipped += 1

        # Insert batch
        if batch:
            try:
                execute_batch(cursor, insert_sql, batch, page_size=batch_size)
                conn.commit()
                total_ingested += len(batch)
                logger.info(f"Inserted {len(batch)} permits (total: {total_ingested})")
            except Exception as e:
                logger.error(f"Error inserting batch: {e}")
                conn.rollback()

        # Check if we got fewer results than limit (end of data)
        if len(permits) < 5000:
            logger.info("Reached end of data")
            break

        offset += 5000

    # Get final count
    cursor.execute("SELECT COUNT(*) FROM permits;")
    final_count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    logger.info(f"✓ Ingestion complete!")
    logger.info(f"  Total ingested: {total_ingested}")
    logger.info(f"  Total skipped: {total_skipped}")
    logger.info(f"  Total in database: {final_count}")

if __name__ == "__main__":
    ingest_permits()
