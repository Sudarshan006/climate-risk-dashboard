"""
Step 5a: Kafka live pipeline -- NOAA weather alerts, inspect-first.

Before writing the real producer (which pushes into Kafka), just pull the
live NOAA alerts feed and print what a real alert looks like, so we build
the producer against the real field names.

Source: National Weather Service API (api.weather.gov), no API key needed.
  https://api.weather.gov/alerts/active?area={STATE}

This fetches currently active alerts for one Gulf state and prints the
raw structure -- no Kafka involved yet.
"""

import json
import urllib.request

STATE = "TX"  # try one state first; the real producer loops over all 5
URL = f"https://api.weather.gov/alerts/active?area={STATE}"


def main():
    print(f"Fetching {URL} ...")
    req = urllib.request.Request(URL, headers={
        "User-Agent": "capstone-data-pipeline (student project, contact: patelmalav1234@gmail.com)",
        "Accept": "application/geo+json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    features = payload.get("features", [])
    print(f"\n{len(features)} active alert(s) for {STATE} right now.")

    if not features:
        print("No active alerts for this state at the moment -- that's normal, "
              "not an error. Try again later, or try a different state below.")
        return

    first = features[0]["properties"]
    print(f"\nAll property keys in one alert:")
    for key in first.keys():
        print(f"  {key}")

    print("\nKey fields from the first alert:")
    for field in ["event", "severity", "certainty", "urgency", "areaDesc",
                  "headline", "effective", "expires", "ends", "description"]:
        print(f"\n--- {field} ---")
        print(first.get(field))


if __name__ == "__main__":
    main()
