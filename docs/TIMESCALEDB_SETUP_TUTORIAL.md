# NYC TV/Film Locations Database — Complete Setup Guide
## TimescaleDB + pgvector + Semantic Search + Trend Analysis

This guide walks you through building a production-ready filming locations database with TimescaleDB, enabling semantic search, and analyzing filming trends across NYC.

---

## 🤔 Why PostgreSQL/TimescaleDB + pgvector?

### The Problem You're Solving

You have:
- ✅ 100+ filming locations with addresses, descriptions, episodes
- ✅ Historical data (1933 King Kong → 2026 current productions)
- ✅ Time-series data (filming dates matter — when did they film?)
- ✅ Need for semantic search (find scenes by meaning, not keywords)
- ✅ Need for trend analysis (which neighborhoods film most?)

### Why NOT Other Solutions?

| Solution | Problem | Why It's Wrong |
|----------|---------|---|
| **Spreadsheet/CSV** | Can't scale; no search; slow analysis | Queries take minutes; impossible to add embeddings |
| **MongoDB** | Document store; not optimized for time-series | Slower queries for temporal analysis; no native vector support |
| **Elasticsearch** | Search-focused; overkill complexity | Designed for logs/text search, not relational data; expensive to run |
| **Firebase/DynamoDB** | NoSQL; designed for web apps | Limited query power; vector search requires separate service |
| **SQLite** | Single-file; limited concurrency | Can't handle semantic search; no hypertables for time-series |

### Why PostgreSQL/TimescaleDB + pgvector?

#### ✅ **1. PostgreSQL is the Swiss Army Knife**

PostgreSQL handles everything you need in ONE database:

```sql
-- Relational queries (productions → locations)
SELECT p.title, l.address 
FROM productions p 
JOIN locations l ON p.id = l.production_id;

-- Time-series queries (when was it filmed?)
SELECT DATE_TRUNC('month', filming_date) as month, COUNT(*)
FROM filming_events
GROUP BY DATE_TRUNC('month', filming_date);

-- Full-text search (find by description)
SELECT * FROM scenes 
WHERE description @@ plainto_tsquery('dark warehouse scene');

-- JSON queries (flexible metadata)
SELECT metadata->>'director' FROM productions;

-- Vector similarity (semantic search - find similar scenes)
SELECT * FROM scenes 
ORDER BY embedding <-> query_embedding 
LIMIT 10;
```

**Compare to:**
- MongoDB: Good at documents, bad at joins and time-series
- Elasticsearch: Good at search, bad at joins and analytics
- Firebase: Good for web apps, bad for complex queries

#### ✅ **2. TimescaleDB = PostgreSQL Optimized for Time-Series**

Your data IS time-series:
- When was X filmed?
- When did production Y happen?
- Which month had the most filming?

**TimescaleDB hypertables automatically:**
- Partition data by time (Jan 2024, Feb 2024, etc.)
- Make time-range queries 100-1000x faster
- Handle automatic data retention policies

```sql
-- This query on 1M+ events runs in milliseconds
SELECT neighborhood, COUNT(*) 
FROM filming_events 
WHERE time > NOW() - INTERVAL '30 days'
GROUP BY neighborhood;
```

**Without hypertables (regular PostgreSQL):** Could be slow on 100K+ rows  
**With hypertables:** Instant, even on millions of rows

#### ✅ **3. pgvector = Semantic Search Built-In**

You want: *"Find me scenes where a character is alone in a dark urban setting"*

**Without pgvector:**
- Store embeddings in separate service (Pinecone, Weaviate)
- Make HTTP calls (slow)
- Can't join with your location data
- Manage two systems = complexity

**With pgvector:**
- Store embeddings in same database as locations/productions
- Single SQL query joins everything
- No external API calls after embeddings are generated
- One system to manage

```sql
-- Single query: Find scenes + join with locations
SELECT p.title, l.address, fe.description,
       (fe.embedding <-> query_embedding) as similarity
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
WHERE (fe.embedding <-> query_embedding) < 0.3
ORDER BY similarity
LIMIT 10;
```

#### ✅ **4. Powerful Trend Analysis**

