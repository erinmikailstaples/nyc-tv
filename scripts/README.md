# NYC Filming Locations Database Scripts

Complete toolkit for building a production-ready filming locations database with TimescaleDB + pgvector.

---

## 📚 Start Here

**Read first:** [`docs/TIMESCALEDB_SETUP_TUTORIAL.md`](../docs/TIMESCALEDB_SETUP_TUTORIAL.md)

This tutorial explains:
- Why PostgreSQL/TimescaleDB + pgvector is the right choice
- Step-by-step setup guide
- How to load data
- How to run queries and find trends
- How to add semantic search

---

## 🔧 Scripts Overview

### 1. **nyc_locations_schema.sql**
Database schema for TimescaleDB

**What it does:**
- Creates `productions` table (shows/films metadata)
- Creates `locations` table (NYC addresses)
- Creates `filming_events` hypertable (time-series filming data)
- Sets up `scene_embeddings` table for semantic search
- Creates indexes and useful views

**Run it:**
```bash
psql -h your-host -U user -d tsdb -f scripts/nyc_locations_schema.sql
```

**Or via Python:**
```python
import psycopg
conn = psycopg.connect("postgresql://user:pass@host/tsdb")
with open('scripts/nyc_locations_schema.sql', 'r') as f:
    conn.execute(f.read())
conn.commit()
```

---

### 2. **load_csv_to_timescaledb.py**
Load CSV data into database

**What it does:**
- Reads `/data/nyc_filming_locations.csv`
- Parses productions and locations
- Creates filming events with timestamps
- Inserts into TimescaleDB with deduplication

**Prerequisites:**
```bash
pip install psycopg
```

**Environment variables:**
```bash
export TIMESCALE_HOST="your-host.tsdb.cloud.timescale.com"
export TIMESCALE_USER="tsdbadmin"
export TIMESCALE_PASSWORD="your-password"
export TIMESCALE_DB="tsdb"  # optional, defaults to tsdb
```

**Run it:**
```bash
python scripts/load_csv_to_timescaledb.py
```

**Expected output:**
```
✅ Connected to TimescaleDB at your-host.tsdb.cloud.timescale.com
📥 Loading data...
✅ Load complete!
   Productions: 45
   Locations:   103
   Events:      127
```

---

### 3. **trend_queries.sql**
Analyze filming trends and patterns

**What's included:**
- Most filmed neighborhoods
- Borough breakdown
- Location reuse (places in multiple productions)
- Production categories (Film vs TV vs Commercial)
- Temporal trends (filming over time)
- Top producing shows
- Street-level hotspots
- TV show analysis by season/episode
- Cross-borough patterns
- Central Park usage
- Database summary statistics

**Run it:**
```bash
psql -h your-host -U user -d tsdb -f scripts/trend_queries.sql
```

**Or interactively:**
```bash
psql -h your-host -U user -d tsdb
```
Then copy-paste queries from the file.

**Example queries:**
```sql
-- Most filmed neighborhoods
SELECT neighborhood, COUNT(*) as filming_events
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
GROUP BY neighborhood
ORDER BY filming_events DESC;

-- Location reuse
SELECT address, COUNT(DISTINCT production_id) as productions
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
GROUP BY address
HAVING COUNT(DISTINCT production_id) > 1
ORDER BY productions DESC;
```

---

### 4. **search_locations.py**
CLI tool for searching the database

**What it does:**
- Search by production (show/film name)
- Search by neighborhood
- Search by specific location
- Search by borough
- Search by year
- Search by category (Film/TV/etc.)
- Pretty-prints results in tables

**Prerequisites:**
```bash
pip install tabulate psycopg
```

**Usage:**
```bash
# Find all locations used in Dexter
python scripts/search_locations.py production dexter

# Find all scenes filmed in Times Square
python scripts/search_locations.py neighborhood "times square"

# Find all productions at Bethesda Fountain
python scripts/search_locations.py location "bethesda"

# Find all filming in Manhattan
python scripts/search_locations.py borough manhattan

# Find all productions filmed in 2024
python scripts/search_locations.py year 2024

# Find all TV productions
python scripts/search_locations.py category tv
```

---

### 5. **sync_nyc_permits.py** (NEW!)
Sync official NYC film permits for validation + enrichment

**What it does:**
- Fetches permits from NYC Open Data API (government data)
- Stores in `nyc_official_permits` table
- Validates your curated data against official records
- Can be scheduled daily for live updates
- Shows summary stats: permits by borough, type, recent activity

**Prerequisites:**
```bash
pip install requests
```

**Run it:**
```bash
# Sync last 30 days of permits
python scripts/sync_nyc_permits.py

# Sync all permits ever issued
python scripts/sync_nyc_permits.py --full

# Verify against your curated data
python scripts/sync_nyc_permits.py --verify
```

**Expected output:**
```
✅ Fetched 847 permits
   Inserted: 812
   Updated: 35

📊 NYC Official Permits Summary
Total permits: 847

By Borough:
  Manhattan: 412
  Brooklyn: 251
```

**Why this matters:**
- Official data validates your curated locations
- Find new productions before they're in blogs
- Track actual filming dates (not just guesses)
- Identify "film-friendly" locations (used repeatedly)

**Schedule daily syncs:**
```bash
# Add to crontab (runs every day at 3 AM)
0 3 * * * cd /path/to/nyc-tv && python scripts/sync_nyc_permits.py >> /tmp/sync.log 2>&1
```

