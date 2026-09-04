-- NYC Film Locations: Three-Layer Queries
-- Demonstrates how curated data + TimescaleDB + official permits work together
--
-- LAYER 1: Your curated data (films, TV shows, locations)
-- LAYER 2: TimescaleDB (time-series analysis, trends, semantic search prep)
-- LAYER 3: Official permits (validation, enrichment, discovery)

\echo '🎬 THREE-LAYER ARCHITECTURE QUERIES'
\echo '===================================='

-- ============================================================================
-- Query 1: Iconic Locations + Official Permits
-- ============================================================================
\echo ''
\echo '✅ QUERY 1: Iconic Locations With Official Permits'
\echo '================================================'
\echo 'Shows classic filming locations that have official permits'
\echo ''

SELECT
  p.title,
  p.year_aired,
  l.location_name,
  l.address,
  l.borough,
  COUNT(DISTINCT nop.event_id) as official_permits,
  MIN(nop.start_date) as first_permit,
  MAX(nop.end_date) as latest_permit,
  CASE
    WHEN COUNT(DISTINCT nop.event_id) > 0 THEN '🔴 STILL FILMING'
    ELSE '⚪ HISTORIC ONLY'
  END as status
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
LEFT JOIN nyc_official_permits nop
  ON (LOWER(l.address) LIKE LOWER(nop.location)
      OR LOWER(nop.production_company) LIKE LOWER(p.title) || '%')
WHERE p.year_aired < 2015  -- Classic films
GROUP BY p.id, p.title, p.year_aired, l.id, l.location_name, l.address, l.borough
HAVING COUNT(DISTINCT nop.event_id) > 0
ORDER BY official_permits DESC, p.year_aired DESC
LIMIT 15;

-- ============================================================================
-- Query 2: Coverage Analysis (How Good Is Your Data?)
-- ============================================================================
\echo ''
\echo '📊 QUERY 2: Coverage Analysis'
\echo '=============================='
\echo 'Compares your curated data vs official permits'
\echo ''

WITH curated_summary AS (
  SELECT
    COUNT(DISTINCT p.id) as curated_productions,
    COUNT(DISTINCT l.id) as curated_locations,
    COUNT(*) as curated_events,
    COUNT(DISTINCT l.borough) as curated_boroughs
  FROM filming_events fe
  JOIN productions p ON fe.production_id = p.id
  JOIN locations l ON fe.location_id = l.id
),
official_summary AS (
  SELECT
    COUNT(DISTINCT LOWER(production_company)) as official_productions,
    COUNT(DISTINCT location) as official_locations,
    COUNT(*) as official_permits,
    COUNT(DISTINCT borough) as official_boroughs
  FROM nyc_official_permits
  WHERE start_date >= CURRENT_DATE - INTERVAL '365 days'
)
SELECT
  (SELECT curated_productions FROM curated_summary)::TEXT || ' productions' as "Curated Data",
  (SELECT official_productions FROM official_summary)::TEXT || ' productions' as "Official Permits (Last Year)",
  (SELECT curated_locations FROM curated_summary)::TEXT || ' locations' as "Your Locations",
  (SELECT official_locations FROM official_summary)::TEXT || ' locations' as "Official Locations";

-- ============================================================================
-- Query 3: Find New Productions from Official Data
-- ============================================================================
\echo ''
\echo '🔍 QUERY 3: New Productions In Official Permits'
\echo '=============================================='
\echo 'Permits that arent yet in your curated data'
\echo ''

SELECT
  nop.event_id,
  nop.production_company,
  nop.event_type,
  nop.location,
  nop.borough,
  nop.start_date,
  nop.end_date,
  (nop.end_date - nop.start_date + 1) as filming_days,
  CASE
    WHEN p.id IS NOT NULL THEN '✅ IN DATABASE'
    ELSE '🆕 NEW - Consider Adding'
  END as in_curated_data
FROM nyc_official_permits nop
LEFT JOIN productions p
  ON LOWER(p.title) LIKE LOWER('%' || TRIM(nop.production_company) || '%')
WHERE nop.start_date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY nop.start_date DESC
LIMIT 20;

