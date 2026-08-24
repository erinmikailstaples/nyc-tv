# NYC-TV: Architecture Alternatives (TimescaleDB-Optimized)

This document explores alternative designs that lean harder into **TimescaleDB's unique capabilities** — moving from "generic geospatial DB" to "the killer app for time-series + geospatial data."

---

## Approach 1: Real-Time Production Analytics Dashboard (⭐ Recommended for Showcasing TimescaleDB)

### Vision
Turn NYC-TV into a **live production intelligence platform** — a dashboard showing *right now* what's filming in NYC, historical trends, and predictive insights. TimescaleDB's continuous aggregates + compression make this sing.

### Key TimescaleDB Features Showcased
1. **Continuous Aggregates** (automatic, real-time materialized views)
2. **Time-Bucketing** (aggregate by hour, day, week, borough)
3. **Compression** (store 10 years of hourly data efficiently)
4. **Gap-Filling Functions** (handle missing time periods)
5. **Geospatial + Time-Series** (production density by neighborhood over time)

### Data Model Pivot

```sql
-- Hypertable: Permit "events" (continuous stream)
-- Instead of one row per permit, track permit LIFECYCLE events
CREATE TABLE permit_events (
  time TIMESTAMPTZ NOT NULL,
  permit_id INTEGER,
  event_type VARCHAR,  -- 'issued', 'active', 'completed', 'cancelled'
  production_name VARCHAR,
  borough VARCHAR,
  neighborhood VARCHAR,
  location_geom GEOMETRY(POINT, 4326),
  production_type VARCHAR,
  PRIMARY KEY (time, permit_id, event_type)
) PARTITION BY TIME_RANGE (time INTERVAL '1 day');

-- Enable compression: compress data older than 30 days
ALTER TABLE permit_events SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'borough,production_type'
);

-- Continuous Aggregate: Active productions by hour
CREATE MATERIALIZED VIEW active_productions_1h
WITH (timescaledb.continuous, timescaledb.materialized_only=false)
AS
  SELECT
    time_bucket('1 hour', time) as bucket,
    borough,
    production_type,
    COUNT(DISTINCT permit_id) as count,
    COUNT(DISTINCT location_geom) as unique_locations
  FROM permit_events
  WHERE event_type = 'active'
  GROUP BY bucket, borough, production_type;

-- Continuous Aggregate: Daily neighborhoods
CREATE MATERIALIZED VIEW filming_locations_daily
WITH (timescaledb.continuous, timescaledb.materialized_only=false)
AS
  SELECT
    time_bucket('1 day', time) as bucket,
    borough,
    neighborhood,
    location_geom,
    COUNT(*) as permit_count,
    ARRAY_AGG(DISTINCT production_name) as productions
  FROM permit_events
  WHERE event_type = 'active'
  GROUP BY bucket, borough, neighborhood, location_geom;

-- Compression policy: auto-compress data older than 30 days
SELECT add_compression_policy('permit_events', INTERVAL '30 days');
```

### Frontend: Real-Time Dashboards
```javascript
// Stream live data to React Dashboard
const Dashboard = () => {
  // Endpoint: /api/dashboard/active-now
  // Returns: hourly active productions by borough (pre-aggregated by continuous aggregate)
  
  // Real-time heatmap: updated every 5 minutes
  // Shows current filming hotspots
  
  // Time-series chart: production trends over last 30 days
  // Powered by compressed data + cagg
  
  // Neighborhoods ranked: "Most filmed today", "Week trend", "Year-over-year"
};
```

### Why This Showcases TimescaleDB
✅ **Continuous Aggregates**: Queries hit pre-computed views (millisecond response)  
✅ **Compression**: Store 10 years of hourly data in <100GB  
✅ **Gap Filling**: Answer "which hours had zero productions?"  
✅ **Time-Bucketing**: Slice data by any time granularity instantly  
✅ **Real-Time Analytics**: Dashboard updates without re-computing from raw data

