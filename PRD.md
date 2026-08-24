# NYC-TV: Interactive Film & TV Geospatial Explorer

**Product Requirements Document**

---

## 1. Executive Summary

**NYC-TV** is an interactive geospatial visualization platform that maps where films and TV shows are shot across New York City. By combining NYC film permits data with production metadata and scene information, users can explore the city through the lens of media — discovering where their favorite scenes were filmed, what projects have been shot in their neighborhood, and understanding production patterns across NYC's five boroughs.

**Core Value Proposition:**
- Film enthusiasts, location scouts, and tourists can discover filming locations
- Production companies gain insights into popular neighborhoods and permitting trends
- Urban planners and community boards understand media production impact in their areas
- Developers/researchers access a rich geospatial dataset for analysis

**Target Launch:** Phase 1 (MVP) in 6-8 weeks

---

## 2. Product Vision

### Long-term Goal
Become NYC's definitive source for understanding the intersection of media production and geography — allowing users to explore the city as a character, not just a location.

### Guiding Principles
- **Exploratory**: Designed for casual browsing and discovery
- **Accurate**: Powered by official NYC permits data + crowdsourced production metadata
- **Geospatial-First**: Map is the primary interface; tables/lists are secondary
- **Performance**: Handle 10k+ filming locations without lag
- **Accessible**: Works for casual users and researchers alike

---

## 3. Problem Statement

### Current Pain Points
1. **Fragmented Data**: Film location info scattered across IMDb, production notes, fan wikis, and social media — no authoritative source
2. **Permit Opacity**: NYC issues thousands of film permits annually, but public data doesn't link to what was actually produced
3. **Geographic Blindness**: Users can't easily ask "What was filmed in my neighborhood?" or "Where do most action scenes happen?"
4. **No Historical Context**: Difficult to understand production trends by location or time

### Opportunity
NYC Department of Consumer Affairs publishes film permit data (NYC Open Data). Combined with production metadata and scene information, this becomes a rich, explorable dataset.

---

## 4. User Personas & Use Cases

### Persona 1: "Tourist/Fan" (40% of users)
- Wants to visit filming locations from favorite shows (e.g., *Friends*, *Succession*)
- Needs: Easy search, walking routes, current-day photos of locations
- **Use Case**: Search for "Chandler's apartment" and see the real building + episode clips

### Persona 2: "Location Scout / Producer" (30% of users)
- Planning a shoot, needs neighborhood insights and historical data
- Wants to understand: What's popular? Permitting trends? Competitor productions?
- **Use Case**: Filter by neighborhood, view permit density, production timeline

### Persona 3: "Data Enthusiast / Researcher" (20% of users)
- Analyzing media production patterns, urban dynamics, cultural trends
- Needs: Export data, time-series analysis, statistical summaries
- **Use Case**: Compare production activity by neighborhood, year-over-year trends

### Persona 4: "Community Board / Local Official" (10% of users)
- Monitoring local impact, managing permitting, understanding neighborhood character
- Needs: Production volume trends, permit details, neighborhood-level dashboards
- **Use Case**: See all 2023-2025 productions in their district with permit details

---

## 5. Core Features (MVP)

### 5.1 Interactive Map Interface
- **Tech**: Deck.gl or Mapbox for high-performance geospatial rendering
- **Features**:
  - Base layer: NYC streets/neighborhoods
  - Permit pins: Color-coded by production type (film, TV, music, etc.)
  - Click a pin: Show permit details (date, location, production name, status)
  - Heatmap mode: See filming density by block
  - Filter by:
    - Date range (slider: permits issued 2015-2026)
    - Production type (Film, TV, Documentary, Music Video, etc.)
    - Borough/neighborhood
    - Production status (active, completed)

### 5.2 Production Details Panel
When clicking a permit or production, show:
- Production name & type
- Filming dates
- Borough & neighborhood
- Production company
- Specific address(es)
- Link to IMDb/Wikipedia (if available)
- Photos/clips from location (future phase)
- User contributions: scenes filmed here, episode info

### 5.3 Search & Discovery
- **Search bar**: Find by production name, show title, or actor
- **Autocomplete**: Popular productions, neighborhoods, landmarks
- **Featured collections** (hardcoded MVP):
  - "All *Succession* locations"
  - "All *Friends* locations"
  - "Films from [selected year]"
  - "Most filmed neighborhoods"

