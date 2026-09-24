"""
Step 3a: Just download the CDC/ATSDR Social Vulnerability Index (SVI) county
file and LOOK at it, before we write the real filtering script.

The team roles doc calls this "FEMA SVI," but it's actually published by
CDC/ATSDR, not FEMA -- FEMA just links to it. Source:
  https://svi.cdc.gov/dataDownloads/data-download.html
  Direct national CSV: https://svi.cdc.gov/publications/data/svi-pub-data.csv

This script doesn't filter or clean anything yet -- it just prints what's
actually in the file (columns, shape, a few sample rows) so we can write
the real processing script against the REAL column names instead of
guessing (see the FEMA "title" vs "declarationTitle" bug from last time).
"""

import pandas as pd

SVI_URL = "https://svi.cdc.gov/publications/data/svi-pub-data.csv"


def main():
    print(f"Downloading {SVI_URL} ...")
    df = pd.read_csv(SVI_URL, low_memory=False)

    print(f"\nShape: {df.shape}")
    print(f"\nAll {len(df.columns)} column names:")
    for col in df.columns:
        print(f"  {col}")

    print("\nFirst 3 rows (all columns):")
    print(df.head(3).to_string())

    # If there's an obvious state-abbreviation-like column, show what Gulf
    # Coast states look like in it, to confirm how to filter later.
    for candidate in ["ST_ABBR", "STATE", "ST"]:
        if candidate in df.columns:
            print(f"\nUnique values in '{candidate}' (first 20):")
            print(sorted(df[candidate].astype(str).unique())[:20])
            break


if __name__ == "__main__":
    main()
