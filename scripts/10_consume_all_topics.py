"""
Step 8: Kafka consumer -- reads messages back out of all 3 live topics.

This is what Manoj's dashboard (or anyone else on the team) uses to
actually read the data your producers are sending into Kafka. It
subscribes to all three topics and prints each message as it arrives.

IMPORTANT -- which connection method to use:
  This uses the NATIVE Kafka protocol (confluent_kafka), not the REST
  workaround from the producer scripts. That's intentional: the REST
  method was only needed because datascience.tamucc.edu specifically
  blocks port 9092. If this consumer runs somewhere else (Manoj's own
  machine, Streamlit Cloud, etc.), the native protocol should work fine
  and is simpler/faster for continuous consuming.

  If you (Malav) run this on datascience.tamucc.edu to test it, you'll
  likely hit the same "Connection refused" error as before -- that's
  expected, not a new bug. If that happens, let me know and I'll build
  a REST-based polling version of this consumer too.

Credentials: read from kafka_credentials.properties (same gitignored
file as the producers).
"""

import json

from confluent_kafka import Consumer

TOPICS = ["noaa-weather-alerts", "usgs-earthquakes", "nasa-firms-fires"]
CREDENTIALS_PATH = "kafka_credentials.properties"
GROUP_ID = "capstone-dashboard-consumer"


def load_kafka_config(path: str) -> dict:
    config = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            config[key.strip()] = value.strip()
    required = ["bootstrap.servers", "security.protocol", "sasl.mechanisms",
                "sasl.username", "sasl.password"]
    missing = [k for k in required if k not in config]
    if missing:
        raise ValueError(f"{path} is missing required keys: {missing}")
    return {k: config[k] for k in required}


def main():
    config = load_kafka_config(CREDENTIALS_PATH)
    config["group.id"] = GROUP_ID
    # "earliest" so a fresh consumer sees everything already sitting in the
    # topic, not just new messages from this point forward -- useful for
    # testing/demoing. A production dashboard might prefer "latest".
    config["auto.offset.reset"] = "earliest"

    consumer = Consumer(config)
    consumer.subscribe(TOPICS)

    print(f"Subscribed to: {TOPICS}")
    print("Waiting for messages ... (Ctrl+C / Stop button to end)\n")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"  Consumer error: {msg.error()}")
                continue

            topic = msg.topic()
            try:
                value = json.loads(msg.value().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                value = msg.value()

            print(f"--- [{topic}] key={msg.key()} ---")
            print(json.dumps(value, indent=2)[:500])  # truncate long records
            print()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
