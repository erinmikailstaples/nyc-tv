# NYC-TV MVP Checklist

Use this to track progress from concept to launch.

---

## Database Setup
- [ ] PostgreSQL installed locally or on Railway
- [ ] PostGIS extension enabled: `CREATE EXTENSION postgis;`
- [ ] Schema created: `psql nyc_tv < schema.sql`
- [ ] Ingestion script installed dependencies: `pip install requests psycopg2-binary`
- [ ] Data ingested: `python scripts/ingest_permits.py` (takes ~30 min)
- [ ] Verify data: `psql nyc_tv -c "SELECT COUNT(*) FROM permits;"`
  - Should show 250k+

---

## Backend API
- [ ] Framework chosen (FastAPI or Express)
- [ ] Database connection working
- [ ] Endpoints implemented:
  - [ ] `GET /api/permits` — List permits with filters
  - [ ] `GET /api/permits/search?q=Friends` — Search by name
  - [ ] `GET /api/permits/{id}` — Get single permit details
  - [ ] `GET /api/boroughs` — List all boroughs (for filter options)
  - [ ] `GET /api/types` — List production types
- [ ] Test endpoints manually with curl or Postman
- [ ] CORS enabled (frontend can call API)
- [ ] Error handling for bad requests
- [ ] Response format is JSON

---

## Frontend Map
- [ ] React project created
- [ ] Mapbox or Deck.gl installed
- [ ] Map component created and displays
- [ ] Mapbox token configured (if using Mapbox)
- [ ] Markers appear on map for permits
- [ ] Click marker shows popup with permit details
- [ ] Search bar exists and updates map
- [ ] Filters work:
  - [ ] Borough dropdown
  - [ ] Production type dropdown
  - [ ] Year range slider
- [ ] Map is responsive (mobile-friendly)

---

## Integration
- [ ] Backend & frontend running locally
- [ ] Frontend can fetch data from backend API
- [ ] Search updates map in real-time
- [ ] Filters update map in real-time
- [ ] No console errors in browser
- [ ] Performance is good (map loads quickly, filters are snappy)

---

## Deployment
- [ ] Backend deployed to Railway or Vercel Functions
- [ ] Frontend deployed to Vercel
- [ ] Database deployed to Railway PostgreSQL
- [ ] Environment variables set correctly (DB URL, Mapbox token, etc.)
- [ ] CORS updated to allow deployed frontend URL
- [ ] Deployed site works end-to-end
- [ ] Data loads on deployed map

---

## Testing & Polish
- [ ] Search works for popular shows (Friends, Succession, etc.)
- [ ] Filters work correctly
- [ ] Map zooms to relevant area on search
- [ ] No UI bugs or layout issues
- [ ] Loading states show while data is fetching
- [ ] Error messages are user-friendly
- [ ] Mobile view looks good (test on phone)

---

## Launch Checklist
- [ ] README.md updated with instructions
- [ ] Live URL works
- [ ] No sensitive data in code (API keys in env vars)
- [ ] Analytics or telemetry added (optional)
- [ ] Share with 5-10 people for feedback
- [ ] Track basic metrics: DAU, search terms, errors

---

## Metrics to Track

Once live, monitor these:

- **Engagement**: How many unique visitors per day?
- **Search**: What shows are people searching for?
- **Errors**: Any API failures or bugs?
- **Performance**: Is the map fast?

---

## Known Limitations (Document for Users)

- Data is from NYC permits only (may miss some productions)
- Permits don't always match exact filming locations (can be approximate)
- No historical photos yet
- No user accounts or favorites yet
- Mobile app coming later

---

## Phase 2 Ideas (Don't Build Yet)

After launch, collect feedback then build:

- Fuzzy search ("Frieds" finds "Friends")
- Popular shows hardcoded (no search needed)
- IMDb links (better metadata)
- Neighborhood stats (top productions per area)
- Export as CSV/GeoJSON
- User contributions (add missing scenes)

---

**Last Updated**: 2026-08-24
