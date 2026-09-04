#!/usr/bin/env python3
"""
Sync NYC Film Permits from NYC Open Data API

This script:
1. Fetches official film permits from NYC Open Data
2. Stores in database for validation + enrichment
3. Can be run daily via cron for live updates
4. Matches permits against your curated locations

NYC Open Data: https://data.cityofnewyork.us/resource/tg4x-b46v.json

Usage:
    python scripts/sync_nyc_permits.py [--full] [--days 30]

Options:
    --full      Fetch all permits (not just last N days)
    --days N    Fetch permits from last N days (default 30)
    --dry-run   Show what would happen without saving

Environment variables:
    TIMESCALE_HOST, TIMESCALE_USER, TIMESCALE_PASSWORD, TIMESCALE_DB
"""

import os
import sys
import json
import argparse
import requests
import psycopg
from datetime import datetime, timedelta
from typing import List, Dict
from urllib.parse import urlencode

# Configuration
TIMESCALE_HOST = os.getenv("TIMESCALE_HOST")
TIMESCALE_PORT = os.getenv("TIMESCALE_PORT", "5432")
TIMESCALE_USER = os.getenv("TIMESCALE_USER")
TIMESCALE_PASSWORD = os.getenv("TIMESCALE_PASSWORD")
TIMESCALE_DB = os.getenv("TIMESCALE_DB", "tsdb")

# NYC Open Data API (Socrata)
NYC_DATA_API = "https://data.cityofnewyork.us/resource/tg4x-b46v.json"

def connect():
    """Create DB connection"""
    try:
        return psycopg.connect(
            f"postgresql://{TIMESCALE_USER}:{TIMESCALE_PASSWORD}@"
            f"{TIMESCALE_HOST}:{TIMESCALE_PORT}/{TIMESCALE_DB}"
        )
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n⚠️  Make sure environment variables are set:")
        print("   TIMESCALE_HOST, TIMESCALE_USER, TIMESCALE_PASSWORD")
        sys.exit(1)

def fetch_permits(days: int = 30, limit: int = 50000) -> List[Dict]:
    """
    Fetch film permits from NYC Open Data API

    Args:
        days: Number of days back to fetch (0 = all)
        limit: Max records to fetch

    Returns:
        List of permit records
    """

    # Build query
    query_parts = []

    if days > 0:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        # NYC Open Data uses 'date_filed_extract' for filtering
        query_parts.append(f"date_filed_extract >= '{start_date}'")

    # Construct SoQL WHERE clause
    where_clause = " AND ".join(query_parts) if query_parts else None

    params = {"$limit": limit}
    if where_clause:
        params["$where"] = where_clause

    print(f"📡 Fetching permits from NYC Open Data API...")
    print(f"   Query: {NYC_DATA_API}")
    if where_clause:
        print(f"   Filter: {where_clause}")

    try:
        response = requests.get(NYC_DATA_API, params=params, timeout=30)
        response.raise_for_status()
        permits = response.json()
        print(f"✅ Fetched {len(permits)} permits\n")
        return permits
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return []

def parse_permit(permit: Dict) -> Dict:
    """
    Parse permit record from NYC Open Data format

    Maps NYC Open Data columns to our schema
    """
    return {
        'event_id': permit.get('event_id', '').strip(),
        'location': permit.get('location', '').strip(),
        'production_company': permit.get('production_company', '').strip(),
        'event_type': permit.get('event_type', '').strip(),
        'start_date': permit.get('start_date'),
        'end_date': permit.get('end_date'),
        'borough': permit.get('borough', '').strip(),
        'latitude': _parse_float(permit.get('latitude')),
        'longitude': _parse_float(permit.get('longitude')),
        'permit_json': json.dumps(permit)
    }

def _parse_float(value):
    """Safely parse float values"""
    try:
        return float(value) if value else None
    except (ValueError, TypeError):
        return None

def store_permits(conn, permits: List[Dict], dry_run: bool = False) -> Dict:
    """
    Store permits in database

    Returns stats about insert/update/skip
    """
    stats = {
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }

    if not permits:
        return stats

    with conn.cursor() as cur:
        for permit in permits:
            try:
                parsed = parse_permit(permit)

                # Skip if missing critical fields
                if not parsed['event_id'] or not parsed['location']:
                    stats['skipped'] += 1
                    continue

                if dry_run:
                    print(f"   [DRY RUN] Would insert: {parsed['event_id']} - {parsed['production_company']}")
                    stats['inserted'] += 1
                    continue

                # Insert or update
                cur.execute("""
                    INSERT INTO nyc_official_permits
                    (event_id, location, production_company, event_type,
                     start_date, end_date, borough, latitude, longitude, permit_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO UPDATE SET
                        production_company = EXCLUDED.production_company,
                        location = EXCLUDED.location,
                        event_type = EXCLUDED.event_type,
                        start_date = EXCLUDED.start_date,
                        end_date = EXCLUDED.end_date,
                        borough = EXCLUDED.borough,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude,
                        permit_json = EXCLUDED.permit_json,
                        synced_at = NOW()
                """, (
                    parsed['event_id'],
                    parsed['location'],
                    parsed['production_company'],
                    parsed['event_type'],
                    parsed['start_date'],
                    parsed['end_date'],
                    parsed['borough'],
                    parsed['latitude'],
                    parsed['longitude'],
                    parsed['permit_json']
                ))

                stats['inserted'] += 1

            except psycopg.IntegrityError:
                stats['updated'] += 1
                conn.rollback()
            except Exception as e:
                print(f"⚠️  Error storing permit {permit.get('event_id')}: {e}")
                stats['errors'] += 1
                conn.rollback()

    if not dry_run:
        conn.commit()

    return stats

