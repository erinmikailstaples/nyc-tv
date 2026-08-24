# NYC-TV: Interactive Film & TV Location Map

**Product Requirements Document - MVP Edition**

---

## 1. Overview

**NYC-TV** is a searchable, interactive map showing where films and TV shows are shot across New York City. Users can explore filming locations from the NYC Open Data film permits dataset.

- **Target Users**: Film fans, tourists, location scouts, researchers
- **Core Feature**: Browse & search filmed locations on an interactive map
- **Timeline**: 2-3 weeks to MVP

---

## 2. MVP Scope: Just the Essentials

### What Users Can Do
1. **View locations on a map** — See all film permit locations across NYC
2. **Search by production name** — Find "Friends" or "Succession" locations
3. **Filter by basics** — Borough, production type, year range
4. **Click a location** — See permit details (address, production name, date, type)

### What We Won't Do (Yet)
- ❌ IMDb integration or rich metadata
- ❌ Neighborhood dashboards or analytics
- ❌ User accounts or contributions
- ❌ Mobile app (web-only)
- ❌ Exports/API (Phase 2)
- ❌ Photos or historical context
- ❌ Precise scene-level data

---

## 3. User Journeys (MVP)

### Journey 1: "Where was Friends shot?"
1. User opens map → sees dots all over NYC
2. User searches "Friends" → map zooms to relevant permits
3. User clicks a pin → sees address, production name, date
4. Done ✓

### Journey 2: "What was filmed in my neighborhood?"
1. User zooms into their neighborhood on the map
2. User filters by borough or year if needed
3. User clicks pins to see what was filmed where
4. Done ✓

### Journey 3: "Show me TV vs. Film locations"
1. User uses production type filter
2. Map updates to show only TV or Film permits
3. User can click around to explore
4. Done ✓

---

## 4. Data Architecture (MVP)

### Data Source
**NYC Open Data - Film Permits**
- URL: https://data.cityofnewyork.us/resource/tg4x-b46p.json
- Contains: ~25k permits/year, 250k+ historical records
- Key fields: production name, location, borough, dates, lat/lng, type

### Database Schema (Simple & Clean)

```sql
-- Single table: permits
-- This is all we need for MVP
CREATE TABLE permits (
  id SERIAL PRIMARY KEY,
  event_id VARCHAR(50) UNIQUE NOT NULL,
  production_name VARCHAR(255) NOT NULL,
  permit_issued_date DATE,
  permit_expiration_date DATE,
  production_type VARCHAR(100),           -- 'Feature Film', 'TV Series', 'Music Video', etc.
  production_company VARCHAR(255),
  location_address VARCHAR(500),          -- Full address from permit
  borough VARCHAR(50),                    -- Manhattan, Brooklyn, Queens, Bronx, Staten Island
  zip_code VARCHAR(10),
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  status VARCHAR(50),                     -- 'Active', 'Completed', 'Cancelled'
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_production_name ON permits (production_name);
CREATE INDEX idx_borough ON permits (borough);
CREATE INDEX idx_production_type ON permits (production_type);
CREATE INDEX idx_permit_issued_date ON permits (permit_issued_date DESC);
CREATE INDEX idx_location ON permits USING GIST (
  ll_to_earth(latitude, longitude)  -- For geographic queries
);
```

### Data Ingestion
- One-time import: Full NYC Open Data dataset → permits table
- Ongoing: Sync new permits monthly via API
- No complex transformations needed for MVP

---

## 5. Technical Stack

| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL + PostGIS |
| Backend API | Python (FastAPI) or Node.js (Express) |
| Frontend Map | React + Mapbox GL or Deck.gl |
| Hosting | Vercel (frontend) + Railway (backend) |

---

## 6. MVP Implementation Timeline

### Week 1: Data & Backend
- Download NYC permits data
- Create PostgreSQL database & permits table
- Write data ingestion script
- Build basic API endpoints:
  - `GET /api/permits` (with filters: borough, type, date range)
  - `GET /api/permits/search?q=Friends`

### Week 2: Frontend Map
- Set up React + Mapbox/Deck.gl
- Display permit locations as pins
- Implement search bar
- Add borough/type/date filters
- Show permit details on click

### Week 3: Polish & Launch
- Test with real data
- Fix bugs & improve UX
- Deploy backend & frontend
- Launch MVP

---

## 7. Success Criteria

The MVP succeeds when:
- Map loads with 250k+ permit locations
- Search for a show name returns its locations
- Filters work (borough, type, date)
- Clicking a pin shows permit details
- Core flows are bug-free

---

## 8. What Comes Next (Phase 2+)

- IMDb integration for richer metadata
- Neighborhood analytics & trends
- CSV/GeoJSON export
- Better search (fuzzy matching, popular shows)
- Public API

---

## Document Info

- **Version**: 2.0 (MVP Edition)
- **Last Updated**: 2026-08-24
- **Owner**: Erin Mikail Staples
