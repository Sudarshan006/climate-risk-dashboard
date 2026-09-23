"""
data_loader.py

Loads the cleaned NOAA GHCN-Daily dataset produced by Malav's
data-engineering pipeline (03_scale_station_download.py).

Owner: Ganesh (ML Modeler)

CONFIRMED schema (verified directly against the real file, 2026-09-23):
    data/processed/gulf_coast_historical.parquet
        STATION     (str)             NOAA station id -- NOT county FIPS
        DATE        (datetime64[us])  daily granularity
        LATITUDE    (float64)
        LONGITUDE   (float64)
        ELEVATION   (float64)
        NAME        (str)             station name, e.g. "ALEXANDER CITY, AL US"
        PRCP        (float64)         precipitation, mm      (1.6% missing)
        SNOW        (float64)         snowfall, mm            (19.0% missing)
        SNWD        (float64)         snow depth, mm           (21.5% missing)
        TMAX        (float64)         max temp, deg C          (8.4% missing)
        TMIN        (float64)         min temp, deg C          (8.8% missing)

    Scale: 15,363,398 rows across 523 stations, 1877-11-01 to 2026-08-27.
    Identity columns (STATION, DATE, LATITUDE, LONGITUDE, ELEVATION, NAME)
    have zero missing values.

KNOWN GAPS (as of 2026-09-23):
    - No county FIPS code -- data is keyed by STATION + lat/lon only.
      See station_to_county() below.
    - No FEMA disaster declarations / risk labels yet -- this means there
      is currently NO TARGET to train XGBoost or TFT against. Confirmed
      blocker per GitHub issue #5 ("Blocked on: FEMA risk labels from Malav").
    - No FIRMS wildfire data yet.
"""

import pandas as pd
from pathlib import Path

NOAA_PARQUET_PATH = "data/processed/gulf_coast_historical.parquet"
NOAA_SAMPLE_CSV_PATH = "data/processed/gulf_coast_historical_sample.csv"

EXPECTED_COLUMNS = [
    "STATION", "DATE", "LATITUDE", "LONGITUDE",
    "ELEVATION", "NAME", "PRCP", "SNOW", "SNWD", "TMAX", "TMIN",
]

# Data goes back to 1877, which is far more history than useful for
# modeling (station coverage / instrumentation quality was much lower
# in early decades). Restrict to a recent, consistent window.
DEFAULT_START_DATE = "2010-01-01"


def load_noaa_data(filepath: str = NOAA_PARQUET_PATH,
                    start_date: str = None) -> pd.DataFrame:
    """
    Load Malav's cleaned NOAA GHCN-Daily parquet (or the CSV sample).

    start_date: optional ISO date string (e.g. "2010-01-01") to filter
    out older, sparser history. Pass None to load everything.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(
            f"No data found at {filepath}. Confirm the file location with "
            f"the Data Engineer -- it's produced by 03_scale_station_download.py "
            f"and not committed to git (too large / gitignored)."
        )

    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix == ".csv":
        df = pd.read_csv(path, parse_dates=["DATE"])
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        print(f"WARNING: expected columns missing from loaded data: {missing}")

    if start_date is not None:
        before = len(df)
        df = df[df["DATE"] >= pd.Timestamp(start_date)].copy()
        print(f"Filtered to >= {start_date}: {before:,} -> {len(df):,} rows")

    return df


def basic_sanity_checks(df: pd.DataFrame) -> None:
    """Quick checks before handing off to feature engineering."""
    print(f"Rows: {len(df):,}")
    print(f"Stations: {df['STATION'].nunique() if 'STATION' in df else 'N/A'}")
    if "DATE" in df:
        print(f"Date range: {df['DATE'].min()} to {df['DATE'].max()}")
    print("Missing values per column (%):")
    print((df.isna().mean() * 100).round(2))


def station_to_county(df: pd.DataFrame, station_county_map: pd.DataFrame = None) -> pd.DataFrame:
    """
    TODO -- KNOWN GAP: no county FIPS in the source data. Our TFT model
    needs a county-level entity id, not a station id.

    If `station_county_map` (a DataFrame with columns STATION, COUNTY_FIPS)
    is supplied, merge it in. Otherwise this is a no-op -- callers should
    NOT proceed to county-level aggregation without this.
    """
    if station_county_map is None:
        print("WARNING: no station-to-county mapping supplied. County-level "
              "features cannot be built yet -- see TODO in station_to_county().")
        return df

    return df.merge(station_county_map, on="STATION", how="left")


if __name__ == "__main__":
    df = load_noaa_data(start_date=DEFAULT_START_DATE)
    basic_sanity_checks(df)
