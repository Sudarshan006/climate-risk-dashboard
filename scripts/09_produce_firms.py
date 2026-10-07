"""
Step 7: Kafka live pipeline -- NASA FIRMS fire detections producer (REST version).

Polls NASA FIRMS for active fire detections in the Gulf Coast region on a
regular interval and sends each one into the Kafka topic "nasa-firms-fires"
on Confluent Cloud.

Uses the same REST-over-HTTPS approach as the NOAA/USGS producers (see
07_produce_noaa_alerts.py for why -- datascience.tamucc.edu blocks the
native Kafka port 9092, but HTTPS/443 works fine).

Source: NASA FIRMS Area API (CSV), needs a free MAP_KEY.
Schema confirmed live via 09a_inspect_firms.py.

Credentials: read from kafka_credentials.properties -- needs these keys:
  sasl.username, sasl.password, rest.endpoint, cluster.id  (Kafka)
  firms_map_key                                            (FIRMS)

Note on the FIRMS day-range: the Area API's DAY_RANGE parameter returns
the *last N days* of detections every time, not just new ones since the
last poll -- so like the NOAA alerts, re-sending the same fire on every
poll is expected (Kafka consumers can dedupe using latitude+longitude+
acq_date+acq_time as a natural key, since FIRMS doesn't give each
detection a persistent unique ID).
"""

import base64
import csv
import io
import time
import json
import urllib.request

TOPIC = "nasa-firms-fires"
POLL_SECONDS = 300  # 5 minutes
CREDENTIALS_PATH = "kafka_credentials.properties"

BBOX = "-99,23,-79,33"  # west,south,east,north -- same box as USGS producer
SOURCE = "VIIRS_SNPP_NRT"
DAY_RANGE = 1


def load_config(path: str) -> dict:
    config = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            config[key.strip()] = value.strip()
    required = ["sasl.username", "sasl.password", "rest.endpoint", "cluster.id", "firms_map_key"]
    missing = [k for k in required if k not in config]
    if missing:
        raise ValueError(f"{path} is missing required keys: {missing}")
    return config


def fetch_fires(map_key: str) -> list[dict]:
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{map_key}/{SOURCE}/{BBOX}/{DAY_RANGE}"
    )
    req = urllib.request.Request(url, headers={
        "User-Agent": "capstone-data-pipeline (student project, contact: patelmalav1234@gmail.com)",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")

    if "Invalid MAP_KEY" in text or "Error" in text[:200]:
        raise RuntimeError(f"FIRMS returned an error instead of data: {text[:300]}")

    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


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


def poll_and_produce(records_url: str, auth_header: str, map_key: str) -> int:
    try:
        fires = fetch_fires(map_key)
    except Exception as e:  # noqa: BLE001
        print(f"  Couldn't fetch FIRMS data: {e}")
        return 0

    sent = 0
    failed = 0
    for fire in fires:
        # No persistent ID from FIRMS -- build a stable key from location + time
        # so the same detection re-sent on later polls uses the same key.
        key = f"{fire.get('latitude')}_{fire.get('longitude')}_{fire.get('acq_date')}_{fire.get('acq_time')}"
        try:
            produce_record(records_url, auth_header, key, fire)
            sent += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAILED to send fire detection {key}: {e}")

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
    map_key = config["firms_map_key"]

    print(f"Sending to: {records_url}")
    print(f"Polling NASA FIRMS fire detections for the Gulf Coast every {POLL_SECONDS}s.")
    print("Press the Stop/Interrupt button in Jupyter to end this.\n")

    try:
        while True:
            sent = poll_and_produce(records_url, auth_header, map_key)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"sent {sent} fire detection(s) to topic '{TOPIC}'")
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