-- ============================================================================
-- Query 4: Validation Report (Data Quality)
-- ============================================================================
\echo ''
\echo '🔎 QUERY 4: Data Validation Report'
\echo '================================='
\echo 'Shows which curated locations match official permits'
\echo ''

WITH matched AS (
  SELECT
    l.id,
    p.title,
    l.location_name,
    l.address,
    COUNT(DISTINCT nop.event_id) as matching_permits
  FROM filming_events fe
  JOIN productions p ON fe.production_id = p.id
  JOIN locations l ON fe.location_id = l.id
  LEFT JOIN nyc_official_permits nop
    ON (LOWER(l.address) LIKE LOWER(nop.location)
        OR LOWER(nop.production_company) LIKE LOWER(p.title) || '%')
  WHERE nop.event_id IS NOT NULL
  GROUP BY l.id, p.title, l.location_name, l.address
)
SELECT
  COUNT(*) as locations_with_permits,
  COUNT(*) FILTER (WHERE matching_permits >= 3) as heavily_used,
  COUNT(*) FILTER (WHERE matching_permits = 1) as single_permit,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(DISTINCT l.id) FROM locations), 1) as percent_validated
FROM matched;

-- ============================================================================
-- Query 5: Trending Neighborhoods (Curated vs Official)
-- ============================================================================
\echo ''
\echo '📈 QUERY 5: Neighborhood Trends'
\echo '=============================='
\echo 'Which neighborhoods are trending (curated data)?'
\echo ''

SELECT
  l.neighborhood,
  COUNT(DISTINCT fe.production_id) as curated_productions,
  (SELECT COUNT(DISTINCT production_company)
   FROM nyc_official_permits
   WHERE LOWER(location) LIKE LOWER('%' || l.neighborhood || '%')
   AND start_date >= CURRENT_DATE - INTERVAL '90 days'
  ) as recent_official_permits,
  CASE
    WHEN (SELECT COUNT(DISTINCT production_company)
          FROM nyc_official_permits
          WHERE LOWER(location) LIKE LOWER('%' || l.neighborhood || '%')
          AND start_date >= CURRENT_DATE - INTERVAL '90 days'
         ) > 5 THEN '🔴 HOT - Lots of activity'
    WHEN COUNT(DISTINCT fe.production_id) > 5 THEN '🟠 WARM - Popular'
    ELSE '⚪ COOL - Less frequent'
  END as trend
FROM filming_events fe
JOIN locations l ON fe.location_id = l.id
WHERE l.neighborhood IS NOT NULL
GROUP BY l.neighborhood
ORDER BY COUNT(DISTINCT fe.production_id) DESC
LIMIT 20;

-- ============================================================================
-- Query 6: Authority Check (Official vs Curated Discrepancies)
-- ============================================================================
\echo ''
\echo '⚠️  QUERY 6: Data Discrepancies'
\echo '=============================='
\echo 'Curated locations with NO official permits'
\echo ''

SELECT
  l.location_name,
  l.address,
  l.borough,
  COUNT(DISTINCT fe.production_id) as films_claimed,
  STRING_AGG(DISTINCT p.title, ', ') as productions,
  CASE
    WHEN COUNT(DISTINCT fe.production_id) = 1 THEN '⚠️  UNVERIFIED - Only 1 film'
    WHEN COUNT(DISTINCT fe.production_id) <= 3 THEN '🟡 LIMITED - Few films'
    WHEN COUNT(DISTINCT fe.production_id) > 3 THEN '🟢 VERIFIED - Multiple sources'
  END as confidence
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
LEFT JOIN nyc_official_permits nop
  ON (LOWER(l.address) LIKE LOWER(nop.location)
      OR LOWER(nop.production_company) LIKE LOWER(p.title) || '%')
WHERE nop.event_id IS NULL  -- No official permit found
GROUP BY l.id, l.location_name, l.address, l.borough
ORDER BY COUNT(DISTINCT fe.production_id) DESC;

-- ============================================================================
-- Query 7: "Golden Locations" (Historic + Currently Filming)
-- ============================================================================
\echo ''
\echo '🏆 QUERY 7: Golden Locations'
\echo '============================='
\echo 'Classic locations that are STILL being used'
\echo ''