Because it's relational + time-series, you can ask complex questions:

```sql
-- Which neighborhoods were most filmed in, and by what genre?
SELECT l.neighborhood, p.category, COUNT(*) as count
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
WHERE EXTRACT(YEAR FROM fe.time) >= 2020
GROUP BY l.neighborhood, p.category
ORDER BY count DESC;

-- Which real-world locations appear in multiple shows?
SELECT l.address, COUNT(DISTINCT p.id) as show_count
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
GROUP BY l.address
HAVING COUNT(DISTINCT p.id) > 1
ORDER BY show_count DESC;

-- Temporal trends: Is filming accelerating in 2024-2026?
SELECT EXTRACT(YEAR FROM time) as year, COUNT(*) as filming_days
FROM filming_events
GROUP BY year
ORDER BY year DESC;
```

**These queries are:**
- ✅ One line of SQL
- ✅ Run in < 100ms (even with 1M+ rows)
- ✅ Impossible in MongoDB/Firebase without data export

#### ✅ **5. Cost-Effective**

- **Self-hosted PostgreSQL:** Free (open-source)
- **Tiger Cloud (managed):** $29-99/month for your data size
- **Elasticsearch:** $100-500+/month
- **Pinecone (vector DB):** $0.40-0.60 per million vectors
- **Firebase:** $0/month → $100s+ as you scale

#### ✅ **6. Extensibility**

PostgreSQL has extensions for almost anything:

```sql
-- PostGIS for geographic queries (find locations near Central Park)
SELECT * FROM locations 
WHERE ST_Distance(location, ST_GeomFromText('POINT(...)')) < 1000;

-- JSON support (store credits/metadata)
SELECT metadata->>'director' FROM productions;

-- Full-text search in descriptions
SELECT * FROM scenes 
WHERE description_tsv @@ to_tsquery('english', 'dark AND basement');

-- UUID generation, hashing, compression, etc.
```

### The TL;DR

| Requirement | PostgreSQL | TimescaleDB | pgvector | Result |
|---|---|---|---|---|
| Store locations + productions | ✅ | ✅ | — | **All in one DB** |
| Query by time (filming dates) | ✅ | **✅✅** | — | **10-1000x faster** |
| Semantic search (embeddings) | ✅ | ✅ | **✅✅** | **No external service** |
| Complex joins (location reuse) | **✅✅** | **✅✅** | ✅ | **Instant analytics** |
| Cost | 🟢 Free | 🟢 $29-99 | 🟢 Included | **Affordable** |
| Scalability | 🟡 OK | 🟢 Great | 🟢 Great | **Scales to millions** |

---

## 📋 What You'll Build

✅ **TimescaleDB database** with optimized schema for time-series filming data  
✅ **pgvector support** (installed but not required initially)  
✅ **CSV → Database loader** to import 100+ locations  
✅ **Trend queries** to find filming hotspots, reuse patterns, temporal trends  
✅ **Semantic search setup** (ready to add OpenAI embeddings)  

---

## 🔧 Prerequisites

- ✅ Tiger Cloud account with TimescaleDB instance
- ✅ Python 3.9+
- ✅ `psycopg2` or `psycopg` (PostgreSQL driver)
- ✅ CSV file: `/data/nyc_filming_locations.csv`
- ⏸️ OpenAI API key (optional for now, add later)

---

## Understanding Your Data Architecture: Three Layers

Before diving into setup, understand how your data flows:

