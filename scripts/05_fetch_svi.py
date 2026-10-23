"""
Step 3: FEMA/CDC Social Vulnerability Index (SVI), county level, for the
Gulf Coast states.

Note on naming: the team roles doc calls this "FEMA SVI," but it's actually
published by CDC/ATSDR -- FEMA just links to it on fema.gov. Same dataset
either way.

Source: CDC/ATSDR SVI 2022, county-level FeatureServer (verified live):
  https://onemap.cdc.gov/onemapservices/rest/services/SVI/CDC_ATSDR_Social_Vulnerability_Index_2022_USA/FeatureServer/1

This is an ArcGIS REST service, not a flat file -- it caps how many records
it returns per request ("exceededTransferLimit"), so this script pages
through with resultOffset until everything's been pulled, same idea as the
$skip pagination in the FEMA disaster-declarations script.

Output:
  processed/svi_gulf_coast_counties.csv
  -- one row per county, key columns: STATE, ST_ABBR, STCNTY (5-digit FIPS,
     matches the county_fips column from the FEMA disaster script),
     COUNTY, E_TOTPOP, RPL_THEME1-4, RPL_THEMES (overall vulnerability
     percentile rank, 0=least vulnerable, 1=most vulnerable)
"""

import os
import time
import urllib.parse
import urllib.request
import json

import pandas as pd

GULF_STATES = ["Texas", "Louisiana", "Mississippi", "Alabama", "Florida"]

BASE_URL = (
    "https://onemap.cdc.gov/onemapservices/rest/services/SVI/"
    "CDC_ATSDR_Social_Vulnerability_Index_2022_USA/FeatureServer/1/query"
)

# The columns we actually need -- skip the ~150 raw estimate/margin-of-error
# columns and keep identity + the ranked percentile scores the model/dashboard
# will actually use.
OUT_FIELDS = [
    "STATE", "ST_ABBR", "STCNTY", "COUNTY", "FIPS", "LOCATION",
    "AREA_SQMI", "E_TOTPOP",
    "RPL_THEME1", "RPL_THEME2", "RPL_THEME3", "RPL_THEME4", "RPL_THEMES",
]

PAGE_SIZE = 1000
OUT_PATH = "processed/svi_gulf_coast_counties.csv"


def fetch_page(offset: int) -> tuple[list[dict], bool]:
    state_list = ",".join(f"'{s}'" for s in GULF_STATES)
    params = {
        "where": f"STATE IN ({state_list})",
        "outFields": ",".join(OUT_FIELDS),
        "f": "json",
        "returnGeometry": "false",
        "resultRecordCount": PAGE_SIZE,
        "resultOffset": offset,
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "capstone-data-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if "error" in payload:
        raise RuntimeError(f"SVI API error: {payload['error']}")

    features = payload.get("features", [])
    exceeded = payload.get("exceededTransferLimit", False)
    return [f["attributes"] for f in features], exceeded


def main():
    print("Downloading SVI 2022 county data for the Gulf Coast states ...")
    all_rows = []
    offset = 0
    while True:
        rows, exceeded = fetch_page(offset)
        if not rows:
            break
        all_rows.extend(rows)
        print(f"  fetched {len(all_rows):,} counties so far")
        if not exceeded and len(rows) < PAGE_SIZE:
            break  # got everything
        offset += PAGE_SIZE
        time.sleep(0.3)

    if not all_rows:
        raise RuntimeError(
            "No SVI records returned -- check the service is reachable and "
            "the state names / where clause still match the live schema."
        )

    df = pd.DataFrame(all_rows).drop_duplicates(subset=["STCNTY"])
    df["STCNTY"] = df["STCNTY"].astype(str).str.zfill(5)  # 5-digit county FIPS

    os.makedirs("processed", exist_ok=True)
    df.to_csv(OUT_PATH, index=False)

    print(f"\nSaved {len(df):,} counties -> {OUT_PATH}")
    print("\nCounties by state:")
    print(df["ST_ABBR"].value_counts())
    print("\nOverall vulnerability (RPL_THEMES) distribution:")
    print(df["RPL_THEMES"].describe())


if __name__ == "__main__":
    main()
