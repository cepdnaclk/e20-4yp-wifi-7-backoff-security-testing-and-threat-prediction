# telemetry/exporters/ns3_file_exporter/exporter.py
import json
import os
import time
from typing import Optional, Any, Dict

from confluent_kafka import Producer
from pydantic import BaseModel, ValidationError
from dateutil import parser as dtparser


TOPIC = os.getenv("KAFKA_TOPIC", "wifi7.telemetry.v0_1")
BROKERS = os.getenv("KAFKA_BROKERS", "bus-redpanda:9092")
TELEMETRY_FILE = os.getenv("TELEMETRY_FILE")  # must be set
SOURCE = os.getenv("SOURCE", "ns3")
SCHEMA_VERSION = os.getenv("SCHEMA_VERSION", "v0.1")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "0.25"))

STATE_FILE = os.getenv("STATE_FILE", "/state/exporter_state.json")


class TelemetryRecord(BaseModel):
    experiment_id: str
    ts: Any  # ISO string or epoch ms (int)
    source: str
    schema_version: str
    entity_id: str
    metric: str
    value: float
    unit: str


def normalize_ts(ts: Any) -> str:
    # Store ISO string in Kafka (stable), regardless of input.
    if isinstance(ts, int):
        # epoch milliseconds
        return dtparser.parse(time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(ts / 1000))).isoformat() + "Z"
    if isinstance(ts, str):
        # accept ISO-8601
        return dtparser.parse(ts).isoformat()
    # fallback: now
    return dtparser.parse(time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime())).isoformat() + "Z"


def load_state() -> Dict[str, Any]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "files" in data and isinstance(data["files"], dict):
                return data
            return {"files": {}}
    except FileNotFoundError:
        return {"files": {}}


def get_offset(state: Dict[str, Any], path: str) -> int:
    return int(state.get("files", {}).get(path, 0))


def save_offset(state: Dict[str, Any], path: str, offset: int) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    state.setdefault("files", {})
    state["files"][path] = offset
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)



def delivery_report(err, msg):
    if err is not None:
        print(f"[exporter] delivery failed: {err}")


def main():
    if not TELEMETRY_FILE:
        raise SystemExit("TELEMETRY_FILE env is required (path to telemetry.jsonl)")

    producer = Producer({"bootstrap.servers": BROKERS})
    state = load_state()
    offset = get_offset(state, TELEMETRY_FILE)

    print(f"[exporter] brokers={BROKERS} topic={TOPIC}")
    print(f"[exporter] file={TELEMETRY_FILE} resume_offset={offset}")

    while True:
        if not os.path.exists(TELEMETRY_FILE):
            time.sleep(1.0)
            continue

        with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
            f.seek(offset)

            while True:
                line = f.readline()
                if not line:
                    break

                offset = f.tell()

                line = line.strip()
                if not line:
                    continue

                try:
                    raw = json.loads(line)
                    raw["source"] = raw.get("source", SOURCE)
                    raw["schema_version"] = raw.get("schema_version", SCHEMA_VERSION)
                    raw["ts"] = normalize_ts(raw.get("ts"))

                    rec = TelemetryRecord(**raw)

                    # Deterministic key helps idempotency downstream
                    key = f"{rec.experiment_id}|{rec.entity_id}|{rec.metric}|{rec.ts}"
                    producer.produce(
                        TOPIC,
                        key=key.encode("utf-8"),
                        value=json.dumps(rec.model_dump()).encode("utf-8"),
                        callback=delivery_report,
                    )
                    producer.poll(0)

                    # persist state after successful enqueue
                    save_offset(state, TELEMETRY_FILE, offset)

                except (json.JSONDecodeError, ValidationError) as e:
                    print(f"[exporter] invalid line skipped: {e}")

        producer.flush(1.0)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
