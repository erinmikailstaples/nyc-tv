#!/usr/bin/env python3
"""
CLI Tool: Search NYC Filming Locations Database

Usage Examples:
    python search_locations.py production "Dexter"
    python search_locations.py neighborhood "Times Square"
    python search_locations.py location "Bethesda Fountain"
    python search_locations.py borough "Manhattan"
    python search_locations.py year 2024
    python search_locations.py category "TV"
"""

import os
import sys
import psycopg
from tabulate import tabulate
from datetime import datetime

# Connection config
TIMESCALE_HOST = os.getenv("TIMESCALE_HOST")
TIMESCALE_PORT = os.getenv("TIMESCALE_PORT", "5432")
TIMESCALE_USER = os.getenv("TIMESCALE_USER")
TIMESCALE_PASSWORD = os.getenv("TIMESCALE_PASSWORD")
TIMESCALE_DB = os.getenv("TIMESCALE_DB", "tsdb")

def connect():
    """Create DB connection"""
    try:
        return psycopg.connect(
            f"postgresql://{TIMESCALE_USER}:{TIMESCALE_PASSWORD}@"
            f"{TIMESCALE_HOST}:{TIMESCALE_PORT}/{TIMESCALE_DB}"
        )
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n⚠️  Make sure TimescaleDB is running and environment variables are set:")
        print("   TIMESCALE_HOST, TIMESCALE_USER, TIMESCALE_PASSWORD")
        sys.exit(1)

def search_by_production(query, conn):
    """Find all locations used in a production"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
              p.title,
              p.category,
              p.year_aired,
              l.location_name,
              l.address,
              l.neighborhood,
              fe.season_episode,
              fe.scene_description
            FROM filming_events fe
            JOIN productions p ON fe.production_id = p.id
            JOIN locations l ON fe.location_id = l.id
            WHERE p.title ILIKE %s
            ORDER BY p.title, fe.season_episode
        """, (f"%{query}%",))

        results = cur.fetchall()
        if not results:
            print(f"❌ No productions found matching: {query}")
            return

        production_title = results[0][0]
        print(f"\n🎬 {production_title}")
        print(f"   {'─' * 70}\n")

        rows = []
        for title, category, year, loc_name, address, neighborhood, ep, desc in results:
            rows.append([
                ep or "—",
                loc_name or address,
                neighborhood,
                desc[:50] + "..." if desc and len(desc) > 50 else desc or "—"
            ])

        print(tabulate(rows, headers=["Episode", "Location", "Neighborhood", "Description"],
                      tablefmt="grid", maxcolwidths=[8, 25, 20, 45]))
        print(f"\n✅ {len(results)} locations found\n")

def search_by_neighborhood(query, conn):
    """Find all scenes filmed in a neighborhood"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
              l.neighborhood,
              l.location_name,
              l.address,
              p.title,
              p.category,
              fe.season_episode,
              fe.scene_description
            FROM filming_events fe
            JOIN locations l ON fe.location_id = l.id
            JOIN productions p ON fe.production_id = p.id
            WHERE l.neighborhood ILIKE %s
            ORDER BY l.neighborhood, p.title
        """, (f"%{query}%",))

        results = cur.fetchall()
        if not results:
            print(f"❌ No locations found in: {query}")
            return

        neighborhood = results[0][0]
        print(f"\n📍 {neighborhood}")
        print(f"   {'─' * 70}\n")

        rows = []
        for neighborhood, loc_name, address, title, category, ep, desc in results:
            rows.append([
                title,
                category,
                ep or "—",
                loc_name or address,
                desc[:40] + "..." if desc and len(desc) > 40 else desc or "—"
            ])

        print(tabulate(rows, headers=["Production", "Type", "Ep", "Location", "Description"],
                      tablefmt="grid", maxcolwidths=[20, 10, 6, 20, 40]))
        print(f"\n✅ {len(results)} scenes found\n")

def search_by_location(query, conn):
    """Find all productions filmed at a specific location"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
              l.location_name,
              l.address,
              l.neighborhood,
              l.borough,
              p.title,
              p.category,
              p.year_aired,
              fe.scene_description
            FROM filming_events fe
            JOIN locations l ON fe.location_id = l.id
            JOIN productions p ON fe.production_id = p.id
            WHERE l.location_name ILIKE %s OR l.address ILIKE %s
            ORDER BY l.address, p.title
        """, (f"%{query}%", f"%{query}%"))

        results = cur.fetchall()
        if not results:
            print(f"❌ No locations found for: {query}")
            return

        location = f"{results[0][1]}, {results[0][2]}"
        print(f"\n🏢 {results[0][0] or location}")
        print(f"   Address: {results[0][1]}")
        print(f"   Borough: {results[0][3]}")
        print(f"   {'─' * 70}\n")

        rows = []
        for loc_name, address, neighborhood, borough, title, category, year, desc in results:
            rows.append([
                title,
                category,
                year or "—",
                desc[:50] + "..." if desc and len(desc) > 50 else desc or "—"
            ])

        print(tabulate(rows, headers=["Production", "Type", "Year", "Scene Description"],
                      tablefmt="grid", maxcolwidths=[25, 10, 6, 55]))
        print(f"\n✅ Used in {len(results)} production(s)\n")

