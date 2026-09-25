"""
Step 4: Station -> county mapping.

Spatially joins each of the 523 official Gulf Coast weather stations
(lat/lon) to the U.S. county polygon it falls inside, producing a
station -> 5-digit county FIPS lookup table. This is the missing link
between the station-keyed historical weather data (STATION) and the
county-keyed FEMA disaster / SVI data (county_fips / STCNTY).

Source confirmed live via 06a_inspect_county_shapefile.py:
  Census cartographic boundary county shapefile, 2023, 1:500,000 scale.
  Key columns: STATEFP (2-digit), COUNTYFP (3-digit), GEOID (5-digit,
  STATEFP+COUNTYFP -- same format as county_fips/STCNTY), NAME, STUSPS.

Input:
  processed/gulf_coast_stations_official.csv (from 00_get_official_station_list.py)
  -- must have a station-id column and latitude/longitude columns.

Output:
  processed/station_county_mapping.csv
  -- one row per station: STATION, LATITUDE, LONGITUDE, county_fips,
     county_name, state_abbr
"""

import os

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

STATIONS_CSV = "processed/gulf_coast_stations_official.csv"
SHAPEFILE_URL = "zip+https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"
OUT_PATH = "processed/station_county_mapping.csv"

STATION_ID_COL_CANDIDATES = ["STATION", "station", "id", "ID"]
LAT_COL_CANDIDATES = ["LATITUDE", "latitude", "lat", "LAT"]
LON_COL_CANDIDATES = ["LONGITUDE", "longitude", "lon", "LON", "long"]


def find_col(df: pd.DataFrame, candidates: list[str], label: str) -> str:
    col = next((c for c in candidates if c in df.columns), None)
    if col is None:
        raise ValueError(
            f"Couldn't find a {label} column in {STATIONS_CSV} "
            f"(looked for {candidates}); check the file's actual column names "
            f"(run: pd.read_csv('{STATIONS_CSV}').columns) and add the real "
            f"name to the candidates list above."
        )
    return col


def main():
    stations = pd.read_csv(STATIONS_CSV)
    id_col = find_col(stations, STATION_ID_COL_CANDIDATES, "station-id")
    lat_col = find_col(stations, LAT_COL_CANDIDATES, "latitude")
    lon_col = find_col(stations, LON_COL_CANDIDATES, "longitude")

    print(f"Loaded {len(stations)} stations from {STATIONS_CSV} "
          f"(id={id_col}, lat={lat_col}, lon={lon_col})")

    # Build a station GeoDataFrame -- station lat/lon is in plain WGS84
    # (EPSG:4326), same as GPS coordinates.
    station_points = gpd.GeoDataFrame(
        stations[[id_col, lat_col, lon_col]].copy(),
        geometry=[Point(xy) for xy in zip(stations[lon_col], stations[lat_col])],
        crs="EPSG:4326",
    )

    print(f"Downloading county boundaries from {SHAPEFILE_URL} ...")
    counties = gpd.read_file(SHAPEFILE_URL)[["STATEFP", "COUNTYFP", "GEOID", "NAME", "STUSPS", "geometry"]]

    # Match CRS before joining -- county file is EPSG:4269 (NAD83), stations
    # are EPSG:4326 (WGS84). These are close enough in practice for county-
    # level assignment, but reproject properly rather than assuming.
    counties = counties.to_crs(station_points.crs)

    print("Running point-in-polygon spatial join ...")
    joined = gpd.sjoin(station_points, counties, how="left", predicate="within")

    unmatched = joined["GEOID"].isna()
    if unmatched.any():
        print(f"\n{int(unmatched.sum())} station(s) didn't fall inside any county polygon "
              f"on the first pass (likely just off the coastline/boundary edge) -- "
              f"retrying those with a small buffer ...")
        # A station right on a coastline can fall just outside every polygon
        # due to simplified boundary geometry. Retry unmatched points against
        # the nearest county instead of leaving them blank.
        unmatched_points = station_points[unmatched]
        nearest = gpd.sjoin_nearest(unmatched_points, counties, how="left")
        for idx in unmatched_points.index:
            for col in ["STATEFP", "COUNTYFP", "GEOID", "NAME", "STUSPS", "index_right"]:
                joined.loc[idx, col] = nearest.loc[idx, col]

    result = joined[[id_col, lat_col, lon_col, "GEOID", "NAME", "STUSPS"]].rename(
        columns={
            id_col: "STATION",
            lat_col: "LATITUDE",
            lon_col: "LONGITUDE",
            "GEOID": "county_fips",
            "NAME": "county_name",
            "STUSPS": "state_abbr",
        }
    )

    still_unmatched = result["county_fips"].isna().sum()
    if still_unmatched:
        print(f"\nWARNING: {still_unmatched} station(s) still unmatched after nearest-county "
              f"fallback -- check these manually.")
        print(result[result["county_fips"].isna()])

    os.makedirs("processed", exist_ok=True)
    result.to_csv(OUT_PATH, index=False)

    print(f"\nSaved {len(result):,} station-county mappings -> {OUT_PATH}")
    print(f"\nStations matched to counties by state:")
    print(result["state_abbr"].value_counts())
    print(f"\nUnique counties covered: {result['county_fips'].nunique()}")


if __name__ == "__main__":
    main()