---

### 6. **generate_embeddings.py** (Optional)
Generate OpenAI embeddings for semantic search

**What it does:**
- Fetches scene descriptions without embeddings
- Calls OpenAI API to generate embeddings
- Stores embeddings in database
- Creates vector index for fast search
- Estimates cost (~$0.02-0.05 for 100 locations)

**Prerequisites:**
```bash
pip install openai tqdm
```

**Get OpenAI API key:**
1. Go to https://platform.openai.com/api/keys
2. Create new key
3. Copy it (you won't see it again!)

**Run it:**
```bash
python scripts/generate_embeddings.py --openai-key sk-your-api-key
```

**Dry run (see what would happen):**
```bash
python scripts/generate_embeddings.py --openai-key sk-... --dry-run
```

**Limit to 50 embeddings:**
```bash
python scripts/generate_embeddings.py --openai-key sk-... --limit 50
```

**After embeddings are generated, semantic search:**
```sql
SELECT p.title, l.address, fe.scene_description,
       (fe.scene_embedding <-> query_embedding) as similarity
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
WHERE fe.scene_embedding IS NOT NULL
ORDER BY similarity
LIMIT 10;
```

---

## 🚀 Quick Start (10 minutes)

### Step 1: Set Environment Variables
```bash
export TIMESCALE_HOST="xxx-xxx.tsdb.cloud.timescale.com"
export TIMESCALE_USER="tsdbadmin"
export TIMESCALE_PASSWORD="your-password"
```

### Step 2: Create Database Schema
```bash
psql -h $TIMESCALE_HOST -U $TIMESCALE_USER -d tsdb -f scripts/nyc_locations_schema.sql
```

### Step 3: Load Curated CSV Data (Your Data)
```bash
python scripts/load_csv_to_timescaledb.py
```

### Step 4: Sync Official NYC Permits (Government Data)
```bash
pip install requests  # One-time only
python scripts/sync_nyc_permits.py --verify
```

This validates your data against official government permits ✅

### Step 5: Run Trend Queries
```bash
psql -h $TIMESCALE_HOST -U $TIMESCALE_USER -d tsdb -f scripts/trend_queries.sql
```

### Step 6: Try CLI Search
```bash
python scripts/search_locations.py production dexter
```

**Done!** Your three-layer database is ready. 🎉

---

## 📊 Example Queries

### Find most filmed neighborhoods
```bash
psql -h host -U user -d tsdb -c "
SELECT neighborhood, COUNT(*) as filming_events
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
GROUP BY neighborhood
ORDER BY filming_events DESC;"
```

### Find location reuse
```bash
psql -h host -U user -d tsdb -c "
SELECT address, COUNT(DISTINCT production_id) as productions
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
GROUP BY address
HAVING COUNT(DISTINCT production_id) > 1
ORDER BY productions DESC;"
```

### See all Dexter: Resurrection locations
```bash
python scripts/search_locations.py production "dexter: resurrection"
```

### Find all TV shows filming in Manhattan
```bash
psql -h host -U user -d tsdb -c "
SELECT DISTINCT p.title, COUNT(DISTINCT l.id) as locations
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
WHERE l.borough = 'Manhattan' AND p.category = 'TV'
GROUP BY p.id, p.title
ORDER BY locations DESC;"
```

---

## 🆘 Troubleshooting

### "Connection refused"
Check that TimescaleDB is running and your credentials are correct:
```bash
psql -h $TIMESCALE_HOST -U $TIMESCALE_USER -d tsdb -c "SELECT version();"
```

### "Table already exists"
Drop and recreate:
```sql
DROP HYPERTABLE IF EXISTS filming_events CASCADE;
DROP TABLE IF EXISTS productions CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
-- Then re-run schema file
```

### CSV loader skipping rows
Check CSV format:
```bash
head -5 data/nyc_filming_locations.csv
```

Should start with column headers:
```
Title,Address,Borough/Neighborhood,Description,Category,Season/Episode,Year,Source
```

### Missing tabulate module
```bash
pip install tabulate
```

---

## 📈 Next Steps

1. ✅ **Load data** → `load_csv_to_timescaledb.py`
2. ✅ **Explore with queries** → `trend_queries.sql`
3. ✅ **Search CLI** → `search_locations.py`
4. ⏭️ **Add embeddings** → `generate_embeddings.py`
5. ⏭️ **Build API** → Flask/FastAPI wrapper
6. ⏭️ **Web dashboard** → Streamlit or React frontend

---

## 📚 Resources

- **TimescaleDB Docs:** https://docs.timescale.com
- **pgvector Docs:** https://github.com/pgvector/pgvector
- **OpenAI Embeddings:** https://platform.openai.com/docs/guides/embeddings
- **PostgreSQL Full-Text Search:** https://www.postgresql.org/docs/current/textsearch.html

---

## 💡 Tips

- **Backup before major changes:**
  ```bash
  pg_dump -h host -U user -d tsdb > backup.sql
  ```

- **Monitor database size:**
  ```sql
  SELECT pg_size_pretty(pg_total_relation_size('filming_events')) as size;
  ```

- **View indexes:**
  ```sql
  SELECT indexname FROM pg_indexes WHERE tablename = 'filming_events';
  ```

- **Check hypertable chunks:**
  ```sql
  SELECT * FROM timescaledb_information.chunks 
  WHERE hypertable_name = 'filming_events';
  ```

---

**Happy exploring! 🎬🗽**