```
┌──────────────────────────────────────────────────────────────┐
│ LAYER 1: CURATED DATA (Your CSV)                             │
│ ─────────────────────────────────────────────────────────────│
│ Source: Reddit, blogs, Dexter: Resurrection detailed blog    │
│ Content: Historical (1933-2010) + Current (2024-2026)        │
│ Status: Verified, hand-curated, rich descriptions            │
│ Examples: "King Kong at Empire State Building (1933)"        │
│           "Dexter S1E8 at Wig shop in Flatiron (2024)"       │
│ Records: 130+ locations, 100% verified                       │
└──────────────────────┬───────────────────────────────────────┘
                       │ load_csv_to_timescaledb.py
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ LAYER 2: TIMESCALEDB (Your Source of Truth)                  │
│ ─────────────────────────────────────────────────────────────│
│ Tables: productions, locations, filming_events (hypertable)  │
│ What it does:                                                 │
│   • Deduplicates productions & locations                     │
│   • Timestamps everything for trend analysis                 │
│   • Enables semantic search (via pgvector)                   │
│   • Allows complex joins across decades                      │
│ Queries: Find hotspots, trending neighborhoods, patterns     │
│ Storage: ~500KB-1MB for your dataset                         │
└──────────────────────┬───────────────────────────────────────┘
                       │ sync_nyc_permits.py (daily)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ LAYER 3: NYC OFFICIAL DATA (Authority Layer)                 │
│ ─────────────────────────────────────────────────────────────│
│ Source: NYC Open Data API (data.cityofnewyork.us)            │
│ Content: Official government film permits issued by Mayor     │
│ Status: Real-time, authoritative, official                   │
│ Examples: Event E-202400456: "Dexter" filming 2024-06-15     │
│           Event E-202400789: "Law & Order SVU" 2024-07-22    │
│ Records: 1000s+ per year (auto-synced)                       │
│ Purpose: Validate your data, enrich metadata, track permits  │
└──────────────────────────────────────────────────────────────┘

WHY THREE LAYERS?

✓ LAYER 1 (Curated): Rich descriptions for tourism + scouting
✓ LAYER 2 (TimescaleDB): Fast queries, trend analysis, semantic search
✓ LAYER 3 (Official): Verify data, track real filming, find new locations

EXAMPLE QUERY ACROSS ALL LAYERS:
  "Show me iconic locations (Layer 1) that are still filming (Layer 3)"
  
  SELECT p.title, l.location_name, l.address,
         COUNT(DISTINCT nop.event_id) as official_permits
  FROM filming_events fe
  JOIN productions p ON fe.production_id = p.id
  JOIN locations l ON fe.location_id = l.id
  LEFT JOIN nyc_official_permits nop ON l.address ~* nop.location
  WHERE p.year_aired < 2020  -- Historic filming
    AND nop.event_id IS NOT NULL  -- Still filming officially
  GROUP BY p.id, l.id
  ORDER BY official_permits DESC;
```

---

## Step 1: Set Up Tiger Cloud TimescaleDB

### 1.1 Create a TimescaleDB Instance

