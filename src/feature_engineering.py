"""
feature_engineering.py

Builds continuous daily sequences per station and constructs the 30-day
sliding windows used by TFT (via pytorch-forecasting's TimeSeriesDataSet,
which needs a continuous integer time_idx per entity).

Owner: Ganesh (ML Modeler)

CONFIRMED against real data (2026-09-23):
    - 523 stations, 2,821,106 rows in the 2010-01-01 to 2026-08-27 window
    - Median missing-day rate per station: ~1.8%
    - 60 of 523 stations have >20% missing days (some as high as 95%) --
      these are excluded by default (see MIN_COVERAGE_THRESHOLD below),
      since a station with huge date gaps can't support a meaningful
      30-day rolling window.

NOTE: Sequences are currently built per STATION (not per county), since
county FIPS mapping is still an open TODO -- see data_loader.station_to_county().
Once that mapping exists, aggregate to county level before calling
build_sequences(), or adjust entity_col accordingly.
"""

import pandas as pd
import numpy as np

SEQUENCE_LENGTH_DAYS = 30      # lookback window (TFT encoder length)
PREDICTION_HORIZON_DAYS = 7    # forecast horizon (TFT decoder length) -- TODO: confirm with team

# Stations with more missing days than this (as a fraction) are dropped --
# too many gaps to support reliable 30-day sequences.
MIN_COVERAGE_THRESHOLD = 0.20

WEATHER_COLUMNS = ["PRCP", "TMAX", "TMIN"]  # SNOW/SNWD excluded -- see data_loader.py notes


def assess_station_coverage(df: pd.DataFrame, date_col: str = "DATE",
                             entity_col: str = "STATION") -> pd.DataFrame:
    """
    For each station, compute what fraction of calendar days in its range
    are actually present. Returns a per-station summary DataFrame.
    """
    rows = []
    for station, sub in df.groupby(entity_col):
        sub = sub.sort_values(date_col)
        span_days = (sub[date_col].max() - sub[date_col].min()).days + 1
        actual_days = sub[date_col].nunique()
        missing_pct = (span_days - actual_days) / span_days if span_days > 0 else 1.0
        rows.append({entity_col: station, "span_days": span_days,
                      "actual_days": actual_days, "missing_pct": missing_pct})
    return pd.DataFrame(rows)


def filter_low_coverage_stations(df: pd.DataFrame, coverage: pd.DataFrame = None,
                                  threshold: float = MIN_COVERAGE_THRESHOLD,
                                  entity_col: str = "STATION") -> pd.DataFrame:
    """Drop stations whose missing-day rate exceeds `threshold`."""
    if coverage is None:
        coverage = assess_station_coverage(df, entity_col=entity_col)

    good_stations = coverage[coverage["missing_pct"] <= threshold][entity_col]
    before_stations = df[entity_col].nunique()
    df_filtered = df[df[entity_col].isin(good_stations)].copy()
    after_stations = df_filtered[entity_col].nunique()

    print(f"Station coverage filter (threshold={threshold:.0%} missing days): "
          f"{before_stations} -> {after_stations} stations kept "
          f"({before_stations - after_stations} dropped)")

    return df_filtered


