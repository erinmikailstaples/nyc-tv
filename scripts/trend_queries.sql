-- NYC Filming Locations Trend Analysis Queries
-- Run these to discover patterns in your database
-- Connect first: psql -h host -U user -d dbname -f trend_queries.sql

\echo '🎬 NYC FILMING LOCATIONS TREND ANALYSIS'
\echo '======================================'

-- ============================================================================
-- Query 1: Most Filmed Neighborhoods
-- ============================================================================
\echo ''
\echo '📍 QUERY 1: Most Filmed Neighborhoods'
\echo '======================================'
\echo 'Which neighborhoods have the most filming activity?'
\echo ''

SELECT
  l.neighborhood,
  COUNT(*) as filming_events,
  COUNT(DISTINCT fe.production_id) as unique_productions,
  COUNT(DISTINCT fe.location_id) as unique_locations,
  STRING_AGG(DISTINCT p.title, ' | ') as productions
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
WHERE l.neighborhood IS NOT NULL
GROUP BY l.neighborhood
ORDER BY filming_events DESC
LIMIT 15;

-- ============================================================================
-- Query 2: Borough Breakdown
-- ============================================================================
\echo ''
\echo '🗺️  QUERY 2: Borough Breakdown'
\echo '================================'
\echo 'How is filming distributed across NYC boroughs?'
\echo ''

SELECT
  COALESCE(l.borough, 'Unknown') as borough,
  COUNT(*) as filming_events,
  COUNT(DISTINCT l.id) as unique_locations,
  COUNT(DISTINCT fe.production_id) as unique_productions,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM filming_events), 1) as percentage
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
GROUP BY l.borough
ORDER BY filming_events DESC;

-- ============================================================================
-- Query 3: Location Reuse (Places Used in Multiple Productions)
-- ============================================================================
\echo ''
\echo '♻️  QUERY 3: Highly Reused Locations'
\echo '======================================'
\echo 'Which real-world addresses are used in multiple productions?'
\echo ''

SELECT
  l.location_name,
  l.address,
  l.borough,
  l.neighborhood,
  COUNT(DISTINCT fe.production_id) as production_count,
  STRING_AGG(DISTINCT p.title, ' | ') as productions
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
GROUP BY l.id, l.location_name, l.address, l.borough, l.neighborhood
HAVING COUNT(DISTINCT fe.production_id) > 1
ORDER BY production_count DESC
LIMIT 20;

-- ============================================================================
-- Query 4: Production Categories (Film vs TV vs Commercial)
-- ============================================================================
\echo ''
\echo '🎬 QUERY 4: Production Categories'
\echo '=================================='
\echo 'What types of productions film in NYC?'
\echo ''

SELECT
  COALESCE(p.category, 'Unknown') as category,
  COUNT(*) as filming_events,
  COUNT(DISTINCT p.id) as unique_productions,
  COUNT(DISTINCT fe.location_id) as unique_locations,
  STRING_AGG(DISTINCT p.title, ', ') as example_productions
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
GROUP BY p.category
ORDER BY filming_events DESC;

-- ============================================================================
-- Query 5: Temporal Trends (Filming Over Time)
-- ============================================================================
\echo ''
\echo '📈 QUERY 5: Filming Activity Over Years'
\echo '======================================='
\echo 'How has filming activity changed over time?'
\echo ''

SELECT
  EXTRACT(YEAR FROM fe.time)::INT as year,
  COUNT(*) as filming_events,
  COUNT(DISTINCT fe.production_id) as active_productions,
  COUNT(DISTINCT fe.location_id) as unique_locations
FROM filming_events fe
GROUP BY EXTRACT(YEAR FROM fe.time)
ORDER BY year DESC
LIMIT 20;

-- ============================================================================
-- Query 6: Top Producing Productions (Most Locations Used)
-- ============================================================================
\echo ''
\echo '⭐ QUERY 6: Productions with Most Locations'
\echo '=========================================='
\echo 'Which shows/films use the most different NYC locations?'
\echo ''

SELECT
  p.title,
  p.category,
  p.year_aired,
  COUNT(DISTINCT fe.location_id) as locations_used,
  COUNT(*) as total_filming_events,
  STRING_AGG(DISTINCT l.neighborhood, ', ') as neighborhoods
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
GROUP BY p.id, p.title, p.category, p.year_aired
ORDER BY locations_used DESC
LIMIT 20;

