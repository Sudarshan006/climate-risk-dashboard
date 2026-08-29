"""
feature_engineering.py

Builds the feature set and rolling sequences used by both the XGBoost
baseline and the TFT model. Splits inputs into the three categories
TFT expects: static, known-future, and observed-past.

Owner: Ganesh (ML Modeler)

Reference: Lim et al. 2021, "Temporal Fusion Transformers for interpretable
multi-horizon time series forecasting" (Section 3 - input categories).
"""

import pandas as pd
import numpy as np

# --- Feature category definitions (TODO: confirm/adjust against real schema) ---

STATIC_FEATURES = [
    "county_fips",
    "state",
    "svi_score",       # FEMA Social Vulnerability Index
]

KNOWN_FUTURE_FEATURES = [
    "day_of_week",
    "month",
    "is_hurricane_season",  # engineered flag, e.g. June-Nov
]

OBSERVED_FEATURES = [
    # NOAA climate variables - fill in exact column names once confirmed
    "noaa_precip",
    "noaa_temp_max",
    "noaa_temp_min",
    "noaa_wind_speed",
    "firms_fire_count",
    "fema_declaration_flag",
]

TARGET_COLUMNS = [
    "target_flood_risk",
    "target_wildfire_risk",
    "target_storm_risk",
]

SEQUENCE_LENGTH_DAYS = 30  # lookback window, per project abstract


def add_calendar_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Engineer known-future calendar features."""
    df = df.copy()
    df["day_of_week"] = df[date_col].dt.dayofweek
    df["month"] = df[date_col].dt.month
    df["is_hurricane_season"] = df["month"].between(6, 11).astype(int)
    return df


def normalize_continuous(df: pd.DataFrame, columns: list, per_entity_col: str = "county_fips") -> pd.DataFrame:
    """
    Z-score normalize continuous features, per entity (per county) -
    following the paper's approach for datasets with entities of
    differing magnitude (Section 6.2 / Appendix A).
    """
    df = df.copy()
    for col in columns:
        df[col] = df.groupby(per_entity_col)[col].transform(
            lambda x: (x - x.mean()) / (x.std() + 1e-8)
        )
    return df


def build_sequences(df: pd.DataFrame, entity_col: str = "county_fips",
                     date_col: str = "date", seq_len: int = SEQUENCE_LENGTH_DAYS):
    """
    Build rolling sequences of length `seq_len` per entity, for TFT's
    TimeSeriesDataSet input format (long format with a time_idx column).

    Returns a DataFrame with an added `time_idx` column (integer index
    per entity, required by pytorch-forecasting's TimeSeriesDataSet).
    """
    df = df.sort_values([entity_col, date_col]).copy()
    df["time_idx"] = df.groupby(entity_col).cumcount()

    # Filter out entities with fewer than seq_len observations
    counts = df.groupby(entity_col)[date_col].count()
    valid_entities = counts[counts >= seq_len].index
    df = df[df[entity_col].isin(valid_entities)]

    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Full pipeline: calendar features -> normalization -> sequence prep."""
    df = add_calendar_features(df)
    df = normalize_continuous(df, [c for c in OBSERVED_FEATURES if c in df.columns])
    df = build_sequences(df)
    return df


if __name__ == "__main__":
    # TODO: wire up to data_loader.py once real data is available
    pass
