#!/usr/bin/env python3
"""
Load NYC Filming Locations CSV into TimescaleDB

This script:
1. Reads data/nyc_filming_locations.csv
2. Parses productions and locations
3. Creates filming events with timestamps
4. Inserts into TimescaleDB (running on Tiger Cloud)

Usage:
    python scripts/load_csv_to_timescaledb.py

Environment variables required:
    TIMESCALE_HOST
    TIMESCALE_PORT (default 5432)
    TIMESCALE_USER
    TIMESCALE_PASSWORD
    TIMESCALE_DB (default tsdb)
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path
import psycopg
from psycopg import sql

# Configuration from environment
TIMESCALE_HOST = os.getenv("TIMESCALE_HOST")
TIMESCALE_PORT = os.getenv("TIMESCALE_PORT", "5432")
TIMESCALE_USER = os.getenv("TIMESCALE_USER")
TIMESCALE_PASSWORD = os.getenv("TIMESCALE_PASSWORD")
TIMESCALE_DB = os.getenv("TIMESCALE_DB", "tsdb")
CSV_PATH = Path(__file__).parent.parent / "data" / "nyc_filming_locations.csv"

# Validate environment
if not all([TIMESCALE_HOST, TIMESCALE_USER, TIMESCALE_PASSWORD]):
    print("❌ Missing environment variables:")
    print("   Set: TIMESCALE_HOST, TIMESCALE_USER, TIMESCALE_PASSWORD")
    sys.exit(1)

if not CSV_PATH.exists():
    print(f"❌ CSV file not found: {CSV_PATH}")
    sys.exit(1)

def connect_to_timescale():
    """Create connection to TimescaleDB"""
    try:
        conn = psycopg.connect(
            f"postgresql://{TIMESCALE_USER}:{TIMESCALE_PASSWORD}@"
            f"{TIMESCALE_HOST}:{TIMESCALE_PORT}/{TIMESCALE_DB}"
        )
        print(f"✅ Connected to TimescaleDB at {TIMESCALE_HOST}")
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

def parse_year(year_str):
    """Parse year from various formats"""
    if not year_str or year_str.lower() == "current":
        return None
    try:
        return int(year_str.split("-")[0])  # Handle "2024-Present" format
    except:
        return None

def generate_timestamp(year):
    """Generate timestamp for filming event"""
    if not year:
        # Default to recent date for "current" productions
        return datetime(2026, 6, 1)
    try:
        return datetime(int(year), 6, 15)  # Mid-year placeholder
    except:
        return datetime(2026, 6, 1)

def load_csv_to_database(conn):
    """Load CSV data into database"""

    # Track what we're loading
    productions_added = set()
    locations_added = set()
    events_added = 0
    skipped = 0

    with conn.cursor() as cur:
        # Read CSV
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    title = row.get('Title', '').strip()
                    address = row.get('Address', '').strip()
                    borough_neighborhood = row.get('Borough/Neighborhood', '').strip()
                    description = row.get('Description', '').strip()
                    category = row.get('Category', '').strip()
                    season_episode = row.get('Season/Episode', '').strip()
                    year = row.get('Year', '').strip()
                    source = row.get('Source', '').strip()

                    # Skip if missing critical fields
                    if not title or not address:
                        skipped += 1
                        continue

                    # Parse borough/neighborhood
                    if ', ' in borough_neighborhood:
                        parts = borough_neighborhood.rsplit(', ', 1)
                        neighborhood = parts[0].strip()
                        borough = parts[1].strip() if len(parts) > 1 else None
                    else:
                        neighborhood = borough_neighborhood
                        borough = None

                    # Insert or get production
                    if title not in productions_added:
                        cur.execute(
                            """INSERT INTO productions (title, category, year_aired, description, source)
                               VALUES (%s, %s, %s, %s, %s)
                               ON CONFLICT (title) DO NOTHING""",
                            (title, category or None, parse_year(year), description or None, source or None)
                        )
                        productions_added.add(title)

                    # Get production ID
                    cur.execute("SELECT id FROM productions WHERE title = %s", (title,))
                    prod_result = cur.fetchone()
                    if not prod_result:
                        skipped += 1
                        continue
                    production_id = prod_result[0]

                    # Insert or get location
                    location_key = (address, borough)
                    if location_key not in locations_added:
                        cur.execute(
                            """INSERT INTO locations (address, borough, neighborhood, source)
                               VALUES (%s, %s, %s, %s)
                               ON CONFLICT (address, borough) DO NOTHING""",
                            (address, borough, neighborhood or None, source or None)
                        )
                        locations_added.add(location_key)

                    # Get location ID
                    cur.execute(
                        "SELECT id FROM locations WHERE address = %s AND borough = %s",
                        (address, borough)
                    )
                    loc_result = cur.fetchone()
                    if not loc_result:
                        skipped += 1
                        continue
                    location_id = loc_result[0]

                    # Insert filming event
                    timestamp = generate_timestamp(parse_year(year))
                    cur.execute(
                        """INSERT INTO filming_events
                           (time, production_id, location_id, scene_description, season_episode, source_credit)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (timestamp, production_id, location_id, description or None,
                         season_episode or None, source or None)
                    )
                    events_added += 1

                except Exception as e:
                    print(f"⚠️  Error loading row: {e}")
                    skipped += 1
                    continue

        # Commit all changes
        conn.commit()

    return {
        'productions': len(productions_added),
        'locations': len(locations_added),
        'events': events_added,
        'skipped': skipped
    }

def main():
    """Main execution"""
    print("\n🎬 NYC Filming Locations CSV Loader\n")
    print(f"📂 CSV file: {CSV_PATH}")
    print(f"🗄️  Database: {TIMESCALE_HOST}/{TIMESCALE_DB}\n")

    # Connect
    conn = connect_to_timescale()

    try:
        # Load data
        print("📥 Loading data...")
        stats = load_csv_to_database(conn)

        # Report results
        print("\n✅ Load complete!")
        print(f"   Productions: {stats['productions']}")
        print(f"   Locations:   {stats['locations']}")
        print(f"   Events:      {stats['events']}")
        if stats['skipped'] > 0:
            print(f"   Skipped:     {stats['skipped']}")

        print("\n🎯 Next steps:")
        print("   1. Run trend queries: scripts/trend_queries.sql")
        print("   2. Try CLI search: python scripts/search_locations.py production dexter")
        print("   3. Add embeddings: python scripts/generate_embeddings.py --openai-key XXX")

    except Exception as e:
        print(f"❌ Error during load: {e}")
        sys.exit(1)

    finally:
        conn.close()
        print("\n✓ Connection closed\n")

if __name__ == "__main__":
    main()