### API Endpoints (All powered by continuous aggregates)
```
GET /api/dashboard/active-now
GET /api/dashboard/borough/{borough}/24h-trend
GET /api/dashboard/neighborhood/{neighborhood}/30d-analysis
GET /api/dashboard/production-type/{type}/year-over-year
GET /api/export/hourly-data?start=2024-01-01&end=2024-12-31&format=csv
```

---

## Approach 2: Multi-Tenant Location Intelligence SaaS (🎯 Advanced TimescaleDB)

### Vision
Position NYC-TV as a **B2B SaaS platform** where location scouts, realtors, and urban planners rent access to production analytics. TimescaleDB's multi-tenant capabilities shine here.

### Key TimescaleDB Features
1. **Distributed Hypertables** (multi-node, horizontal scaling)
2. **Row-level security** (each tenant sees only their data/neighborhoods)
3. **Per-tenant compression policies** (custom retention by client)
4. **Continuous aggregates** (pre-computed analytics per tenant)
5. **Geospatial bulk operations** (fast neighborhood-level rollups)

### Data Model

```sql
-- Multi-tenant schema
CREATE TABLE customers (
  customer_id UUID PRIMARY KEY,
  org_name VARCHAR,
  tier VARCHAR,  -- 'free', 'pro', 'enterprise'
  created_at TIMESTAMPTZ
);

-- Hypertable with tenant segmentation
CREATE TABLE permit_telemetry (
  time TIMESTAMPTZ NOT NULL,
  customer_id UUID NOT NULL,  -- Tenant segmentation
  permit_id INTEGER,
  production_name VARCHAR,
  borough VARCHAR,
  geom GEOMETRY(POINT, 4326),
  PRIMARY KEY (time, customer_id, permit_id)
) PARTITION BY TIME_RANGE (time INTERVAL '1 day');

-- Row-level security: each tenant sees only their rows
CREATE POLICY customer_isolation ON permit_telemetry
  USING (customer_id = current_setting('app.current_customer_id')::uuid);

-- Continuous Aggregate per tenant (filtered automatically)
CREATE MATERIALIZED VIEW customer_production_summary_daily
WITH (timescaledb.continuous)
AS
  SELECT
    time_bucket('1 day', time) as day,
    customer_id,
    COUNT(DISTINCT permit_id) as permits_issued,
    COUNT(DISTINCT borough) as boroughs_active
  FROM permit_telemetry
  GROUP BY day, customer_id;

-- Compression: free tier compresses after 7 days, enterprise after 90 days
SELECT add_compression_policy(
  'permit_telemetry',
  INTERVAL '7 days',
  if_not_exists => true
) WHERE tier = 'free';
```

### Billing & Metering
```sql
-- Automatic usage tracking via continuous aggregate
CREATE MATERIALIZED VIEW customer_usage_metrics
WITH (timescaledb.continuous)
AS
  SELECT
    time_bucket('1 day', time) as day,
    customer_id,
    COUNT(*) as queries_run,
    SUM(1) as data_points_accessed
  FROM permit_telemetry
  GROUP BY day, customer_id;

-- Queries:
-- - Pro plan: $50/mo, 5k queries/mo
-- - Enterprise: $500/mo, unlimited
```

### Why This Showcases TimescaleDB
✅ **Distributed Hypertables**: Scale horizontally as customers grow  
✅ **Row-Level Security**: Built-in multi-tenancy without app-layer complexity  
✅ **Per-Customer Policies**: Different retention/compression for different tiers  
✅ **Usage Metering**: Continuous aggregates power billing dashboards  
✅ **Scaling Story**: "We went from 1 to 1,000 customers without changing queries"

---

## Approach 3: Historical Event Stream + Streaming Analytics (📊 Real-Time Ingest)

### Vision
Ingest **live permit feeds** as events (permits issued, updated, cancelled), perform real-time analytics, and backfill historical data. TimescaleDB + Kafka showcase its streaming strength.