def search_by_borough(query, conn):
    """Find filming activity in a borough"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
              l.borough,
              l.neighborhood,
              COUNT(*) as filming_events,
              COUNT(DISTINCT p.id) as productions
            FROM filming_events fe
            JOIN locations l ON fe.location_id = l.id
            JOIN productions p ON fe.production_id = p.id
            WHERE l.borough ILIKE %s
            GROUP BY l.borough, l.neighborhood
            ORDER BY filming_events DESC
        """, (f"%{query}%",))

        results = cur.fetchall()
        if not results:
            print(f"❌ No filming found in: {query}")
            return

        borough = results[0][0]
        print(f"\n🗺️  {borough}")
        print(f"   {'─' * 70}\n")

        rows = []
        total_events = 0
        total_productions = 0
        for b, neighborhood, events, prods in results:
            rows.append([neighborhood, events, prods])
            total_events += events
            total_productions += prods

        print(tabulate(rows, headers=["Neighborhood", "Filming Events", "Productions"],
                      tablefmt="grid"))
        print(f"\n✅ {total_events} total filming events in {total_productions} productions\n")

def search_by_year(query, conn):
    """Find productions filmed in a year"""
    try:
        year = int(query)
    except:
        print(f"❌ Invalid year: {query}")
        return

    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT
              p.title,
              p.category,
              p.year_aired,
              COUNT(DISTINCT l.id) as locations,
              STRING_AGG(DISTINCT l.neighborhood, ', ') as neighborhoods
            FROM filming_events fe
            JOIN productions p ON fe.production_id = p.id
            JOIN locations l ON fe.location_id = l.id
            WHERE EXTRACT(YEAR FROM fe.time) = %s
            GROUP BY p.id, p.title, p.category, p.year_aired
            ORDER BY p.title
        """, (year,))

        results = cur.fetchall()
        if not results:
            print(f"❌ No filming found in year: {year}")
            return

        print(f"\n📅 Filming Activity in {year}")
        print(f"   {'─' * 70}\n")

        rows = []
        for title, category, year_aired, locations, neighborhoods in results:
            rows.append([title, category, locations, neighborhoods])

        print(tabulate(rows, headers=["Production", "Type", "Locations", "Neighborhoods"],
                      tablefmt="grid", maxcolwidths=[30, 12, 10, 50]))
        print(f"\n✅ {len(results)} productions filmed in {year}\n")

def search_by_category(query, conn):
    """Find productions by category"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
              p.category,
              COUNT(DISTINCT p.id) as productions,
              COUNT(DISTINCT l.id) as locations,
              COUNT(*) as total_events,
              STRING_AGG(DISTINCT p.title, ', ') as example_titles
            FROM filming_events fe
            JOIN productions p ON fe.production_id = p.id
            JOIN locations l ON fe.location_id = l.id
            WHERE p.category ILIKE %s
            GROUP BY p.category
        """, (f"%{query}%",))

        results = cur.fetchall()
        if not results:
            print(f"❌ No productions found in category: {query}")
            return

        category = results[0][0]
        print(f"\n🎬 {category} Productions")
        print(f"   {'─' * 70}\n")

        rows = []
        for cat, prods, locs, events, titles in results:
            rows.append([prods, locs, events, titles[:60] + "..." if len(titles) > 60 else titles])

        print(tabulate(rows, headers=["Productions", "Locations", "Events", "Examples"],
                      tablefmt="grid", maxcolwidths=[12, 10, 8, 60]))
        print()

def main():
    """Main CLI"""
    if len(sys.argv) < 3:
        print("🎬 NYC Filming Locations Search Tool\n")
        print("Usage:")
        print("  python search_locations.py [search_type] [query]\n")
        print("Search Types:")
        print("  production [name]      - Find all locations used in a show/film")
        print("  neighborhood [name]    - Find all scenes filmed in a neighborhood")
        print("  location [name]        - Find all productions filmed at a location")
        print("  borough [name]         - Find filming activity in a borough")
        print("  year [YYYY]            - Find productions filmed in a year")
        print("  category [type]        - Find productions by category (Film, TV, etc.)\n")
        print("Examples:")
        print("  python search_locations.py production 'Dexter'")
        print("  python search_locations.py neighborhood 'Times Square'")
        print("  python search_locations.py location 'Bethesda Fountain'")
        print("  python search_locations.py borough Manhattan")
        print("  python search_locations.py year 2024")
        print("  python search_locations.py category TV\n")
        sys.exit(1)

    search_type = sys.argv[1].lower()
    query = " ".join(sys.argv[2:])

    conn = connect()

    try:
        if search_type == "production":
            search_by_production(query, conn)
        elif search_type == "neighborhood":
            search_by_neighborhood(query, conn)
        elif search_type == "location":
            search_by_location(query, conn)
        elif search_type == "borough":
            search_by_borough(query, conn)
        elif search_type == "year":
            search_by_year(query, conn)
        elif search_type == "category":
            search_by_category(query, conn)
        else:
            print(f"❌ Unknown search type: {search_type}")
            print("   Use: production, neighborhood, location, borough, year, or category")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
