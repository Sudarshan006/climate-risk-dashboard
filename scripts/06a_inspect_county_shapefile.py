"""
Step 4a: Download the Census cartographic boundary county shapefile and LOOK
at it before writing the real station-to-county join script.

Same "inspect first" pattern used for SVI (05a_inspect_svi.py), after the
FEMA "title" field bug taught us not to guess column names blind.

Source: U.S. Census Bureau cartographic boundary files (county, national,
1:500,000 scale), 2023 vintage:
  https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html
  Direct download: https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip

geopandas can read a zipped shapefile straight from a URL (no manual
unzip needed) using the "zip+https://" prefix.

This script doesn't filter or join anything yet -- it just prints the
columns, shape, CRS, and a few sample rows so we can confirm the exact
field names (state FIPS, county FIPS, combined GEOID, county name) before
writing the real spatial-join script.
"""

import geopandas as gpd

SHAPEFILE_URL = "zip+https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"


def main():
    print(f"Downloading {SHAPEFILE_URL} ...")
    counties = gpd.read_file(SHAPEFILE_URL)

    print(f"\nShape: {counties.shape}")
    print(f"CRS: {counties.crs}")
    print(f"\nAll {len(counties.columns)} column names:")
    for col in counties.columns:
        print(f"  {col}")

    print("\nFirst 5 rows (non-geometry columns):")
    print(counties.drop(columns="geometry").head(5).to_string())

    # Confirm which columns hold state FIPS, county FIPS, and the combined
    # 5-digit GEOID, since these are what we'll need to match the
    # county_fips / STCNTY columns already used in the FEMA and SVI data.
    for candidate in ["STATEFP", "COUNTYFP", "GEOID", "GEOIDFQ", "NAME", "STUSPS"]:
        if candidate in counties.columns:
            print(f"\n'{candidate}' sample values: {counties[candidate].head(5).tolist()}")


if __name__ == "__main__":
    main()
