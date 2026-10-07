"""
Step 7a: Kafka live pipeline -- NASA FIRMS fire detections, inspect-first.

Before writing the real producer, pull a small slice of the live FIRMS
feed for the Gulf Coast region and print what it looks like.

Source: NASA FIRMS Area API (CSV), needs a free MAP_KEY.
  https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{BBOX}/{DAY_RANGE}

MAP_KEY: read from kafka_credentials.properties (key: firms_map_key) --
same gitignored file as the Kafka credentials.

SOURCE: VIIRS_SNPP_NRT -- near-real-time fire detections from the
Suomi-NPP satellite, good balance of coverage and resolution for VIIRS.

BBOX: west,south,east,north -- same rough Gulf Coast box as the USGS
earthquake producer.
"""

import csv
import io
import urllib.request

CREDENTIALS_PATH = "kafka_credentials.properties"
BBOX = "-99,23,-79,33"  # west,south,east,north
SOURCE = "VIIRS_SNPP_NRT"
DAY_RANGE = 1  # most recent 1 day of detections


def load_firms_key(path: str) -> str:
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("firms_map_key="):
                return line.split("=", 1)[1].strip()
    raise ValueError(
        f"Couldn't find a 'firms_map_key=' line in {path}. "
        f"Add it: firms_map_key=YOUR_KEY_HERE"
    )


def main():
    map_key = load_firms_key(CREDENTIALS_PATH)
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{map_key}/{SOURCE}/{BBOX}/{DAY_RANGE}"
    )
    print(f"Fetching FIRMS data for the Gulf Coast bounding box ...")
    req = urllib.request.Request(url, headers={
        "User-Agent": "capstone-data-pipeline (student project, contact: patelmalav1234@gmail.com)",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")

    # A key-invalid or rate-limited response comes back as a short message,
    # not real CSV -- check for that before trying to parse it as data.
    if "Invalid MAP_KEY" in text or "Error" in text[:200]:
        print(f"FIRMS returned an error instead of data:\n{text[:500]}")
        return

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    print(f"\n{len(rows)} fire detection(s) in the Gulf Coast region in the last {DAY_RANGE} day(s).")

    if not rows:
        print("No active fires detected in this region/window right now -- "
              "that's normal, not an error.")
        return

    print(f"\nColumn names: {reader.fieldnames}")
    print(f"\nFirst detection:")
    for key, value in rows[0].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
