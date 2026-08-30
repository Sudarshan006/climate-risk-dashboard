"""
Step 1 (scaled) -- production download of daily GHCN-Daily records for the
team's official Gulf Coast station set, per Sud's handoff brief.

Input:
  A CSV with at least a "STATION" (or "id") column listing the 523 official
  station IDs from Sud's selection logic (ghcn_reference.py / 01_explore_ghcn.ipynb
  on the analysis branch). Point STATIONS_CSV at that file once you have it --
  for now this defaults to our own gulf_coast_stations.csv as a placeholder,
  which is NOT the official list and should be swapped out.

What it does:
  - Downloads one CSV per station from NOAA's per-station "access" endpoint
  - Caches each raw download to data/raw/ so a crash/rerun doesn't re-download
    stations already fetched (resumable)
  - Shows a tqdm progress bar
  - Combines everything, converts units (tenths -> real units), and writes
    a single cleaned Parquet matching the team's schema contract:
      STATION, DATE, LATITUDE, LONGITUDE, ELEVATION, NAME, PRCP, TMAX, TMIN
  - Prints a data-quality summary (per Sud's missingness notes:
    PRCP should be ~99% complete, TMAX/TMIN ~13% missing on co-op stations)

Output:
  data/raw/{STATION}.csv          -- one cached file per station (untouched)
  data/processed/gulf_coast_historical.parquet -- combined, cleaned, unit-converted
"""

import os
import time

import pandas as pd

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(iterable, **kwargs):
        return iterable

STATIONS_CSV = "processed/gulf_coast_stations_official.csv"  # from 00_get_official_station_list.py
STATION_ID_COL_CANDIDATES = ["STATION", "station", "id", "ID"]

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
OUT_PATH = os.path.join(PROCESSED_DIR, "gulf_coast_historical.parquet")

KEEP_COLS = ["STATION", "DATE", "LATITUDE", "LONGITUDE", "ELEVATION",
             "NAME", "PRCP", "SNOW", "SNWD", "TMAX", "TMIN"]

REQUEST_PAUSE_SECONDS = 0.5     # be polite to NOAA's server
MAX_RETRIES = 2


def get_station_ids(path: str) -> list[str]:
    df = pd.read_csv(path)
    col = next((c for c in STATION_ID_COL_CANDIDATES if c in df.columns), None)
    if col is None:
        raise ValueError(
            f"Couldn't find a station-id column in {path} "
            f"(looked for {STATION_ID_COL_CANDIDATES}); check the file."
        )
    return df[col].astype(str).tolist()


def download_station(station_id: str) -> pd.DataFrame | None:
    """Download one station's full daily record, using the on-disk cache if present."""
    os.makedirs(RAW_DIR, exist_ok=True)
    cache_path = os.path.join(RAW_DIR, f"{station_id}.csv")

    if os.path.exists(cache_path):
        return pd.read_csv(cache_path, low_memory=False)

    url = (
        "https://www.ncei.noaa.gov/data/"
        "global-historical-climatology-network-daily/access/"
        f"{station_id}.csv"
    )
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            df = pd.read_csv(url, low_memory=False)
            df.to_csv(cache_path, index=False)  # cache raw response for resumability
            return df
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.0 * attempt)
    print(f"  FAIL {station_id}: {last_err}")
    return None


def main():
    station_ids = get_station_ids(STATIONS_CSV)
    print(f"Downloading {len(station_ids)} stations "
          f"(cached files in {RAW_DIR}/ are reused, not re-downloaded)")

    frames = []
    failed = []
    for station_id in tqdm(station_ids, desc="stations"):
        df = download_station(station_id)
        if df is None:
            failed.append(station_id)
            continue
        available = [c for c in KEEP_COLS if c in df.columns]
        frames.append(df[available].copy())
        time.sleep(REQUEST_PAUSE_SECONDS)

    if failed:
        print(f"\n{len(failed)} stations failed to download: {failed[:20]}"
              f"{' ...' if len(failed) > 20 else ''}")
        print("Re-run this script later -- succeeded stations are cached and will be skipped.")

    combined = pd.concat(frames, ignore_index=True)

    # Unit conversions -- GHCN stores tenths of a degree C / tenths of a mm
    for col in ("TMAX", "TMIN", "PRCP"):
        if col in combined.columns:
            combined[col] = combined[col] / 10
    combined["DATE"] = pd.to_datetime(combined["DATE"])

    # Schema contract: one row per station per day, at least these columns
    contract_cols = ["STATION", "DATE", "LATITUDE", "LONGITUDE", "ELEVATION",
                      "NAME", "PRCP", "TMAX", "TMIN"]
    for col in contract_cols:
        if col not in combined.columns:
            combined[col] = pd.NA
    combined = combined.drop_duplicates(subset=["STATION", "DATE"])

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    combined.to_parquet(OUT_PATH, index=False)
    print(f"\nSaved {len(combined):,} rows, {combined['STATION'].nunique()} stations -> {OUT_PATH}")

    # Data-quality summary (per Sud's missingness notes)
    print("\nMissingness by field:")
    for col in ["PRCP", "TMAX", "TMIN", "SNOW", "SNWD"]:
        if col in combined.columns:
            pct_missing = combined[col].isna().mean() * 100
            print(f"  {col}: {pct_missing:.1f}% missing")


if __name__ == "__main__":
    main()
