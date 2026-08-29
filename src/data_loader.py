"""
data_loader.py

Loads the cleaned, joined dataset produced by the Data Engineer's pipeline
(GHCN-Daily + NASA FIRMS + FEMA Disaster Declarations + FEMA SVI), ready
for feature engineering.

Owner: Ganesh (ML Modeler)
"""

import pandas as pd
from pathlib import Path


def load_raw_data(filepath: str) -> pd.DataFrame:
    """
    Load the cleaned dataset from the data engineering pipeline.

    Expected columns (confirm exact schema with Malav once pipeline is live):
        - county_fips        (str)  static entity id
        - state               (str)  static
        - date                (datetime)
        - noaa_* columns      (float) observed climate readings
        - firms_fire_count    (int)   observed fire detections
        - fema_declaration    (bool/int) observed past disaster flags
        - svi_score           (float) static social vulnerability index
        - target_flood_risk / target_wildfire_risk / target_storm_risk (label)

    TODO: replace with actual path/schema once Malav's pipeline delivers output
    (likely a parquet/csv from Kafka sink or a batch export).
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"No data found at {filepath}. Confirm output path with Data Engineer.")

    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix == ".csv":
        df = pd.read_csv(path, parse_dates=["date"])
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    return df


def basic_sanity_checks(df: pd.DataFrame) -> None:
    """Quick checks before handing off to feature engineering."""
    print(f"Rows: {len(df)}, Counties: {df['county_fips'].nunique() if 'county_fips' in df else 'N/A'}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}" if 'date' in df else "No date column found")
    print(f"Missing values per column:\n{df.isna().sum()}")


if __name__ == "__main__":
    # TODO: update path once real data is available
    df = load_raw_data("../data/cleaned_gulf_coast_data.parquet")
    basic_sanity_checks(df)
