"""
Step 6a: Kafka live pipeline -- USGS earthquakes, inspect-first.

Before writing the real producer, pull the live USGS feed and print what a
real earthquake record looks like, confirming field names before building
against them.

Source: USGS Earthquake Hazards Program GeoJSON feed, no API key needed.
  https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{FEED}.geojson

USGS publishes several pre-built feeds by magnitude/time window. We use
"all_day" here (every earthquake worldwide in the last 24 hours) just to
inspect the shape of the data -- the real producer will filter down to
magnitude/area relevant to the Gulf Coast.
"""

import json
import urllib.request

URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"


def main():
    print(f"Fetching {URL} ...")
    req = urllib.request.Request(URL, headers={
        "User-Agent": "capstone-data-pipeline (student project, contact: patelmalav1234@gmail.com)",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    features = payload.get("features", [])
    print(f"\n{len(features)} earthquake(s) worldwide in the last 24 hours.")
    print(f"Metadata: {payload.get('metadata', {})}")

    if not features:
        print("No earthquakes in the feed right now -- unusual but not impossible.")
        return

    first = features[0]
    props = first.get("properties", {})
    geom = first.get("geometry", {})

    print(f"\nAll property keys in one earthquake record:")
    for key in props.keys():
        print(f"  {key}")

    print("\nKey fields from the first earthquake:")
    for field in ["mag", "place", "time", "updated", "tsunami", "sig",
                  "magType", "type", "title", "status"]:
        print(f"  {field}: {props.get(field)}")

    print(f"\nGeometry (type + coordinates [lon, lat, depth_km]):")
    print(f"  {geom}")


if __name__ == "__main__":
    main()