### 5.4 Neighborhood Insights
- Clicking a neighborhood shows:
  - Production count by year (bar chart)
  - Top 5 productions filmed there
  - Most common production types
  - Permit volume trend (last 10 years)

### 5.5 Data Export & API (Phase 1.5)
- Export filtered results as CSV/GeoJSON
- Simple REST API for developers:
  - `GET /api/permits?borough=Brooklyn&year=2024`
  - `GET /api/production/{id}`
  - Geospatial queries (circle/polygon search)

---

## 6. Data Architecture

### 6.1 Primary Data Sources

#### NYC Film Permits (NYC Open Data)
- **URL**: [NYC Open Data - Film Permits](https://data.cityofnewyork.us/resource/tg4x-b46p.json) 
- **Fields**: event_ID, production_name, permit_issued_date, permit_expiration_date, location, borough, zip_code, latitude, longitude, production_type, production_company
- **Volume**: ~25k permits/year (250k+ historical)
- **Freshness**: Near real-time

#### Enrichment Data (Sources to integrate):
1. **IMDb/Wikipedia**: Production titles, genres, release dates, cast info
2. **User Contributions**: Scene information, episode numbers, coordinates refinement
3. **Historic Photos**: Location photos from [time-period], updated status

### 6.2 Database Schema (TimescaleDB)

```sql
-- Permits (main fact table, hypertable for time-series)
CREATE TABLE IF NOT EXISTS permits (
  id SERIAL PRIMARY KEY,
  event_id VARCHAR UNIQUE,
  production_name VARCHAR,
  permit_issued_date TIMESTAMPTZ,
  permit_expiration_date TIMESTAMPTZ,
  production_type VARCHAR,
  production_company VARCHAR,
  location VARCHAR,
  borough VARCHAR,
  neighborhood VARCHAR,
  zip_code VARCHAR,
  latitude FLOAT8,
  longitude FLOAT8,
  geom GEOMETRY(POINT, 4326),
  status VARCHAR, -- active, completed, cancelled
  created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (permit_issued_date);

-- Scenes (crowdsourced/IMDb linked)
CREATE TABLE scenes (
  id SERIAL PRIMARY KEY,
  permit_id INTEGER REFERENCES permits(id),
  production_id VARCHAR,  -- IMDb ID
  episode_info VARCHAR,   -- "S01E05" format
  scene_description TEXT,
  latitude FLOAT8,
  longitude FLOAT8,
  geom GEOMETRY(POINT, 4326),
  source VARCHAR,         -- 'imdb', 'user', 'wikipedia'
  verified BOOLEAN,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Neighborhoods (reference table)
CREATE TABLE neighborhoods (
  id SERIAL PRIMARY KEY,
  name VARCHAR UNIQUE,
  borough VARCHAR,
  geom GEOMETRY(POLYGON, 4326)
);

-- Production metadata (IMDb-linked)
CREATE TABLE productions (
  id VARCHAR PRIMARY KEY,  -- IMDb ID
  title VARCHAR,
  type VARCHAR,            -- 'TV', 'Film', etc.
  release_year INT,
  imdb_url VARCHAR,
  wikipedia_url VARCHAR,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Materialized view for permit-production joins
CREATE MATERIALIZED VIEW permit_production_view AS
  SELECT 
    p.*, 
    prod.title, 
    prod.type, 
    prod.release_year,
    prod.imdb_url
  FROM permits p
  LEFT JOIN productions prod 
    ON LOWER(p.production_name) SIMILAR TO LOWER(prod.title) || '%'
  WHERE p.permit_issued_date > NOW() - INTERVAL '15 years';
```

### 6.3 Indexing Strategy
```sql
-- Geospatial index for fast location queries
CREATE INDEX ON permits USING GIST (geom);

-- Time-series optimization
CREATE INDEX ON permits (permit_issued_date DESC);

-- Text search on production names
CREATE INDEX ON permits USING GIN (
  to_tsvector('english', production_name)
);

-- Borough/type filtering
CREATE INDEX ON permits (borough, production_type);
```

---

## 7. Technical Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Database** | TimescaleDB (PostgreSQL) | Time-series optimized, native geospatial support (PostGIS), handles 250k+ records efficiently |
| **Backend API** | Python (FastAPI) | Fast, async-ready, great geospatial libraries (Shapely, GeoPandas) |
| **Geospatial Processing** | GeoPandas + Shapely | Neighborhood polygon queries, spatial joins |
| **Frontend** | React + Deck.gl / Mapbox GL | High-performance geospatial rendering, 60 FPS on large datasets |
| **Caching** | Redis (optional Phase 2) | Cache aggregated queries (top productions, neighborhood stats) |
| **Deployment** | Docker + Vercel/Railway | Easy scaling, minimal DevOps |

---

## 8. MVP Scope & Timeline

### Phase 1: Foundation (Weeks 1-4)
- [ ] Ingest NYC permits data into TimescaleDB
- [ ] Build FastAPI backend with permit endpoints
- [ ] Implement geospatial queries (borough/neighborhood filtering)
- [ ] Basic React + Deck.gl map
- [ ] Search functionality

### Phase 1.5: Enrichment (Weeks 5-6)
- [ ] Link productions to IMDb metadata (title matching)
- [ ] Neighborhood dashboard
- [ ] Export as CSV/GeoJSON
- [ ] Date range filtering

### Phase 2: Polish (Weeks 7-8)
- [ ] UI refinement & mobile responsiveness
- [ ] Performance optimization
- [ ] Analytics (track popular locations)
- [ ] Soft launch + feedback

### Future Phases
- Phase 2.5: User contributions (comment, add scenes)
- Phase 3: Historical photos, street view integration
- Phase 4: Recommendations ("Films like this were shot near you")
- Phase 5: Mobile app

---

## 9. Success Metrics

### Engagement
- Daily active users (DAU)
- Search volume & trending queries
- Map interactions (clicks, filters applied)
- Export/API usage

### Data Quality
- % of permits successfully matched to productions
- Geospatial accuracy (user feedback on location precision)
- Data freshness (lag between permit issuance & availability)

### Platform Health
- API response time (target: <200ms for map queries)
- Map render time (target: <500ms for 10k points)
- User-contributed scene accuracy

---

## 10. Out of Scope (MVP)

- ❌ Historical photos/images of locations
- ❌ Street view integration
- ❌ Real-time permit alerts
- ❌ User authentication & favoriting
- ❌ Mobile app (responsive web only)
- ❌ Predictions ("where will next season film?")

---

## 11. Open Questions / Risks

1. **Data Matching**: How accurately can we match permit "production_name" to IMDb titles?
   - *Mitigation*: Fuzzy string matching + manual curated list of popular shows

2. **Geospatial Precision**: NYC permits sometimes list broad areas; can we pinpoint exact locations?
   - *Mitigation*: Start with permit address; layer in user contributions

3. **Dataset Gaps**: Are all permits in the NYC Open Data source?
   - *Mitigation*: Cross-check with anecdotal data (IMDb, fan wikis); document gaps publicly

4. **Infrastructure Cost**: TimescaleDB + API + frontend hosting?
   - *Mitigation*: Use managed services (Railway, Vercel); optimize queries to minimize compute

---

## 12. Glossary

- **Permit**: Official NYC film authorization document
- **Production**: Film, TV series, music video, or documentary being shot
- **Borough**: NYC's five administrative districts (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
- **Neighborhood**: Smaller geographic division within a borough
- **Geom**: Geometry object (point/polygon) used in PostGIS spatial queries
- **Hypertable**: TimescaleDB term for time-partitioned table (optimized for time-series data)

---

## 13. Appendix: Sample User Journeys

### Journey 1: "Where was this scene filmed?"
1. User searches "Grand Central Terminal Breaking Bad"
2. App returns all permits for Breaking Bad + map pins on that location
3. User clicks pin → sees episode info, permit details, photos
4. User exports as PDF for travel planning

### Journey 2: "What's being filmed in my neighborhood?"
1. User clicks their neighborhood (e.g., "Park Slope, Brooklyn")
2. Dashboard shows: 247 permits last 10 years, 15 major productions
3. Bar chart shows production trend (spike in 2019-2020)
4. User filters by TV shows only → sees top 5 shows filmed there
5. Clicks each to see specific addresses

### Journey 3: "Help me scout a location"
1. Producer searches "Median household income > $150k, similar to Riverdale"
2. App suggests neighborhoods matching that profile + shows production density
3. Producer views permit trends to understand competition
4. Producer exports current active permits in area + recent completed productions
5. Reaches out to neighborhoods with lower permitting load

---

**Document Version**: 1.0  
**Last Updated**: 2026-08-24  
**Owner**: Erin Mikail Staples (erin@tigerdata.com)
