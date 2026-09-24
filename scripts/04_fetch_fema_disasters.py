"""
Step 2: FEMA Disaster Declarations for the Gulf Coast states -- these become
the model's risk labels (a disaster was/wasn't declared for a given
county/date), per the team's handoff list.

Source: OpenFEMA REST API, "Disaster Declarations Summaries v2"
  https://www.fema.gov/about/openfema/api
  Base URL pattern: https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries

No API key needed. Paginates through all matching records via $top/$skip.

Output:
  processed/fema_disaster_declarations_gulf_coast.csv
  -- one row per declared disaster per county, with a 5-digit FIPS column
     (fipsStateCode + fipsCountyCode) for joining to station/county data later.
"""

import os
import time
import urllib.parse
import urllib.request
import json

import pandas as pd

GULF_STATES = ["TX", "LA", "MS", "AL", "FL"]

BASE_URL = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
PAGE_SIZE = 1000  # OpenFEMA default/safe page size (max allowed is 10,000)

FIELDS = [
    "disasterNumber", "state", "declarationType", "declarationDate",
    "fyDeclared", "incidentType", "declarationTitle", "incidentBeginDate",
    "incidentEndDate", "designatedArea", "fipsStateCode", "fipsCountyCode",
]

OUT_PATH = "processed/fema_disaster_declarations_gulf_coast.csv"


def fetch_page(state_filter: str, skip: int) -> list[dict]:
    params = {
        "$filter": state_filter,
        "$select": ",".join(FIELDS),
        "$top": PAGE_SIZE,
        "$skip": skip,
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "capstone-data-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("DisasterDeclarationsSummaries", [])


def fetch_all_for_state(state: str) -> list[dict]:
    state_filter = f"state eq '{state}'"
    records = []
    skip = 0
    while True:
        page = fetch_page(state_filter, skip)
        if not page:
            break
        records.extend(page)
        print(f"  {state}: fetched {len(records):,} records so far")
        if len(page) < PAGE_SIZE:
            break  # last page
        skip += PAGE_SIZE
        time.sleep(0.3)  # be polite to the API
    return records


def main():
    all_records = []
    for state in GULF_STATES:
        print(f"Fetching disaster declarations for {state} ...")
        all_records.extend(fetch_all_for_state(state))

    if not all_records:
        raise RuntimeError(
            "No records returned for any Gulf Coast state -- check the API is reachable "
            "and the $filter syntax hasn't changed."
        )

    df = pd.DataFrame(all_records)

    # Build a 5-digit county FIPS for joining to county-level data later.
    # fipsStateCode is 2 digits, fipsCountyCode is 3 digits.
    df["fipsStateCode"] = df["fipsStateCode"].astype(str).str.zfill(2)
    df["fipsCountyCode"] = df["fipsCountyCode"].astype(str).str.zfill(3)
    df["county_fips"] = df["fipsStateCode"] + df["fipsCountyCode"]

    df["declarationDate"] = pd.to_datetime(df["declarationDate"], errors="coerce")
    df["incidentBeginDate"] = pd.to_datetime(df["incidentBeginDate"], errors="coerce")
    df["incidentEndDate"] = pd.to_datetime(df["incidentEndDate"], errors="coerce")

    df = df.drop_duplicates()

    os.makedirs("processed", exist_ok=True)
    df.to_csv(OUT_PATH, index=False)

    print(f"\nSaved {len(df):,} disaster declaration records -> {OUT_PATH}")
    print("\nBy state:")
    print(df["state"].value_counts())
    print("\nBy incident type (top 10):")
    print(df["incidentType"].value_counts().head(10))
    print(f"\nDate range: {df['declarationDate'].min()} to {df['declarationDate'].max()}")


if __name__ == "__main__":
    main()
