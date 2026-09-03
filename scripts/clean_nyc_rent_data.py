#!/usr/bin/env python3
"""
Clean Zillow ZORI (Zip-level rent) data down to NYC's five boroughs and
reshape it from Zillow's wide (one column per month) format into a long
format that maps directly onto a `rent_prices` SQL table.

Usage:
    python scripts/clean_nyc_rent_data.py

Input:
    data/raw/zillow/Zip_zori_uc_sfrcondomfr_sm_month.csv

Output:
    data/processed/nyc_rent_zori.csv
    Columns: zip_code, borough, county_name, period, rent_index
"""

import csv
from pathlib import Path

INPUT_PATH = Path("data/raw/zillow/Zip_zori_uc_sfrcondomfr_sm_month.csv")
OUTPUT_PATH = Path("data/processed/nyc_rent_zori.csv")

# Zillow's CountyName -> NYC borough name (matches permits.borough values)
COUNTY_TO_BOROUGH = {
    "New York County": "Manhattan",
    "Kings County": "Brooklyn",
    "Queens County": "Queens",
    "Bronx County": "Bronx",
    "Richmond County": "Staten Island",
}

NON_DATE_COLUMNS = {
    "RegionID", "SizeRank", "RegionName", "RegionType",
    "StateName", "State", "City", "Metro", "CountyName",
}


def clean():
    if not INPUT_PATH.exists():
        raise SystemExit(f"Missing input file: {INPUT_PATH}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    zips_seen = set()
    periods_seen = set()

    with INPUT_PATH.open(newline="", encoding="utf-8") as f_in, \
         OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f_out:

        reader = csv.DictReader(f_in)
        date_columns = [c for c in reader.fieldnames if c not in NON_DATE_COLUMNS]

        writer = csv.writer(f_out)
        writer.writerow(["zip_code", "borough", "county_name", "period", "rent_index"])

        for row in reader:
            county = row.get("CountyName")
            borough = COUNTY_TO_BOROUGH.get(county)
            if not borough:
                continue  # skip anything outside the 5 boroughs

            zip_code = row["RegionName"].strip()

            for period in date_columns:
                value = row.get(period, "").strip()
                if not value:
                    continue  # Zillow leaves cells blank when data is unavailable
                writer.writerow([zip_code, borough, county, period, value])
                rows_written += 1
                zips_seen.add(zip_code)
                periods_seen.add(period)

    print(f"Wrote {rows_written} rows to {OUTPUT_PATH}")
    print(f"Zip codes covered: {len(zips_seen)}")
    print(f"Period range: {min(periods_seen)} to {max(periods_seen)}")


if __name__ == "__main__":
    clean()
