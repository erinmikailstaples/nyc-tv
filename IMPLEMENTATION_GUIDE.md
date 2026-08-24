# NYC-TV MVP Implementation Guide

## What Changed

I've simplified the original PRD from a 6-8 week, multi-feature vision into a focused **2-3 week MVP**. Here's what's different:

### Old PRD Was
- 🔴 7 user personas with different needs
- 🔴 5+ phases with complex dependencies
- 🔴 Multiple data sources (IMDb, Wikipedia, user contributions)
- 🔴 Neighborhood analytics, exports, recommendations
- 🔴 Time-partitioned tables, complex views, materilialized views with fuzzy matching

### New MVP Is
- 🟢 **One core use case**: Browse & search filming locations on a map
- 🟢 **One table**: `permits` (250k NYC film permits)
- 🟢 **One API**: Basic endpoints for search, filter, details
- 🟢 **One map**: Deck.gl or Mapbox showing permit locations
- 🟢 **Shipping in 2-3 weeks**, not 6-8

---

## What You Have Now

### 1. **PRD.md** (Updated)
Simplified product requirements focusing on MVP only.

### 2. **schema.sql** (New)
PostgreSQL schema with:
- Single `permits` table
- Indexes for fast queries
- Bonus: `production_summary` materialized view for future dashboards

### 3. **DATABASE.md** (New)
Complete database setup guide with:
- How to initialize PostgreSQL
- Sample API queries
- Data ingestion steps

### 4. **scripts/ingest_permits.py** (New)
Python script that:
- Fetches data from NYC Open Data API
- Inserts into PostgreSQL
- Handles pagination & errors automatically
- Ready to run: `python scripts/ingest_permits.py`

---

## How to Build the MVP

### Phase 1: Database (2-3 hours)

```bash
# 1. Set up PostgreSQL with PostGIS
createdb nyc_tv
psql nyc_tv -c "CREATE EXTENSION postgis;"

# 2. Create schema
psql nyc_tv < schema.sql

# 3. Ingest data
pip install requests psycopg2-binary
python scripts/ingest_permits.py
# Takes ~30 min to fetch and insert 250k+ permits
```

**Done**: You now have 250k+ filming locations in PostgreSQL ✓

### Phase 2: Backend API (1 day)

Build a simple FastAPI or Express server with these endpoints:

```python
# FastAPI example
from fastapi import FastAPI
import psycopg2

app = FastAPI()
conn = psycopg2.connect("postgresql://localhost/nyc_tv")

@app.get("/api/permits")
def get_permits(
    borough: str = None,
    production_type: str = None,
    year: int = None,
    limit: int = 100
):
    """Return permits with optional filters."""
    query = "SELECT * FROM permits WHERE 1=1"
    params = []

    if borough:
        query += " AND borough = %s"
        params.append(borough)

    if production_type:
        query += " AND production_type = %s"
        params.append(production_type)

    if year:
        query += " AND EXTRACT(YEAR FROM permit_issued_date) = %s"
        params.append(year)

    query += " ORDER BY permit_issued_date DESC LIMIT %s"
    params.append(limit)

    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    return results

@app.get("/api/permits/search")
def search_permits(q: str, limit: int = 50):
    """Search by production name (case-insensitive)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM permits WHERE production_name ILIKE %s ORDER BY permit_issued_date DESC LIMIT %s",
        (f"%{q}%", limit)
    )
    results = cursor.fetchall()
    return results

@app.get("/api/permits/{permit_id}")
def get_permit(permit_id: int):
    """Get a single permit by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM permits WHERE id = %s", (permit_id,))
    result = cursor.fetchone()
    return result
```

**Done**: API is running, can fetch and search permits ✓

### Phase 3: Frontend Map (1 day)

Build a React + Mapbox component:

```jsx
// Example: React + Mapbox
import mapboxgl from 'mapbox-gl';
import React, { useState, useEffect } from 'react';

export default function Map() {
  const [permits, setPermits] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    // Fetch permits from API
    const url = searchTerm
      ? `/api/permits/search?q=${searchTerm}`
      : '/api/permits?limit=1000';

    fetch(url)
      .then(r => r.json())
      .then(data => setPermits(data));
  }, [searchTerm]);

  useEffect(() => {
    // Initialize Mapbox
    const map = new mapboxgl.Map({
      container: 'map',
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [-74.0, 40.7], // NYC
      zoom: 11
    });

    // Add permit pins
    permits.forEach(permit => {
      new mapboxgl.Marker()
        .setLngLat([permit.longitude, permit.latitude])
        .setPopup(new mapboxgl.Popup().setHTML(`
          <strong>${permit.production_name}</strong><br/>
          ${permit.location_address}<br/>
          ${permit.production_type}
        `))
        .addTo(map);
    });
  }, [permits]);

  return (
    <div>
      <input
        type="text"
        placeholder="Search production..."
        value={searchTerm}
        onChange={e => setSearchTerm(e.target.value)}
      />
      <div id="map" style={{ width: '100%', height: '600px' }} />
    </div>
  );
}
```

**Done**: Map shows filming locations, search works ✓

---

## Deployment

### Backend
- **Railway**: Deploy FastAPI in 5 minutes, auto-scales
- **Vercel**: Use Vercel Functions for serverless API (if Node.js)

### Frontend
- **Vercel**: Deploy Next.js or React app directly

### Database
- **Railway PostgreSQL**: Managed database, automatic backups

---

## After MVP Ships

Once you have users clicking around the map, you can add:

1. **Better search** — Fuzzy matching, popular show names
2. **IMDb integration** — Show title, year, genre
3. **Neighborhood dashboards** — See what's filmed per area
4. **Exports** — CSV/GeoJSON downloads
5. **User accounts** — Favorites, saved searches
6. **Analytics** — Track popular locations, trends

All of these are 1-2 day additions **after** you've validated users want the map.

---

## File Structure

```
nyc-tv/
├── PRD.md                          # Product requirements (simplified)
├── DATABASE.md                     # Database setup guide
├── schema.sql                      # SQL schema (ready to run)
├── IMPLEMENTATION_GUIDE.md         # This file
├── scripts/
│   └── ingest_permits.py           # Data ingestion script
├── backend/                        # (You'll create)
│   ├── main.py                     # FastAPI app
│   └── requirements.txt
└── frontend/                       # (You'll create)
    ├── src/
    │   └── Map.jsx                 # Map component
    └── package.json
```

---

## Next Steps

1. **Read PRD.md** — Understand the MVP scope
2. **Follow DATABASE.md** — Set up PostgreSQL & ingest data
3. **Build backend** — 4 API endpoints (2-3 hours)
4. **Build frontend** — React + Mapbox component (4-5 hours)
5. **Deploy** — Railway + Vercel (1-2 hours)
6. **Ship & gather feedback** — Then iterate

**Total time: 2-3 weeks, one person, MVP in production.**

Good luck! 🚀