def reindex_to_daily(df: pd.DataFrame, date_col: str = "DATE",
                      entity_col: str = "STATION") -> pd.DataFrame:
    """
    Reindex each station's data onto a continuous daily calendar within
    its own date range, filling gap-days with NaN for the weather columns
    (identity columns -- LATITUDE, LONGITUDE, etc. -- are forward-filled
    since they don't change over time for a station).

    This is required before building a clean time_idx for TimeSeriesDataSet:
    pytorch-forecasting expects time_idx to increment by exactly 1 per step,
    so gap-days need to exist as rows (with NaN weather values) rather than
    being silently skipped.
    """
    static_cols = [c for c in df.columns if c not in
                   [date_col, entity_col] + WEATHER_COLUMNS + ["SNOW", "SNWD"]]

    filled_frames = []
    for station, sub in df.groupby(entity_col):
        sub = sub.sort_values(date_col).set_index(date_col)
        full_range = pd.date_range(sub.index.min(), sub.index.max(), freq="D")
        sub_reindexed = sub.reindex(full_range)
        sub_reindexed[entity_col] = station
        # static/identity columns don't change -- forward/back fill them
        for col in static_cols:
            if col in sub_reindexed.columns:
                sub_reindexed[col] = sub_reindexed[col].ffill().bfill()
        sub_reindexed.index.name = date_col
        filled_frames.append(sub_reindexed.reset_index())

    result = pd.concat(filled_frames, ignore_index=True)
    print(f"Reindexed to daily: {len(df):,} -> {len(result):,} rows "
          f"({len(result) - len(df):,} gap-day rows added with NaN weather values)")
    return result


def add_time_idx(df: pd.DataFrame, date_col: str = "DATE",
                  entity_col: str = "STATION") -> pd.DataFrame:
    """
    Add the integer `time_idx` column pytorch-forecasting's TimeSeriesDataSet
    requires: increments by exactly 1 per day, per entity. Only valid after
    reindex_to_daily() has removed gaps.
    """
    df = df.sort_values([entity_col, date_col]).copy()
    df["time_idx"] = df.groupby(entity_col).cumcount()
    return df


def filter_min_sequence_length(df: pd.DataFrame, entity_col: str = "STATION",
                                min_len: int = SEQUENCE_LENGTH_DAYS + PREDICTION_HORIZON_DAYS
                                ) -> pd.DataFrame:
    """Keep only entities with enough history to form at least one full sequence."""
    counts = df.groupby(entity_col).size()
    valid_entities = counts[counts >= min_len].index
    before = df[entity_col].nunique()
    df_filtered = df[df[entity_col].isin(valid_entities)].copy()
    after = df_filtered[entity_col].nunique()
    print(f"Min-length filter (>= {min_len} days): {before} -> {after} stations kept")
    return df_filtered


def build_sequences(df: pd.DataFrame, date_col: str = "DATE",
                     entity_col: str = "STATION",
                     coverage_threshold: float = MIN_COVERAGE_THRESHOLD) -> pd.DataFrame:
    """
    Full pipeline: filter low-coverage stations -> reindex to continuous
    daily calendar -> add time_idx -> filter stations with too little
    history to form a full sequence.

    Returns a DataFrame ready to be wrapped in a pytorch-forecasting
    TimeSeriesDataSet (has time_idx, still has NaN gaps in weather columns
    that need interpolation -- see the temperature-interpolation task).
    """
    df = filter_low_coverage_stations(df, threshold=coverage_threshold, entity_col=entity_col)
    df = reindex_to_daily(df, date_col=date_col, entity_col=entity_col)
    df = add_time_idx(df, date_col=date_col, entity_col=entity_col)
    df = filter_min_sequence_length(df, entity_col=entity_col)
    return df


if __name__ == "__main__":
    from data_loader import load_noaa_data, DEFAULT_START_DATE

    df = load_noaa_data(start_date=DEFAULT_START_DATE)
    df_seq = build_sequences(df)

    print("\n=== Final sequence-ready dataset ===")
    print(f"Rows: {len(df_seq):,}")
    print(f"Stations: {df_seq['STATION'].nunique()}")
    print(f"time_idx range per station (should start at 0): "
          f"{df_seq.groupby('STATION')['time_idx'].min().unique()[:5]} ... "
          f"max example: {df_seq['time_idx'].max()}")
    print("\nSample rows for one station:")
    sample_station = df_seq['STATION'].iloc[0]
    print(df_seq[df_seq['STATION'] == sample_station][
        ['STATION', 'DATE', 'time_idx', 'PRCP', 'TMAX', 'TMIN']].head(10))