### Key TimescaleDB Features
1. **High-throughput ingest** (bulk insert 1k events/sec)
2. **Upsert semantics** (permit updates don't duplicate)
3. **Immediate aggregation** (continuous aggregates update as data lands)
4. **Retention policies** (automatically archive to cold storage)
5. **Geospatial joins** (correlate streaming permits with neighborhoods instantly)

### Architecture

```
Kafka (NYC Permit Stream) 
  ↓
Python Consumer (FastAPI background)
  ↓
TimescaleDB (Hypertable: permit_events)
  ↓ (via continuous aggregates)
Redis Cache (hot stats)
  ↓
React Dashboard (real-time)
```

### Schema Optimized for Streaming

```sql
-- Ultra-fast ingest hypertable
CREATE TABLE permit_stream (
  time TIMESTAMPTZ NOT NULL,
  permit_id INTEGER NOT NULL,
  event_type VARCHAR NOT NULL,  -- 'created', 'updated', 'closed'
  production_name VARCHAR,
  borough VARCHAR,
  geom GEOMETRY(POINT, 4326),
  raw_json JSONB,  -- Store full permit data for later analysis
  PRIMARY KEY (time, permit_id, event_type)
) PARTITION BY TIME_RANGE (time INTERVAL '1 hour');

-- Continuous Aggregate: Real-time borough heatmap
CREATE MATERIALIZED VIEW borough_activity_5m
WITH (timescaledb.continuous, timescaledb.materialized_only=false)
AS
  SELECT
    time_bucket('5 minutes', time) as bucket,
    borough,
    COUNT(*) as events,
    COUNT(DISTINCT permit_id) as unique_permits,
    ST_ClusterDBSCAN(geom, 100, 1) OVER (PARTITION BY borough) as cluster_id
  FROM permit_stream
  WHERE time > NOW() - INTERVAL '24 hours'
  GROUP BY bucket, borough;

-- Retention policy: keep raw stream for 90 days, then archive
SELECT add_retention_policy('permit_stream', INTERVAL '90 days');

-- Compression: compress after 3 days
SELECT add_compression_policy('permit_stream', INTERVAL '3 days');
```

### Python Kafka Consumer

```python
from kafka import KafkaConsumer
from timescaledb import insert_batch
import json

consumer = KafkaConsumer('nyc-permits', bootstrap_servers=['localhost:9092'])

batch = []
for message in consumer:
    permit_event = json.loads(message.value)
    batch.append({
        'time': permit_event['timestamp'],
        'permit_id': permit_event['id'],
        'event_type': permit_event['type'],
        'production_name': permit_event['production'],
        'borough': permit_event['borough'],
        'geom': f"POINT({permit_event['lon']} {permit_event['lat']})",
        'raw_json': permit_event
    })
    
    if len(batch) >= 1000:
        insert_batch('permit_stream', batch)  # Bulk insert for speed
        batch = []
```

### Frontend: Live Activity Feed
```javascript
// Real-time websocket connection
const LiveDashboard = () => {
  // Endpoint: /api/live/borough-activity?interval=5m
  // Source: borough_activity_5m (refreshed by TimescaleDB, not us)
  
  return (
    <Map
      heatmap={updateEvery(5_minutes)}  // Hot data from continuous aggregate
      overlay={realTimePins}  // Newest 100 permits
    />
  );
};
```

### Why This Showcases TimescaleDB
✅ **High-Throughput Ingest**: Handle 1k events/sec without queuing  
✅ **Upsert Support**: Permit update → same row, no duplicates  
✅ **Streaming Analytics**: Continuous aggregates update in real-time  
✅ **Retention Policies**: Auto-delete old data, compress warm data  
✅ **Geospatial + Events**: Cluster permits by location as they arrive

---

## Approach 4: Time-Travel + Historical Simulation (🔮 Advanced Queries)

### Vision
Let users **time-travel** — "Show me what was filming in NYC in 2015" or "Predict where next season will film." TimescaleDB's time-series functions enable this beautifully.

### Key TimescaleDB Features
1. **Time-bucketing functions** (slice by any granularity)
2. **LAG/LEAD window functions** (compare year-over-year)
3. **Gap-filling** (smooth out missing weeks)
4. **First/Last aggregates** (when did filming in a neighborhood peak?)
5. **Time-weighted averages** (production density over time)

### Schema

```sql
-- Historical permit hypertable
CREATE TABLE permits_history (
  time TIMESTAMPTZ NOT NULL,
  permit_id INTEGER,
  production_name VARCHAR,
  borough VARCHAR,
  neighborhood VARCHAR,
  production_type VARCHAR,
  geom GEOMETRY(POINT, 4326),
  PRIMARY KEY (time, permit_id)
) PARTITION BY TIME_RANGE (time INTERVAL '1 year');

-- Query 1: Year-over-year comparison
-- "Filming in Brooklyn: 2023 vs 2024"
SELECT
  time_bucket('1 month', time) as month,
  COUNT(*) as permits,
  LAG(COUNT(*)) OVER (ORDER BY time_bucket('1 month', time)) as prev_year_permits,
  ROUND(100.0 * (COUNT(*) - LAG(COUNT(*)) OVER (...)) / LAG(COUNT(*)) OVER (...), 2) as yoy_growth
FROM permits_history
WHERE borough = 'Brooklyn'
  AND time >= '2023-01-01'::timestamptz
GROUP BY month
ORDER BY month;

-- Query 2: Neighborhood popularity trend (smoothed)
-- "Which neighborhoods had the most production in Q1 each year?"
WITH smoothed AS (
  SELECT
    time_bucket('1 quarter', time) as quarter,
    neighborhood,
    COUNT(*) as permits,
    -- Fill gaps if neighborhood had zero permits that quarter
    COALESCE(COUNT(*), 0) as permits_filled
  FROM permits_history
  WHERE borough = 'Brooklyn'
  GROUP BY quarter, neighborhood
)
SELECT
  quarter,
  neighborhood,
  permits_filled,
  ROW_NUMBER() OVER (PARTITION BY quarter ORDER BY permits_filled DESC) as rank
FROM smoothed
WHERE rank <= 5;

-- Query 3: First/Last aggregates
-- "When did each neighborhood's production boom START?"
SELECT
  neighborhood,
  MIN(time) as first_permit,
  MAX(time) as last_permit,
  DATE_TRUNC('year', MIN(time)) as boom_year,
  COUNT(*) as total_permits
FROM permits_history
WHERE COUNT(*) > 50  -- Active neighborhoods only
GROUP BY neighborhood
ORDER BY first_permit DESC;

-- Query 4: Gap-filling (answer "why was there no filming in March?")
WITH time_range AS (
  SELECT generate_series(
    '2020-01-01'::timestamptz,
    '2024-12-31'::timestamptz,
    '1 month'::interval
  ) as month
)
SELECT
  tr.month,
  COALESCE(ph.count, 0) as permits,
  CASE
    WHEN COALESCE(ph.count, 0) = 0 THEN 'LOW'
    WHEN COALESCE(ph.count, 0) BETWEEN 1 AND 10 THEN 'MEDIUM'
    ELSE 'HIGH'
  END as activity_level,
  LAG(COALESCE(ph.count, 0)) OVER (ORDER BY tr.month) as prev_month
FROM time_range tr
LEFT JOIN (
  SELECT
    time_bucket('1 month', time) as bucket,
    COUNT(*) as count
  FROM permits_history
  GROUP BY bucket
) ph ON tr.month = ph.bucket
ORDER BY tr.month;
```

### Frontend: Time-Travel Interface

```javascript
const TimeTravel = () => {
  const [year, setYear] = useState(2024);
  const [neighborhood, setNeighborhood] = useState('Manhattan');
  
  // Query: Show all permits + activity in [neighborhood] for [year]
  const data = useQuery(`/api/timeline/${neighborhood}/${year}`);
  
  // Display:
  // - Timeline slider: drag through 2000-2026
  // - Map shows historical permits
  // - Chart: year-over-year comparison
  // - Prediction: "Based on trend, 2025 will have +15% more filming"
  
  return (
    <>
      <Slider value={year} onChange={setYear} min={2000} max={2026} />
      <Map permits={data.permits} />
      <Chart data={data.yearOverYear} />
      <Prediction trend={data.forecast} />
    </>
  );
};
```

### Why This Showcases TimescaleDB
✅ **Time-Bucketing**: "Group by quarter" or "by week" instantly  
✅ **Window Functions**: Year-over-year comparisons without joins  
✅ **Gap-Filling**: Answer "why not" questions  
✅ **First/Last Aggregates**: Understand neighborhood lifecycle  
✅ **Historical Analysis**: 20+ years of data, responsive queries

---

## Approach 5: Geospatial + Time-Series: Hyper-Local Analytics (🗺️ GIS Integration)

### Vision
Combine **geospatial queries** with **time-series** to answer: "Which neighborhoods have the most consistent year-round filming?" or "Production density correlates with population density?"

### Key TimescaleDB Features
1. **Geospatial aggregation** (ST_Union neighborhoods, ST_Buffer for radius)
2. **Continuous aggregates on geometry** (pre-computed neighborhood stats)
3. **Time-series + spatial joins** (link permits with neighborhood polygons over time)
4. **Kriging/interpolation** (estimate filming density on unmapped areas)

### Schema

```sql
-- Neighborhood reference (static)
CREATE TABLE neighborhoods (
  id SERIAL PRIMARY KEY,
  name VARCHAR UNIQUE,
  borough VARCHAR,
  geom GEOMETRY(POLYGON, 4326),
  population_2020 INTEGER,
  median_income INTEGER,
  created_at TIMESTAMPTZ
);

-- Hypertable: permits with neighborhood association
CREATE TABLE permits_by_neighborhood (
  time TIMESTAMPTZ NOT NULL,
  permit_id INTEGER,
  neighborhood_id INTEGER REFERENCES neighborhoods(id),
  production_name VARCHAR,
  geom GEOMETRY(POINT, 4326),
  PRIMARY KEY (time, permit_id)
) PARTITION BY TIME_RANGE (time INTERVAL '1 year');

-- Create spatial index for fast neighborhood lookups
CREATE INDEX ON permits_by_neighborhood USING GIST (geom);

-- Continuous Aggregate: Neighborhood heatmap (daily)
CREATE MATERIALIZED VIEW neighborhood_production_daily
WITH (timescaledb.continuous, timescaledb.materialized_only=false)
AS
  SELECT
    time_bucket('1 day', time) as day,
    pbn.neighborhood_id,
    n.name,
    n.geom,
    COUNT(*) as daily_permits,
    COUNT(DISTINCT pbn.permit_id) as unique_productions,
    ST_Collect(pbn.geom) as permit_locations
  FROM permits_by_neighborhood pbn
  JOIN neighborhoods n ON pbn.neighborhood_id = n.id
  GROUP BY day, pbn.neighborhood_id, n.name, n.geom;

-- Continuous Aggregate: Seasonal trends (which neighborhoods are "summer hotspots"?)
CREATE MATERIALIZED VIEW seasonal_neighborhood_patterns
WITH (timescaledb.continuous)
AS
  SELECT
    DATE_TRUNC('quarter', time) as quarter,
    neighborhood_id,
    COUNT(*) as quarterly_permits,
    ROUND(AVG(daily_permits), 2) as avg_daily_activity
  FROM permits_by_neighborhood
  GROUP BY quarter, neighborhood_id;

-- Query: Neighborhoods with consistent filming (variance analysis)
SELECT
  n.name,
  COUNT(DISTINCT EXTRACT(YEAR FROM time)) as years_with_filming,
  STDDEV(COUNT(*)) as variance,
  AVG(COUNT(*)) as avg_annual_permits,
  CASE
    WHEN STDDEV(COUNT(*)) < 5 THEN 'CONSISTENT'
    WHEN STDDEV(COUNT(*)) < 20 THEN 'MODERATE'
    ELSE 'VOLATILE'
  END as activity_pattern
FROM permits_by_neighborhood pbn
JOIN neighborhoods n ON pbn.neighborhood_id = n.id
WHERE EXTRACT(YEAR FROM time) >= 2015
GROUP BY n.id, n.name
ORDER BY activity_pattern, avg_annual_permits DESC;

-- Query: Production "hot zones" (radius around popular locations)
-- "Which 3-block radius has the most filming?"
SELECT
  ST_Buffer(
    (SELECT geom FROM permits_by_neighborhood WHERE permit_id = MAX(permit_id)),
    0.0045  -- ~500 meters in lat/lon
  ) as hotzone,
  COUNT(*) as permits_nearby,
  ARRAY_AGG(DISTINCT production_name) as productions
FROM permits_by_neighborhood
WHERE ST_DWithin(
  geom,
  (SELECT geom FROM permits_by_neighborhood WHERE permit_id = MAX(permit_id)),
  0.0045
)
GROUP BY hotzone
ORDER BY permits_nearby DESC;
```

### Visualization: Heatmap + Time-Series

```javascript
const GeoTemporal = () => {
  // Left: Geospatial heatmap (neighborhood density)
  // Right: Time-series (activity over decades)
  
  // Query: /api/geo-temporal/neighborhood/{id}/complete-history
  // Returns: daily permits + neighborhood polygon + seasonal patterns
  
  return (
    <SplitView>
      <GeoMap
        neighborhoods={data.geoms}
        heatmapValues={data.daily_permits}  // From continuous aggregate
        onClick={selected => setSelected(selected)}
      />
      <TimeSeriesChart
        data={data.yearly_trends}
        forecast={data.prediction}
      />
    </SplitView>
  );
};
```

### Why This Showcases TimescaleDB
✅ **Geospatial + Time-Series**: The killer combo (not many DBs do both)  
✅ **ST_Buffer/ST_DWithin**: Radius queries on streaming data  
✅ **Continuous Aggregates on Geometry**: Pre-computed polygons  
✅ **Window Functions + Spatial**: Variance analysis per neighborhood over time  
✅ **Scalability**: 20 years × 50k permits × neighborhoods, instant queries

---

## Comparison Matrix

| Approach | Best For | TimescaleDB Stars | Effort | ROI |
|----------|----------|-------------------|--------|-----|
| **1: Real-Time Analytics Dashboard** | Showcasing caggs + compression | ⭐⭐⭐⭐⭐ | Medium | High visibility |
| **2: Multi-Tenant SaaS** | Enterprise positioning | ⭐⭐⭐⭐ | High | Revenue potential |
| **3: Streaming Analytics** | Kafka + real-time ingest | ⭐⭐⭐⭐⭐ | High | Technical depth |
| **4: Time-Travel UI** | Historical analysis + ML | ⭐⭐⭐⭐ | Medium | User engagement |
| **5: Geospatial + Time-Series** | GIS integration | ⭐⭐⭐⭐⭐ | High | Data science appeal |

---

## Recommendation

**Hybrid Approach** (Approaches 1 + 4 + 5):
- **Phase 1**: Real-time dashboard (Approach 1) — shows continuous aggregates power
- **Phase 2**: Add time-travel slider (Approach 4) — showcases time-series functions
- **Phase 3**: Geospatial analysis (Approach 5) — closes the loop on ST_* functions

This tells the **complete TimescaleDB story**:
- ✅ High-throughput ingest
- ✅ Real-time aggregation
- ✅ Historical time-series analytics
- ✅ Geospatial + temporal queries
- ✅ Compression & retention

**Marketing angle**: "The platform that proves TimescaleDB handles enterprise-scale geospatial time-series analytics."

---

**Document Version**: 1.0  
**For questions**: erin@tigerdata.com
