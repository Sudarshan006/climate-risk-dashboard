"""
Step 1 (scaled) -- production download of daily GHCN-Daily records for the
team's official Gulf Coast station set, per Sud's handoff brief.

Input:
  A CSV with at least a "STATION" (or "id") column listing the 523 official
  station IDs (from 00_get_official_station_list.py).

What it does:
  - Downloads one CSV per station from NOAA's per-station "access" endpoint
  - Caches each raw download to data/raw/ so a crash/rerun doesn't re-download
    stations already fetched (resumable)
  - Shows a tqdm progress bar
  - Applies NOAA's own quality-control flags: any PRCP/TMAX/TMIN/SNOW/SNWD
    observation NOAA itself flagged as suspect gets nulled out rather than
    kept as-is
  - Validates that STATION/DATE are usable and drops rows that aren't
  - Combines everything, converts units (tenths -> real units), and writes
    a single cleaned Parquet matching the team's schema contract:
      STATION, DATE, LATITUDE, LONGITUDE, ELEVATION, NAME, PRCP, TMAX, TMIN
  - Fails loudly (instead of crashing on a confusing traceback) if every
    single station download fails
  - Prints a data-quality summary, and writes a small CSV sample + a
    failed-station log for easy handoff to teammates

Output:
  data/raw/{STATION}.csv                         -- one cached file per station (untouched)
  data/processed/gulf_coast_historical.parquet   -- combined, cleaned, unit-converted
  data/processed/gulf_coast_historical_sample.csv -- first 2,000 rows, for quick sharing
  data/raw/failed_stations.txt                    -- full list of stations that never downloaded
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
SAMPLE_PATH = os.path.join(PROCESSED_DIR, "gulf_coast_historical_sample.csv")
FAILED_LOG_PATH = os.path.join(RAW_DIR, "failed_stations.txt")

# Core weather elements + their NOAA quality-flag columns.
# Each *_ATTRIBUTES column is "MFLAG,QFLAG,SFLAG" -- a non-empty QFLAG means
# NOAA itself considers that observation to have failed quality control.
ELEMENTS = ["PRCP", "SNOW", "SNWD", "TMAX", "TMIN"]
ATTR_COLS = [f"{e}_ATTRIBUTES" for e in ELEMENTS]

IDENTITY_COLS = ["STATION", "DATE", "LATITUDE", "LONGITUDE", "ELEVATION", "NAME"]
KEEP_COLS = IDENTITY_COLS + ELEMENTS + ATTR_COLS

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


def apply_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Null out any observation NOAA's own QC flagged as suspect, then drop the
    now-unneeded attribute columns. Prints how many values got nulled per element
    so the team can see the effect of this step, not just trust it silently."""
    for element, attr_col in zip(ELEMENTS, ATTR_COLS):
        if element not in df.columns or attr_col not in df.columns:
            continue
        # attribute string is "MFLAG,QFLAG,SFLAG" -- QFLAG is the middle field
        parts = df[attr_col].astype(str).str.split(",", expand=True)
        if parts.shape[1] < 2:
            continue
        qflag = parts[1].fillna("").str.strip()
        flagged = qflag != ""
        n_flagged = int(flagged.sum())
        if n_flagged:
            print(f"  {element}: nulling {n_flagged:,} observations that failed NOAA QC")
            df.loc[flagged, element] = pd.NA
    return df.drop(columns=[c for c in ATTR_COLS if c in df.columns])


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

    succeeded = len(station_ids) - len(failed)
    print(f"\n{succeeded}/{len(station_ids)} stations downloaded successfully, "
          f"{len(failed)} failed.")

    if failed:
        os.makedirs(RAW_DIR, exist_ok=True)
        with open(FAILED_LOG_PATH, "w") as f:
            f.write("\n".join(failed))
        print(f"Failed station list written to {FAILED_LOG_PATH} "
              f"(preview: {failed[:10]}{' ...' if len(failed) > 10 else ''})")
        print("Re-run this script later -- succeeded stations are cached and will be skipped.")

    # Hard stop with a clear message instead of a confusing pd.concat crash
    # if every single station failed (e.g. NOAA endpoint down, no network).
    if not frames:
        raise RuntimeError(
            f"All {len(station_ids)} station downloads failed -- nothing to combine. "
            f"Check your internet connection and NOAA's endpoint status, then re-run. "
            f"See {FAILED_LOG_PATH} for the full list."
        )

    combined = pd.concat(frames, ignore_index=True)

    # Apply NOAA's own quality-control flags before anything else touches the values
    print("\nApplying NOAA quality-control flags:")
    combined = apply_quality_flags(combined)

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

    # --- Validate required fields instead of silently trusting filled-in NaNs ---
    before = len(combined)
    unusable = combined["STATION"].isna() | combined["DATE"].isna()
    if unusable.any():
        print(f"\nDropping {int(unusable.sum()):,} rows with missing STATION or DATE "
              f"(these are unusable as row identity).")
        combined = combined[~unusable].copy()

    all_weather_missing = combined[["PRCP", "TMAX", "TMIN"]].isna().all(axis=1)
    if all_weather_missing.any():
        print(f"Note: {int(all_weather_missing.sum()):,} rows have PRCP, TMAX, and TMIN "
              f"all missing (kept, but flagged here -- these carry no usable signal).")
    print(f"Row count: {before:,} -> {len(combined):,} after validation")

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    combined.to_parquet(OUT_PATH, index=False)
    combined.head(2000).to_csv(SAMPLE_PATH, index=False)
    print(f"\nSaved {len(combined):,} rows, {combined['STATION'].nunique()} stations -> {OUT_PATH}")
    print(f"Sample (first 2,000 rows) -> {SAMPLE_PATH}")

    # Data-quality summary (per Sud's missingness notes)
    print("\nMissingness by field (after QC-flag nulling):")
    for col in ["PRCP", "TMAX", "TMIN", "SNOW", "SNWD"]:
        if col in combined.columns:
            pct_missing = combined[col].isna().mean() * 100
            print(f"  {col}: {pct_missing:.1f}% missing")

    print("\nUnits: PRCP in mm, TMAX/TMIN in degrees C (converted from GHCN's raw tenths).")


if __name__ == "__main__":
    main()
