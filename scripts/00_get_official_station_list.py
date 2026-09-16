"""
Reproduces Sud's exact station-selection logic from
notebooks/01_explore_ghcn.ipynb (analysis branch) so Malav's pipeline uses
the team's official 523-station Gulf Coast list, not an earlier draft one.

Selection criteria (Sud's, documented in the paper):
  - Region: TX, LA, MS, AL, FL
  - Core elements required: PRCP, TMAX, TMIN (all three present)
  - Minimum record length: 30 years
  - Still active: last year of record >= 2020

Output:
  processed/gulf_coast_stations_official.csv
  -- columns: ID, LATITUDE, LONGITUDE, ELEVATION, STATE, NAME
  -- should be 523 rows: TX 278, FL 85, AL 64, MS 50, LA 46
"""

import os

import pandas as pd

GULF_STATES = ["TX", "LA", "MS", "AL", "FL"]
CORE_ELEMENTS = ["PRCP", "TMAX", "TMIN"]
MIN_YEARS = 30
ACTIVE_SINCE = 2020

STATIONS_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt"
INVENTORY_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-inventory.txt"

OUT_PATH = "processed/gulf_coast_stations_official.csv"


def main():
    # --- station metadata ---
    station_colspecs = [(0, 11), (12, 20), (21, 30), (31, 37), (38, 40), (41, 71)]
    station_names = ["ID", "LATITUDE", "LONGITUDE", "ELEVATION", "STATE", "NAME"]
    print("Downloading ghcnd-stations.txt ...")
    stations = pd.read_fwf(STATIONS_URL, colspecs=station_colspecs, names=station_names)

    gulf_stations = stations[stations["STATE"].isin(GULF_STATES)].copy()
    print(f"  {len(gulf_stations)} Gulf Coast stations before quality filtering")

    # --- inventory (record length per station/element) ---
    inv_colspecs = [(0, 11), (12, 20), (21, 30), (31, 35), (36, 40), (41, 45)]
    inv_names = ["ID", "LATITUDE", "LONGITUDE", "ELEMENT", "FIRSTYEAR", "LASTYEAR"]
    print("Downloading ghcnd-inventory.txt ...")
    inventory = pd.read_fwf(INVENTORY_URL, colspecs=inv_colspecs, names=inv_names)
    inventory["RECORD_LENGTH"] = inventory["LASTYEAR"] - inventory["FIRSTYEAR"]

    good_records = inventory[
        (inventory["ELEMENT"].isin(CORE_ELEMENTS))
        & (inventory["RECORD_LENGTH"] >= MIN_YEARS)
        & (inventory["LASTYEAR"] >= ACTIVE_SINCE)
    ].copy()

    # stations that qualify on all 3 core elements, nationwide
    element_counts = good_records.groupby("ID")["ELEMENT"].nunique()
    complete_stations = element_counts[element_counts == 3].index

    # cross-reference: Gulf Coast stations that are also high quality
    gulf_shortlist = gulf_stations[gulf_stations["ID"].isin(complete_stations)].copy()

    print(f"\nFinal Gulf Coast shortlist: {len(gulf_shortlist)}")
    print(gulf_shortlist["STATE"].value_counts())

    os.makedirs("processed", exist_ok=True)
    gulf_shortlist.to_csv(OUT_PATH, index=False)
    print(f"\nSaved: {OUT_PATH}")


if __name__ == "__main__":
    main()
