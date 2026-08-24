# NYC-TV Database Setup

## Quick Start

### 1. Create Database
```bash
createdb nyc_tv
psql nyc_tv -c "CREATE EXTENSION postgis;"
```

### 2. Initialize Schema
```bash
psql nyc_tv < schema.sql
```

### 3. Load Data
```bash
python scripts/ingest_permits.py
```

---

## Schema

### `permits` Table

This is the only table needed for MVP.

```sql
CREATE TABLE permits (
  id SERIAL PRIMARY KEY,
  event_id VARCHAR(50) UNIQUE NOT NULL,
  production_name VARCHAR(255) NOT NULL,
  permit_issued_date DATE,
  permit_expiration_date DATE,
  production_type VARCHAR(100),
  production_company VARCHAR(255),
  location_address VARCHAR(500),
  borough VARCHAR(50),
  zip_code VARCHAR(10),
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  status VARCHAR(50),
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_production_name ON permits (production_name);
CREATE INDEX idx_borough ON permits (borough);
CREATE INDEX idx_production_type ON permits (production_type);
CREATE INDEX idx_permit_issued_date ON permits (permit_issued_date DESC);
CREATE INDEX idx_geom ON permits USING GIST (
  ll_to_earth(latitude, longitude)
);
```

---

## Data Ingestion

### Source
**NYC Open Data - Film Permits**  
API: `https://data.cityofnewyork.us/resource/tg4x-b46p.json`

### Sample Python Script

```python
import requests
import psycopg2
from datetime import datetime

# Fetch data from NYC Open Data
url = "https://data.cityofnewyork.us/resource/tg4x-b46p.json"
params = {"$limit": 50000}  # API limit, paginate if needed

response = requests.get(url, params=params)
permits = response.json()

# Connect to database
conn = psycopg2.connect("dbname=nyc_tv user=postgres")
cursor = conn.cursor()

# Insert data
insert_sql = """
INSERT INTO permits (
  event_id, production_name, permit_issued_date, 
  permit_expiration_date, production_type, production_company,
  location_address, borough, zip_code, latitude, longitude, status
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (event_id) DO NOTHING;
"""

for permit in permits:
  try:
    cursor.execute(insert_sql, (
      permit.get('event_id'),
      permit.get('production_name'),
      permit.get('permit_issued_date'),
      permit.get('permit_expiration_date'),
      permit.get('production_type'),
      permit.get('production_company'),
      permit.get('location'),
      permit.get('borough'),
      permit.get('zip_code'),
      float(permit.get('latitude', 0)),
      float(permit.get('longitude', 0)),
      permit.get('status', 'Unknown')
    ))
  except Exception as e:
    print(f"Error inserting permit {permit.get('event_id')}: {e}")

conn.commit()
cursor.close()
conn.close()
print(f"Ingested {len(permits)} permits")
```

---

## API Queries

### Get Permits by Borough
```sql
SELECT * FROM permits 
WHERE borough = 'Manhattan' 
ORDER BY permit_issued_date DESC 
LIMIT 100;
```

### Search by Production Name
```sql
SELECT * FROM permits 
WHERE production_name ILIKE '%Friends%' 
ORDER BY permit_issued_date DESC;
```

### Count by Type
```sql
SELECT production_type, COUNT(*) as count
FROM permits
GROUP BY production_type
ORDER BY count DESC;
```

### Permits in Date Range
```sql
SELECT * FROM permits
WHERE permit_issued_date BETWEEN '2023-01-01' AND '2023-12-31'
AND borough = 'Brooklyn'
ORDER BY permit_issued_date DESC;
```

### Geographic Query (e.g., within 1km of point)
```sql
SELECT * FROM permits
WHERE earth_distance(ll_to_earth(latitude, longitude), 
                     ll_to_earth(40.7128, -74.0060)) < 1000
LIMIT 50;
```

---

## Notes

- **Data Volume**: ~250k+ permits total
- **Update Frequency**: Monthly sync recommended
- **Geospatial**: PostGIS provides fast geographic queries
- **No Complex Joins**: MVP keeps schema flat for simplicity

---

## Next Steps (Phase 2)

- Add `productions` table for IMDb metadata
- Add materialized view for permit-production matching
- Cache frequently accessed queries with Redis
- Add user contribution tables (optional)