def validate_against_curated(conn) -> Dict:
    """
    Compare official permits against your curated locations

    Returns matches, mismatches, unverified
    """
    with conn.cursor() as cur:
        # Find curated locations that match official permits
        cur.execute("""
            SELECT
              p.title,
              l.address,
              COUNT(DISTINCT nop.event_id) as matching_permits,
              STRING_AGG(DISTINCT nop.production_company, ' | ') as companies
            FROM filming_events fe
            JOIN productions p ON fe.production_id = p.id
            JOIN locations l ON fe.location_id = l.id
            LEFT JOIN nyc_official_permits nop
              ON (l.address ~* nop.location
                OR nop.production_company ILIKE '%' || p.title || '%')
            GROUP BY p.id, p.title, l.address
            HAVING COUNT(DISTINCT nop.event_id) > 0
            ORDER BY matching_permits DESC
            LIMIT 20
        """)

        matches = cur.fetchall()
        return {
            'verified_locations': len(matches),
            'matches': matches
        }

def show_summary(conn):
    """Display summary stats about permits in database"""
    with conn.cursor() as cur:
        # Total permits
        cur.execute("SELECT COUNT(*) FROM nyc_official_permits")
        total = cur.fetchone()[0]

        # By borough
        cur.execute("""
            SELECT borough, COUNT(*) as count
            FROM nyc_official_permits
            WHERE borough IS NOT NULL
            GROUP BY borough
            ORDER BY count DESC
        """)
        by_borough = cur.fetchall()

        # By type
        cur.execute("""
            SELECT event_type, COUNT(*) as count
            FROM nyc_official_permits
            WHERE event_type IS NOT NULL
            GROUP BY event_type
            ORDER BY count DESC
        """)
        by_type = cur.fetchall()

        # Recent activity
        cur.execute("""
            SELECT DATE(start_date) as date, COUNT(*) as filming_days
            FROM nyc_official_permits
            WHERE start_date IS NOT NULL
            GROUP BY DATE(start_date)
            ORDER BY date DESC
            LIMIT 10
        """)
        recent = cur.fetchall()

    print("📊 NYC Official Permits Summary")
    print("=" * 50)
    print(f"Total permits: {total}\n")

    print("By Borough:")
    for borough, count in by_borough:
        print(f"  {borough}: {count}")

    print("\nBy Type:")
    for event_type, count in by_type:
        print(f"  {event_type}: {count}")

    print("\nRecent Filming (Last 10 days):")
    for date, count in recent:
        print(f"  {date}: {count} productions")

def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description="Sync NYC film permits from NYC Open Data API"
    )
    parser.add_argument("--full", action="store_true",
                       help="Fetch all permits (not just recent)")
    parser.add_argument("--days", type=int, default=30,
                       help="Days back to fetch (default 30)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would happen without saving")
    parser.add_argument("--verify", action="store_true",
                       help="Show matches between permits and curated data")
    args = parser.parse_args()

    print("\n🎬 NYC Film Permits Sync\n")

    # Fetch permits
    days = 0 if args.full else args.days
    permits = fetch_permits(days=days)

    if not permits:
        print("❌ No permits fetched")
        sys.exit(1)

    # Connect to database
    conn = connect()
    print("✅ Connected to TimescaleDB\n")

    try:
        # Store permits
        print("💾 Storing permits...")
        stats = store_permits(conn, permits, dry_run=args.dry_run)

        print(f"   Inserted: {stats['inserted']}")
        print(f"   Updated:  {stats['updated']}")
        print(f"   Skipped:  {stats['skipped']}")
        if stats['errors'] > 0:
            print(f"   Errors:   {stats['errors']}")

        # Show summary
        if not args.dry_run:
            print()
            show_summary(conn)

        # Validate against curated data
        if args.verify:
            print("\n🔍 Verification Against Curated Data")
            print("=" * 50)
            validation = validate_against_curated(conn)
            print(f"Verified locations: {validation['verified_locations']}\n")

            for title, address, permits_count, companies in validation['matches']:
                print(f"✅ {title}")
                print(f"   Address: {address}")
                print(f"   Permits: {permits_count}")
                print(f"   Companies: {companies}\n")

        print("✅ Sync complete!")
        if args.dry_run:
            print("   (This was a DRY RUN - no data was saved)")

        print("\n💡 Next steps:")
        print("   - Run queries: scripts/trend_queries.sql")
        print("   - Verify data: python sync_nyc_permits.py --verify")
        print("   - Schedule daily: crontab -e")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    finally:
        conn.close()
        print()

if __name__ == "__main__":
    main()