-- ============================================================================
-- Query 7: Street-Level Hotspots
-- ============================================================================
\echo ''
\echo '🎯 QUERY 7: Street-Level Filming Hotspots'
\echo '========================================'
\echo 'Which specific addresses are filmed most frequently?'
\echo ''

SELECT
  l.location_name,
  l.address,
  l.neighborhood,
  COUNT(DISTINCT fe.production_id) as production_count,
  COUNT(*) as filming_events,
  STRING_AGG(DISTINCT p.title, ' | ') as productions
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
WHERE l.address IS NOT NULL
GROUP BY l.id, l.location_name, l.address, l.neighborhood
ORDER BY production_count DESC
LIMIT 25;

-- ============================================================================
-- Query 8: TV Show Analysis (Episodes Breakdown)
-- ============================================================================
\echo ''
\echo '📺 QUERY 8: TV Shows by Season/Episode'
\echo '======================================'
\echo 'How many different locations does each TV show use per episode?'
\echo ''

SELECT
  p.title,
  fe.season_episode,
  COUNT(DISTINCT fe.location_id) as locations_in_episode,
  STRING_AGG(DISTINCT l.neighborhood, ', ') as neighborhoods
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
WHERE fe.season_episode IS NOT NULL
  AND p.category = 'TV'
GROUP BY p.id, p.title, fe.season_episode
ORDER BY p.title, fe.season_episode
LIMIT 50;

-- ============================================================================
-- Query 9: Cross-Borough Production Patterns
-- ============================================================================
\echo ''
\echo '🌐 QUERY 9: Cross-Borough Filming'
\echo '================================='
\echo 'Which productions film across multiple boroughs?'
\echo ''

SELECT
  p.title,
  p.category,
  COUNT(DISTINCT l.borough) as boroughs_used,
  STRING_AGG(DISTINCT l.borough, ', ') as boroughs,
  COUNT(DISTINCT fe.location_id) as total_locations
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
WHERE l.borough IS NOT NULL
GROUP BY p.id, p.title, p.category
HAVING COUNT(DISTINCT l.borough) > 1
ORDER BY boroughs_used DESC, total_locations DESC;

-- ============================================================================
-- Query 10: Icon Production Summary View
-- ============================================================================
\echo ''
\echo '📊 QUERY 10: Database Summary Statistics'
\echo '========================================'
\echo 'Overall database statistics'
\echo ''

SELECT
  (SELECT COUNT(*) FROM productions) as total_productions,
  (SELECT COUNT(*) FROM locations) as total_locations,
  (SELECT COUNT(*) FROM filming_events) as total_events,
  (SELECT COUNT(DISTINCT borough) FROM locations) as boroughs_covered,
  (SELECT COUNT(DISTINCT neighborhood) FROM locations WHERE neighborhood IS NOT NULL) as neighborhoods_covered,
  (SELECT MAX(EXTRACT(YEAR FROM time))::INT FROM filming_events) as most_recent_year
AS summary;

-- ============================================================================
-- Query 11: Manhattan Deep Dive
-- ============================================================================
\echo ''
\echo '🗽 QUERY 11: Manhattan Neighborhoods Ranked'
\echo '=========================================='
\echo 'Most filmed neighborhoods in Manhattan'
\echo ''

SELECT
  l.neighborhood,
  COUNT(*) as filming_events,
  COUNT(DISTINCT fe.production_id) as productions,
  COUNT(DISTINCT fe.location_id) as locations,
  STRING_AGG(DISTINCT p.title, ', ') as example_shows
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
JOIN productions p ON fe.production_id = p.id
WHERE l.borough = 'Manhattan'
GROUP BY l.neighborhood
ORDER BY filming_events DESC;

-- ============================================================================
-- Query 12: "Central Park Problem" - How often is the park used?
-- ============================================================================
\echo ''
\echo '🌳 QUERY 12: Central Park Usage'
\echo '=============================='
\echo 'How many productions film in Central Park?'
\echo ''

SELECT
  p.title,
  p.category,
  p.year_aired,
  fe.season_episode,
  fe.scene_description
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
WHERE l.location_name ILIKE '%central park%'
  OR l.location_name ILIKE '%bethesda%'
  OR l.location_name ILIKE '%conservatory%'
ORDER BY p.year_aired DESC, p.title;

-- ============================================================================
-- BONUS: Create useful views for interactive queries
-- ============================================================================

-- Show current views available
\echo ''
\echo '💾 Available Views:'
\echo '=================='
\dt *.*view*