SELECT
  l.location_name,
  l.address,
  l.borough,
  COUNT(DISTINCT CASE WHEN p.year_aired < 2015 THEN p.id END) as historic_productions,
  COUNT(DISTINCT CASE WHEN p.year_aired >= 2015 THEN p.id END) as modern_productions,
  (SELECT MAX(start_date) FROM nyc_official_permits nop
   WHERE LOWER(l.address) LIKE LOWER(nop.location)) as latest_permit_date,
  '⭐ ICONIC & ACTIVE' as significance
FROM filming_events fe
JOIN productions p ON fe.production_id = p.id
JOIN locations l ON fe.location_id = l.id
GROUP BY l.id, l.location_name, l.address, l.borough
HAVING COUNT(DISTINCT CASE WHEN p.year_aired < 2015 THEN p.id END) > 0
  AND COUNT(DISTINCT CASE WHEN p.year_aired >= 2015 THEN p.id END) > 0
ORDER BY COUNT(DISTINCT CASE WHEN p.year_aired < 2015 THEN p.id END) DESC;

-- ============================================================================
-- Query 8: Real-Time Discovery (What's Filming Right Now?)
-- ============================================================================
\echo ''
\echo '🎥 QUERY 8: What\'s Filming Right Now'
\echo '======================================'
\echo 'Active productions from official permits'
\echo ''

SELECT
  nop.production_company,
  nop.event_type,
  nop.location,
  nop.borough,
  nop.start_date,
  nop.end_date,
  (nop.end_date - CURRENT_DATE) as days_remaining,
  CASE
    WHEN nop.end_date < CURRENT_DATE THEN '✅ COMPLETED'
    WHEN nop.start_date <= CURRENT_DATE AND nop.end_date >= CURRENT_DATE THEN '🔴 FILMING NOW'
    WHEN nop.start_date > CURRENT_DATE THEN '🟠 UPCOMING'
  END as status,
  CASE
    WHEN p.id IS NOT NULL THEN '✅ In our database'
    ELSE '🆕 Not yet curated'
  END as in_database
FROM nyc_official_permits nop
LEFT JOIN productions p
  ON LOWER(p.title) LIKE LOWER('%' || TRIM(nop.production_company) || '%')
WHERE (nop.start_date <= CURRENT_DATE + INTERVAL '30 days'
       AND nop.end_date >= CURRENT_DATE - INTERVAL '7 days')
ORDER BY nop.start_date DESC;

-- ============================================================================
-- Summary: The Three Layers Working Together
-- ============================================================================
\echo ''
\echo '📊 SUMMARY: Three Layers'
\echo '======================='
\echo ''
\echo 'LAYER 1 (Your Curated Data):'
WITH layer1 AS (
  SELECT
    COUNT(DISTINCT p.id) as productions,
    COUNT(DISTINCT l.id) as locations,
    MIN(p.year_aired) as earliest_year,
    MAX(p.year_aired) as latest_year
  FROM filming_events fe
  JOIN productions p ON fe.production_id = p.id
  JOIN locations l ON fe.location_id = l.id
)
SELECT '  - ' || productions || ' productions from ' || earliest_year || ' to ' || latest_year FROM layer1
UNION ALL
SELECT '  - ' || locations || ' curated locations' FROM layer1;

\echo ''
\echo 'LAYER 2 (TimescaleDB):'
\echo '  - Stores, indexes, and queries all data'
\echo '  - Enables time-series trend analysis'
\echo '  - Prepares for semantic search (embeddings)'

\echo ''
\echo 'LAYER 3 (Official Permits):'
WITH layer3 AS (
  SELECT COUNT(*) as permits, COUNT(DISTINCT borough) as boroughs
  FROM nyc_official_permits
  WHERE start_date >= CURRENT_DATE - INTERVAL '365 days'
)
SELECT '  - ' || permits || ' official permits in last year' FROM layer3
UNION ALL
SELECT '  - ' || boroughs || ' boroughs covered' FROM layer3;

\echo ''
\echo '✅ All three layers working together for authority + details + trends'
\echo ''
