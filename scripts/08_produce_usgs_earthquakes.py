"""
Step 6: Kafka live pipeline -- USGS earthquakes producer (REST version).

Polls USGS for earthquakes in a bounding box around the Gulf Coast region
on a regular interval and sends each one into the Kafka topic
"usgs-earthquakes" on Confluent Cloud.

Uses the same REST-over-HTTPS approach as the NOAA producer (see
07_produce_noaa_alerts.py for why -- datascience.tamucc.edu blocks the
native Kafka port 9092, but HTTPS/443 works fine).

Source: USGS fdsnws event query API, no API key needed.
  https://earthquake.usgs.gov/fdsnws/event/1/query
Schema confirmed live via 08a_inspect_usgs_earthquakes.py.

Note: the Gulf Coast is not very seismically active, so it's completely
normal for this to send 0 earthquakes most runs -- that's expected, not
a bug. It's still worth having in a multi-hazard framework since the
other 4 hazard states (TX/LA/MS/AL/FL) do occasionally get small quakes,
especially TX (induced seismicity) and the panhandle.

Credentials: read from kafka_credentials.properties (same file as the
NOAA producer -- NOT committed to GitHub, see .gitignore).
"""

import base64
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

TOPIC = "usgs-earthquakes"
POLL_SECONDS = 300  # 5 minutes
CREDENTIALS_PATH = "kafka_credentials.properties"

# Rough bounding box covering TX/LA/MS/AL/FL and nearby Gulf waters.
MIN_LAT, MAX_LAT = 23.0, 33.0
MIN_LON, MAX_LON = -99.0, -79.0

BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def load_config(path: str) -> dict:
    config = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            config[key.strip()] = value.strip()
    required = ["sasl.username", "sasl.password", "rest.endpoint", "cluster.id"]
    missing = [k for k in required if k not in config]
    if missing:
        raise ValueError(f"{path} is missing required keys: {missing}")
    return config


def fetch_recent_quakes() -> list[dict]:
    starttime = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
    params = {
        "format": "geojson",
        "starttime": starttime,
        "minlatitude": MIN_LAT,
        "maxlatitude": MAX_LAT,
        "minlongitude": MIN_LON,
        "maxlongitude": MAX_LON,
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "capstone-data-pipeline (student project, contact: patelmalav1234@gmail.com)",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("features", [])


def produce_record(records_url: str, auth_header: str, key: str, record: dict) -> None:
    body = json.dumps({
        "key": {"type": "STRING", "data": key},
        "value": {"type": "JSON", "data": record},
    }).encode("utf-8")
    req = urllib.request.Request(
        records_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": auth_header,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def poll_and_produce(records_url: str, auth_header: str) -> int:
    try:
        quakes = fetch_recent_quakes()
    except Exception as e:  # noqa: BLE001
        print(f"  Couldn't fetch earthquake data: {e}")
        return 0

    sent = 0
    failed = 0
    for quake in quakes:
        props = quake.get("properties", {})
        geom = quake.get("geometry", {})
        coords = geom.get("coordinates", [None, None, None])
        record = {
            "id": quake.get("id"),
            "mag": props.get("mag"),
            "place": props.get("place"),
            "time": props.get("time"),  # Unix ms timestamp
            "updated": props.get("updated"),
            "tsunami": props.get("tsunami"),
            "sig": props.get("sig"),
            "magType": props.get("magType"),
            "status": props.get("status"),
            "title": props.get("title"),
            "longitude": coords[0],
            "latitude": coords[1],
            "depth_km": coords[2],
        }
        key = record["id"] or "unknown"
        try:
            produce_record(records_url, auth_header, key, record)
            sent += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAILED to send earthquake {key}: {e}")

    if failed:
        print(f"  ({failed} message(s) failed to send -- see errors above)")
    return sent


def main():
    config = load_config(CREDENTIALS_PATH)
    records_url = (
        f"{config['rest.endpoint']}/kafka/v3/clusters/{config['cluster.id']}"
        f"/topics/{TOPIC}/records"
    )
    credentials = f"{config['sasl.username']}:{config['sasl.password']}"
    auth_header = "Basic " + base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    print(f"Sending to: {records_url}")
    print(f"Polling USGS earthquakes near the Gulf Coast every {POLL_SECONDS}s.")
    print("0 earthquakes most runs is normal -- this region isn't very seismically active.")
    print("Press the Stop/Interrupt button in Jupyter to end this.\n")

    try:
        while True:
            sent = poll_and_produce(records_url, auth_header)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"sent {sent} earthquake(s) to topic '{TOPIC}'")
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
