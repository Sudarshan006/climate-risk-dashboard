"""
Step 5: Kafka live pipeline -- NOAA weather alerts producer (REST version).

Polls the National Weather Service's live alerts feed for the 5 Gulf Coast
states on a regular interval and sends each active alert into the Kafka
topic "noaa-weather-alerts" on Confluent Cloud.

Why REST instead of the native Kafka protocol: the native protocol needs
an outbound connection on port 9092, which datascience.tamucc.edu's
Jupyter server blocks (confirmed -- "Connection refused" on 9092).
Confluent Cloud's Kafka REST API v3 does the same job over plain HTTPS
(port 443), which is never blocked since it's the same port normal web
browsing uses. Docs: https://docs.confluent.io/cloud/current/kafka-rest/kafka-rest-cc.html

Source: api.weather.gov/alerts/active?area={STATE} -- no API key needed.
Schema confirmed live via 07a_inspect_noaa_alerts.py.

Credentials: read from kafka_credentials.properties (NOT committed to
GitHub -- see .gitignore). Needs these keys in that file:
  sasl.username, sasl.password   (your Confluent API key/secret)
  rest.endpoint                   (e.g. https://pkc-xxxxx....confluent.cloud:443)
  cluster.id                      (e.g. lkc-xxxxxxxx)

This runs forever, polling every POLL_SECONDS, until you stop it
(Kernel -> Interrupt in Jupyter, or the stop/square button on the cell).
"""

import base64
import json
import time
import urllib.request

GULF_STATES = ["TX", "LA", "MS", "AL", "FL"]
TOPIC = "noaa-weather-alerts"
POLL_SECONDS = 300  # 5 minutes -- NWS alerts don't change second-to-second
CREDENTIALS_PATH = "kafka_credentials.properties"


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
        raise ValueError(
            f"{path} is missing required keys: {missing}. "
            f"Make sure you added rest.endpoint and cluster.id to it."
        )
    return config


def fetch_alerts(state: str) -> list[dict]:
    url = f"https://api.weather.gov/alerts/active?area={state}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "capstone-data-pipeline (student project, contact: patelmalav1234@gmail.com)",
        "Accept": "application/geo+json",
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
        resp.read()  # just confirm it didn't raise; response body not needed


def poll_and_produce(records_url: str, auth_header: str) -> int:
    sent = 0
    failed = 0
    for state in GULF_STATES:
        try:
            alerts = fetch_alerts(state)
        except Exception as e:  # noqa: BLE001
            print(f"  Couldn't fetch alerts for {state}: {e}")
            continue

        for alert in alerts:
            props = alert.get("properties", {})
            record = {
                "id": props.get("id"),
                "state": state,
                "event": props.get("event"),
                "severity": props.get("severity"),
                "certainty": props.get("certainty"),
                "urgency": props.get("urgency"),
                "areaDesc": props.get("areaDesc"),
                "headline": props.get("headline"),
                "effective": props.get("effective"),
                "expires": props.get("expires"),
                "ends": props.get("ends"),
                "description": props.get("description"),
            }
            key = record["id"] or f"{state}-unknown"
            try:
                produce_record(records_url, auth_header, key, record)
                sent += 1
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"  FAILED to send alert {key}: {e}")

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
    print(f"Polling NOAA alerts for {GULF_STATES} every {POLL_SECONDS}s.")
    print("Press the Stop/Interrupt button in Jupyter to end this.\n")

    try:
        while True:
            sent = poll_and_produce(records_url, auth_header)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"sent {sent} active alert(s) to topic '{TOPIC}'")
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
