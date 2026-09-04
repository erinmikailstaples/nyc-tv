-- NYC TV/Film Locations Database Schema
-- TimescaleDB + pgvector
-- Run this to set up the database structure

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS vector CASCADE;

-- ============================================================================
-- PRODUCTIONS TABLE
-- Stores metadata about shows, films, commercials, etc.
-- ============================================================================
CREATE TABLE IF NOT EXISTS productions (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL UNIQUE,
  category TEXT,  -- 'Film', 'TV', 'Commercial', 'Music Video', etc.
  year_filmed INT,  -- Year production was filmed
  year_aired INT,   -- Year it aired/was released
  description TEXT,  -- Synopsis or notes
  source TEXT,  -- Where this info came from (URL, etc.)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_productions_category ON productions(category);
CREATE INDEX idx_productions_year_aired ON productions(year_aired);

-- ============================================================================
-- LOCATIONS TABLE
-- Stores real-world NYC addresses used for filming
-- ============================================================================
CREATE TABLE IF NOT EXISTS locations (
  id SERIAL PRIMARY KEY,
  address TEXT NOT NULL,
  borough TEXT,  -- Manhattan, Brooklyn, Queens, Bronx, Staten Island
  neighborhood TEXT,  -- Times Square, Upper West Side, DUMBO, etc.
  location_name TEXT,  -- Human name (Katz's Deli, Empire Hotel, etc.)
  latitude FLOAT,
  longitude FLOAT,
  notes TEXT,  -- Additional details (building history, current use, etc.)
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(address, borough)
);

CREATE INDEX idx_locations_borough ON locations(borough);
CREATE INDEX idx_locations_neighborhood ON locations(neighborhood);
CREATE INDEX idx_locations_name ON locations(location_name);

-- ============================================================================
-- FILMING_EVENTS HYPERTABLE
-- Time-series data: what was filmed where and when
-- This is a HYPERTABLE (TimescaleDB) for optimized time-range queries
-- ============================================================================
CREATE TABLE IF NOT EXISTS filming_events (
  time TIMESTAMPTZ NOT NULL,
  production_id INT NOT NULL REFERENCES productions(id),
  location_id INT NOT NULL REFERENCES locations(id),
  season_episode TEXT,  -- S1E1, S2E5, etc. (NULL for films)
  scene_description TEXT,  -- What was filmed here and why it matters
  scene_embedding vector(1536),  -- OpenAI embedding (add later)
  source_credit TEXT,  -- Twitter handle or source of info (@levifishman, etc.)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (time, production_id, location_id)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('filming_events', 'time', if_not_exists => TRUE);

-- Indexes for common queries
CREATE INDEX idx_filming_events_production ON filming_events(production_id);
CREATE INDEX idx_filming_events_location ON filming_events(location_id);
CREATE INDEX idx_filming_events_season ON filming_events(season_episode);

-- Vector index for semantic search (when embeddings are added)
CREATE INDEX idx_filming_events_embedding
  ON filming_events
  USING ivfflat (scene_embedding vector_cosine_ops)
  WHERE scene_embedding IS NOT NULL;

-- ============================================================================
-- SCENE_EMBEDDINGS TABLE
-- Optional: Store OpenAI embeddings for semantic search
-- ============================================================================
CREATE TABLE IF NOT EXISTS scene_embeddings (
  id SERIAL PRIMARY KEY,
  event_id INT NOT NULL REFERENCES filming_events(time, production_id, location_id),
  embedding vector(1536),  -- OpenAI text-embedding-3-small
  embedding_model TEXT,  -- Model used (text-embedding-3-small, etc.)
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scene_embeddings_embedding
  ON scene_embeddings
  USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- NYC_OFFICIAL_PERMITS TABLE
-- Official permits from NYC Open Data API
-- Source: https://data.cityofnewyork.us/resource/tg4x-b46v.json
-- Used for validation and enrichment of curated data
-- ============================================================================
CREATE TABLE IF NOT EXISTS nyc_official_permits (
  id SERIAL PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  location TEXT,  -- e.g., "Times Square South", "Brooklyn Bridge"
  production_company TEXT,  -- Company name
  event_type TEXT,  -- 'TV Series', 'Feature Film', 'Commercial', etc.
  start_date DATE,  -- Filming start date
  end_date DATE,  -- Filming end date
  borough TEXT,  -- Manhattan, Brooklyn, Queens, Bronx, Staten Island
  latitude FLOAT,  -- Approximate location
  longitude FLOAT,
  permit_json JSONB,  -- Full permit data from API
  synced_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_nyc_permits_location ON nyc_official_permits(location);
CREATE INDEX idx_nyc_permits_company ON nyc_official_permits(production_company);
CREATE INDEX idx_nyc_permits_borough ON nyc_official_permits(borough);
CREATE INDEX idx_nyc_permits_dates ON nyc_official_permits(start_date, end_date);
CREATE INDEX idx_nyc_permits_synced ON nyc_official_permits(synced_at DESC);

-- ============================================================================
-- VIEW: Most Popular Locations
-- Quick view of which real-world locations are filmed most
-- ============================================================================
CREATE OR REPLACE VIEW popular_locations AS
SELECT
  l.id,
  l.location_name,
  l.address,
  l.borough,
  l.neighborhood,
  COUNT(*) as filming_count,
  COUNT(DISTINCT fe.production_id) as unique_productions,
  STRING_AGG(DISTINCT p.title, ' | ') as productions
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
GROUP BY l.id, l.location_name, l.address, l.borough, l.neighborhood
ORDER BY filming_count DESC;

-- ============================================================================
-- VIEW: Production Timeline
-- See when each production was filmed
-- ============================================================================
CREATE OR REPLACE VIEW production_timeline AS
SELECT
  p.title,
  p.category,
  MIN(fe.time)::DATE as first_filming_date,
  MAX(fe.time)::DATE as last_filming_date,
  COUNT(*) as filming_events,
  COUNT(DISTINCT fe.location_id) as locations_used,
  STRING_AGG(DISTINCT l.neighborhood, ', ') as neighborhoods
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
GROUP BY p.title, p.category
ORDER BY MIN(fe.time) DESC;

-- ============================================================================
-- VIEW: Borough Analysis
-- See filming activity by borough
-- ============================================================================
CREATE OR REPLACE VIEW borough_analysis AS
SELECT
  l.borough,
  COUNT(*) as filming_events,
  COUNT(DISTINCT l.id) as unique_locations,
  COUNT(DISTINCT fe.production_id) as unique_productions,
  COUNT(DISTINCT fe.season_episode) as episodes,
  STRING_AGG(DISTINCT p.category, ', ') as categories
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
WHERE l.borough IS NOT NULL
GROUP BY l.borough
ORDER BY filming_events DESC;

-- ============================================================================
-- FUNCTION: Add filming event with automatic location lookup
-- ============================================================================
CREATE OR REPLACE FUNCTION add_filming_event(
  p_title TEXT,
  p_address TEXT,
  p_borough TEXT,
  p_time TIMESTAMPTZ,
  p_scene_description TEXT,
  p_season_episode TEXT DEFAULT NULL,
  p_source TEXT DEFAULT NULL
)
RETURNS void AS $$
DECLARE
  v_production_id INT;
  v_location_id INT;
BEGIN
  -- Get or create production
  INSERT INTO productions (title, description, source)
  VALUES (p_title, p_scene_description, p_source)
  ON CONFLICT (title) DO UPDATE SET updated_at = NOW()
  RETURNING id INTO v_production_id;

  IF v_production_id IS NULL THEN
    SELECT id INTO v_production_id FROM productions WHERE title = p_title;
  END IF;

  -- Get or create location
  INSERT INTO locations (address, borough, source)
  VALUES (p_address, p_borough, p_source)
  ON CONFLICT (address, borough) DO UPDATE SET updated_at = NOW()
  RETURNING id INTO v_location_id;

  IF v_location_id IS NULL THEN
    SELECT id INTO v_location_id FROM locations WHERE address = p_address AND borough = p_borough;
  END IF;

  -- Insert filming event
  INSERT INTO filming_events (time, production_id, location_id, scene_description, season_episode, source_credit)
  VALUES (p_time, v_production_id, v_location_id, p_scene_description, p_season_episode, p_source);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENT SECTION: Table Documentation
-- ============================================================================

COMMENT ON TABLE productions IS 'Metadata about TV shows, films, commercials, and other productions';
COMMENT ON COLUMN productions.title IS 'Production name (e.g., "Dexter: Resurrection", "King Kong")';
COMMENT ON COLUMN productions.category IS 'Type of production: Film, TV, Commercial, Music Video, etc.';
COMMENT ON COLUMN productions.year_filmed IS 'When it was filmed (may differ from year_aired)';
COMMENT ON COLUMN productions.year_aired IS 'When it aired or was released to public';

COMMENT ON TABLE locations IS 'Real-world NYC addresses where filming took place';
COMMENT ON COLUMN locations.address IS 'Street address (e.g., "44 W 63rd St, Manhattan")';
COMMENT ON COLUMN locations.borough IS 'NYC borough: Manhattan, Brooklyn, Queens, Bronx, Staten Island';
COMMENT ON COLUMN locations.location_name IS 'Familiar name of location (e.g., "Empire Hotel", "Bethesda Fountain")';

COMMENT ON TABLE filming_events IS 'TIME-SERIES: Records of when/where/what was filmed. Stored as hypertable for performance.';
COMMENT ON COLUMN filming_events.time IS 'Date/time when this was filmed (required for hypertable)';
COMMENT ON COLUMN filming_events.season_episode IS 'Episode reference (S1E5) for TV shows; NULL for films';
COMMENT ON COLUMN filming_events.scene_description IS 'What was filmed (used for semantic search after embeddings added)';
COMMENT ON COLUMN filming_events.scene_embedding IS 'OpenAI embedding vector (add with generate_embeddings.py)';

-- ============================================================================
-- GRANTS (if using separate user accounts)
-- ============================================================================
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

COMMIT;
