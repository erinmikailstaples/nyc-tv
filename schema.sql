-- NYC-TV MVP Database Schema
-- Initialize with: psql nyc_tv < schema.sql

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS earthdistance;

-- Core permits table
-- Single source of truth for all film permit locations
CREATE TABLE IF NOT EXISTS permits (
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

-- Indexes for MVP queries
CREATE INDEX IF NOT EXISTS idx_permits_production_name
  ON permits (production_name);

CREATE INDEX IF NOT EXISTS idx_permits_borough
  ON permits (borough);

CREATE INDEX IF NOT EXISTS idx_permits_production_type
  ON permits (production_type);

CREATE INDEX IF NOT EXISTS idx_permits_permit_issued_date
  ON permits (permit_issued_date DESC);

-- Geographic index for spatial queries
CREATE INDEX IF NOT EXISTS idx_permits_location
  ON permits USING GIST (ll_to_earth(latitude, longitude));

-- Text search index for better search performance
CREATE INDEX IF NOT EXISTS idx_permits_production_name_tsvector
  ON permits USING GIN (to_tsvector('english', production_name));

-- Create a simple view for API convenience
CREATE OR REPLACE VIEW permits_view AS
  SELECT
    id,
    event_id,
    production_name,
    permit_issued_date,
    permit_expiration_date,
    production_type,
    production_company,
    location_address,
    borough,
    zip_code,
    latitude,
    longitude,
    status,
    ingested_at
  FROM permits
  ORDER BY permit_issued_date DESC;

-- Useful materialized view: Production summary
-- Run this occasionally with: REFRESH MATERIALIZED VIEW CONCURRENTLY production_summary;
CREATE MATERIALIZED VIEW IF NOT EXISTS production_summary AS
  SELECT
    production_name,
    production_type,
    COUNT(*) as permit_count,
    MIN(permit_issued_date) as first_permit_date,
    MAX(permit_issued_date) as last_permit_date,
    COUNT(DISTINCT borough) as boroughs_used,
    ARRAY_AGG(DISTINCT borough ORDER BY borough) as boroughs
  FROM permits
  WHERE production_name IS NOT NULL
  GROUP BY production_name, production_type
  HAVING COUNT(*) > 0
  ORDER BY permit_count DESC;

CREATE INDEX IF NOT EXISTS idx_production_summary_name
  ON production_summary (production_name);