1. Log into **Tiger Cloud** console
2. Create a new **TimescaleDB service**
3. Choose:
   - **Plan**: Start with smallest (can resize later)
   - **Region**: US East (closest to NYC data)
   - **Extensions**: Enable `pgvector` (you'll see it available)

### 1.2 Get Connection Credentials

After creation, you'll see:
```
Host: xxx-xxx.tsdb.cloud.timescale.com
Port: 5432
Database: tsdb
Username: tsdbadmin
Password: [generated]
```

Save these! You'll need them for the Python loader.

### 1.3 Test Connection

```bash
# Install psycopg if needed
pip install psycopg

# Test connection (replace with your credentials)
psql -h xxx-xxx.tsdb.cloud.timescale.com -U tsdbadmin -d tsdb -c "SELECT version();"
```

---

## Step 2: Create Database Schema

### 2.1 Download Schema File

The schema is in: `/scripts/nyc_locations_schema.sql`

### 2.2 Apply Schema to Tiger Cloud

**Option A: Using psql**
```bash
psql -h your-host.tsdb.cloud.timescale.com \
     -U tsdbadmin \
     -d tsdb \
     -f scripts/nyc_locations_schema.sql
```

**Option B: Connect via Python and run**
```python
import psycopg

conn = psycopg.connect(
    "postgresql://tsdbadmin:password@host:5432/tsdb"
)
with open('scripts/nyc_locations_schema.sql', 'r') as f:
    conn.execute(f.read())
conn.commit()
conn.close()
```

### 2.3 What the Schema Creates

| Table | Purpose |
|-------|---------|
| `productions` | Show/film metadata (title, category, year, description) |
| `locations` | Real-world addresses (street, borough, neighborhood, lat/lon) |
| `filming_events` | **Hypertable** — time-series data of when/where/what was filmed |
| `scene_embeddings` | (Optional) Stores OpenAI embeddings for semantic search |

---

## Step 3: Load CSV Data into Database

### 3.1 Download Loader Script

The script is in: `/scripts/load_csv_to_timescaledb.py`

### 3.2 Configure Environment

Create `.env` file in project root:
```bash
TIMESCALE_HOST=your-host.tsdb.cloud.timescale.com
TIMESCALE_PORT=5432
TIMESCALE_DB=tsdb
TIMESCALE_USER=tsdbadmin
TIMESCALE_PASSWORD=your-password
```

Or set as environment variables:
```bash
export TIMESCALE_HOST="xxx.tsdb.cloud.timescale.com"
export TIMESCALE_USER="tsdbadmin"
export TIMESCALE_PASSWORD="xxx"
```

### 3.3 Run the Loader

```bash
python scripts/load_csv_to_timescaledb.py
```

**What it does:**
1. Reads `/data/nyc_filming_locations.csv`
2. Parses productions and locations
3. Creates filming events with timestamps
4. Inserts into TimescaleDB
5. Creates indexes for performance

**Expected output:**
```
Connected to TimescaleDB
Loading productions... ✓ 45 productions
Loading locations... ✓ 103 locations  
Loading filming events... ✓ 127 events
Creating indexes... ✓
Done! Database ready for queries.
```

---

## Step 4: Run Trend Queries

### 4.1 Download Queries File

Queries are in: `/scripts/trend_queries.sql`

### 4.2 Connect and Run Queries

```bash
psql -h your-host.tsdb.cloud.timescale.com \
     -U tsdbadmin \
     -d tsdb
```

Then run queries below:

### **Query 1: Most Filmed Neighborhoods**

```sql
SELECT 
  l.neighborhood,
  COUNT(*) as filming_events,
  COUNT(DISTINCT p.id) as unique_productions,
  STRING_AGG(DISTINCT p.title, ', ') as productions
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
GROUP BY l.neighborhood
ORDER BY filming_events DESC
LIMIT 10;
```

**Expected output:**
```
        neighborhood        | filming_events | unique_productions |           productions
----------------------------+----------------+--------------------+-----------------------------
 Midtown, Manhattan         |     18         |      8             | Dexter: Resurrection, Times Square...
 Tribeca, Manhattan         |     12         |      5             | Dexter: Resurrection, FBI...
 Upper West Side, Manhattan |     10         |      4             | Ghostbusters, Dexter: Resurrection...
```

### **Query 2: Location Reuse (Places in Multiple Productions)**

```sql
SELECT 
  l.location_name,
  l.address,
  l.borough,
  COUNT(DISTINCT p.id) as production_count,
  STRING_AGG(DISTINCT p.title, ' | ') as shows_filmed_here
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
GROUP BY l.location_name, l.address, l.borough
HAVING COUNT(DISTINCT p.id) > 1
ORDER BY production_count DESC;
```

**Why this matters:** Shows which locations are "film-friendly" reused by productions.

### **Query 3: Borough Distribution**

```sql
SELECT 
  l.borough,
  COUNT(*) as filming_events,
  COUNT(DISTINCT l.id) as unique_locations,
  COUNT(DISTINCT p.id) as unique_productions
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
GROUP BY l.borough
ORDER BY filming_events DESC;
```

### **Query 4: Temporal Trends (When Do Productions Film?)**

```sql
SELECT 
  DATE_TRUNC('month', fe.time) as month,
  COUNT(*) as filming_days,
  COUNT(DISTINCT p.id) as active_productions,
  STRING_AGG(DISTINCT p.title, ', ') as productions
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
GROUP BY DATE_TRUNC('month', fe.time)
ORDER BY month DESC;
```

### **Query 5: Category Analysis (Film vs TV)**

```sql
SELECT 
  p.category,
  COUNT(*) as filming_count,
  COUNT(DISTINCT l.id) as unique_locations,
  AVG(extract(year from fe.time)) as avg_year
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
GROUP BY p.category
ORDER BY filming_count DESC;
```

### **Query 6: Find "Filming Hotspots" (Intersections)**

```sql
-- Shows which street intersections get the most filming
SELECT 
  l.address,
  l.neighborhood,
  COUNT(DISTINCT p.id) as productions_count,
  STRING_AGG(DISTINCT p.title, ' | ') as titles
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
WHERE l.address IS NOT NULL
GROUP BY l.address, l.neighborhood
ORDER BY productions_count DESC
LIMIT 15;
```

---

## Step 5: Sync NYC Official Permits (Authority Layer)

### 5.1 What Are Official Permits?

The NYC Mayor's Office issues permits for all film productions. These are **public records** available via API:

- **Official data source:** NYC Open Data portal
- **Data quality:** Government-maintained, real-time
- **Coverage:** All productions with permits (99%+ of major films)
- **Fields:** Location, dates, company name, production type

### 5.2 Add NYC Permits Table to Schema

The permits table is already in your schema (see `nyc_locations_schema.sql`):

```sql
CREATE TABLE IF NOT EXISTS nyc_official_permits (
  id SERIAL PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  location TEXT,
  production_company TEXT,
  event_type TEXT,
  start_date DATE,
  end_date DATE,
  borough TEXT,
  latitude FLOAT,
  longitude FLOAT,
  permit_json JSONB
);
```

### 5.3 Run the Permit Sync Script

First, install required package:
```bash
pip install requests
```

Then sync permits:
```bash
python scripts/sync_nyc_permits.py
```

**Options:**
```bash
# Fetch permits from last 30 days (default)
python scripts/sync_nyc_permits.py

# Fetch ALL permits ever issued
python scripts/sync_nyc_permits.py --full

# Fetch from last 90 days
python scripts/sync_nyc_permits.py --days 90

# Dry run (see what would happen)
python scripts/sync_nyc_permits.py --dry-run

# Sync AND verify against your curated data
python scripts/sync_nyc_permits.py --verify
```

### 5.4 What the Script Does

```
📡 Fetches from NYC Open Data API
   ↓
📊 Parses ~1000s permits
   ↓
💾 Stores in nyc_official_permits table
   ↓
🔍 Optionally validates against your curated locations
   ↓
✅ Shows summary: permits by borough, type, recent activity
```

**Expected output:**
```
✅ Fetched 847 permits

💾 Storing permits...
   Inserted: 812
   Updated:  35
   Skipped:  0

📊 NYC Official Permits Summary
=====================================
Total permits: 847

By Borough:
  Manhattan: 412
  Brooklyn: 251
  Queens: 123
  Bronx: 61

By Type:
  TV Series: 324
  Feature Film: 213
  Commercial: 210
  Other: 100

Recent Filming (Last 10 days):
  2026-09-04: 12 productions
  2026-09-03: 8 productions
```

### 5.5 Schedule Daily Syncs (Cron)

Keep your data fresh by syncing daily:

```bash
# Edit your crontab
crontab -e

# Add this line (runs every day at 3 AM)
0 3 * * * cd /path/to/nyc-tv && python scripts/sync_nyc_permits.py >> /tmp/nyc_permits_sync.log 2>&1
```

### 5.6 Query: Validate Your Data Against Official Permits

```sql
-- Which of your curated locations have official permits?
SELECT 
  p.title,
  l.location_name,
  l.address,
  COUNT(DISTINCT nop.event_id) as official_permits,
  MIN(nop.start_date) as first_permit,
  MAX(nop.end_date) as last_permit
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
LEFT JOIN nyc_official_permits nop 
  ON (LOWER(l.address) LIKE LOWER(nop.location)
      OR LOWER(nop.production_company) LIKE LOWER(p.title) || '%')
GROUP BY p.id, l.id, p.title, l.location_name, l.address
HAVING COUNT(DISTINCT nop.event_id) > 0
ORDER BY COUNT(DISTINCT nop.event_id) DESC;
```

**Result:** Shows which of your locations are officially permitted ✅

### 5.7 Query: Find New Productions from Official Permits

Discover productions BEFORE they appear in blogs:

```sql
-- Find official permits that aren't in your curated data yet
SELECT 
  nop.event_id,
  nop.production_company,
  nop.event_type,
  nop.location,
  nop.borough,
  nop.start_date,
  nop.end_date,
  CASE 
    WHEN p.id IS NOT NULL THEN 'IN DATABASE'
    ELSE 'NEW - ADD TO CURATED DATA'
  END as status
FROM nyc_official_permits nop
LEFT JOIN productions p 
  ON LOWER(p.title) LIKE LOWER(nop.production_company) || '%'
WHERE nop.start_date >= CURRENT_DATE - INTERVAL '60 days'
  AND p.id IS NULL  -- Only permits not in your database
ORDER BY nop.start_date DESC
LIMIT 20;
```

**Use case:** This shows you new productions filming in NYC that you can research and add to your curated dataset.

### 5.8 Query: Compare Official vs Curated

See how well your curated data matches official records:

```sql
-- Coverage analysis
SELECT 
  'Official Permits' as source,
  COUNT(DISTINCT event_id) as unique_records,
  COUNT(DISTINCT borough) as boroughs_covered,
  COUNT(DISTINCT production_company) as companies
FROM nyc_official_permits

UNION ALL

SELECT 
  'Curated Data' as source,
  COUNT(DISTINCT p.id) as unique_records,
  COUNT(DISTINCT l.borough) as boroughs_covered,
  COUNT(DISTINCT p.title) as companies
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id;
```

**Interpretation:**
- If curated < official: You're missing locations to research
- If curated > official: You have historical data (1933-2010) that predates official permits
- Strong overlap = Your data is credible!

---

## Step 6: Prepare for Semantic Search (Optional, Do Later)

### 5.1 What Are Embeddings?

Embeddings convert text descriptions into numerical vectors. This lets you search by **meaning** instead of keywords.

**Example:**
- Search: "dark basement where character is tortured"
- Finds: Dexter S1E8 "Wig shop kill room scene" (even without exact keywords)

### 5.2 How to Add OpenAI Embeddings Later

When you're ready, run this script:

```bash
python scripts/generate_embeddings.py --openai-key your-api-key
```

This will:
1. Read all scene descriptions from database
2. Call OpenAI API (small cost: ~$0.02-0.05)
3. Store embeddings in `scene_embeddings` table
4. Create vector index for fast search

### 5.3 Semantic Search Query (After Embeddings Added)

```sql
-- Find scenes matching a semantic query
WITH query_embedding AS (
  SELECT embedding_from_openai('diner scene with dramatic conversation') as vec
)
SELECT 
  p.title,
  l.address,
  fe.scene_description,
  fe.season_episode,
  (se.embedding <-> query_embedding.vec) as distance
FROM scene_embeddings se
JOIN filming_events fe ON se.event_id = fe.id
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
CROSS JOIN query_embedding
WHERE (se.embedding <-> query_embedding.vec) < 0.3  -- Similarity threshold
ORDER BY distance
LIMIT 10;
```

---

## Step 6: Build a Search Interface (CLI or API)

### 6.1 Simple Python CLI

Create `scripts/search_locations.py`:

```python
#!/usr/bin/env python3
import psycopg
import sys
from pathlib import Path
import os

# Connection
conn = psycopg.connect(
    f"postgresql://{os.getenv('TIMESCALE_USER')}:{os.getenv('TIMESCALE_PASSWORD')}@"
    f"{os.getenv('TIMESCALE_HOST')}:{os.getenv('TIMESCALE_PORT')}/{os.getenv('TIMESCALE_DB')}"
)

def search_by_neighborhood(neighborhood):
    """Find all scenes filmed in a neighborhood"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.title, l.address, fe.scene_description, fe.season_episode
            FROM filming_events fe
            JOIN locations l ON fe.location_id = l.id
            JOIN productions p ON fe.production_id = p.id
            WHERE l.neighborhood ILIKE %s
            ORDER BY p.title
        """, (f"%{neighborhood}%",))
        return cur.fetchall()

def search_by_production(title):
    """Find all locations used in a production"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT l.address, l.neighborhood, fe.scene_description, fe.season_episode
            FROM filming_events fe
            JOIN locations l ON fe.location_id = l.id
            JOIN productions p ON fe.production_id = p.id
            WHERE p.title ILIKE %s
            ORDER BY fe.season_episode
        """, (f"%{title}%",))
        return cur.fetchall()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python search_locations.py [neighborhood|production] [query]")
        sys.exit(1)
    
    search_type = sys.argv[1]
    query = " ".join(sys.argv[2:])
    
    if search_type == "neighborhood":
        results = search_by_neighborhood(query)
    elif search_type == "production":
        results = search_by_production(query)
    
    for row in results:
        print(f"📍 {row[0]} ({row[1]})")
        print(f"   {row[2]}")
        if row[3]:
            print(f"   {row[3]}")
        print()
```

**Usage:**
```bash
# Find all Dexter scenes
python scripts/search_locations.py production dexter

# Find all scenes in Times Square
python scripts/search_locations.py neighborhood "times square"
```

---

## 📊 Database Optimization Tips

### Indexes Created
```sql
-- Speed up location searches
CREATE INDEX idx_locations_borough ON locations(borough);
CREATE INDEX idx_locations_neighborhood ON locations(neighborhood);

-- Speed up time-series queries (automatic in hypertable)
-- Speed up production lookups
CREATE INDEX idx_filming_events_production ON filming_events(production_id);
```

### Query Performance
- Hypertable automatically chunks data by time for fast range queries
- Vector index (when added) uses IVFFlat for semantic search
- Borough/neighborhood indexes for location discovery

---

## 🚀 Next Steps

1. ✅ **Start here** — Set up Tiger Cloud instance
2. ✅ **Apply schema** — Create tables and indexes
3. ✅ **Load CSV** — Import 100+ curated locations
4. ✅ **Sync official permits** — Import NYC government data
5. ✅ **Run trend queries** — Discover patterns in filming
6. ⏭️ **Verify data** — Cross-reference curated vs official
7. ⏭️ **Add OpenAI embeddings** — Enable semantic search
8. ⏭️ **Build API** — Expose as REST endpoints
9. ⏭️ **Create frontend** — Web interface for searching

---

## 🔍 Troubleshooting

### Connection Issues
```bash
# Test connection from command line
psql -h your-host.tsdb.cloud.timescale.com \
     -U tsdbadmin \
     -d tsdb \
     -c "SELECT 1"
```

### Schema Already Exists
If you get "table already exists" error, drop and recreate:
```sql
DROP HYPERTABLE IF EXISTS filming_events CASCADE;
DROP TABLE IF EXISTS productions CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
-- Then re-run schema file
```

### CSV Load Issues
Check CSV format is correct:
```bash
head -5 data/nyc_filming_locations.csv
```

Should start with:
```
Title,Address,Borough/Neighborhood,Description,Category,Season/Episode,Year,Source
```

---

## 📚 Files Reference

| File | Purpose |
|------|---------|
| `/docs/TIMESCALEDB_SETUP_TUTORIAL.md` | This guide |
| `/scripts/nyc_locations_schema.sql` | Database schema + tables |
| `/scripts/load_csv_to_timescaledb.py` | Load curated CSV data |
| `/scripts/sync_nyc_permits.py` | **NEW** Sync official NYC permits |
| `/scripts/trend_queries.sql` | Analysis queries |
| `/scripts/search_locations.py` | CLI search tool |
| `/scripts/generate_embeddings.py` | OpenAI embeddings (optional) |
| `/scripts/README.md` | Quick start guide |
| `/data/nyc_filming_locations.csv` | Your curated data |

---

## 💡 Ideas for Extensions

- **Map visualization** — Plot locations on Folium/Mapbox
- **Time-series analysis** — Graph filming activity over time
- **Recommendation engine** — "If you liked this location, you'll like..."
- **Location scouting tool** — Search by scene requirements ("diner", "rooftop", "dark alley")
- **Community contributions** — Users add new locations + photos
- **Export reports** — Generate PDF guides for each neighborhood

---

**Happy exploring! 🎬🗽**
