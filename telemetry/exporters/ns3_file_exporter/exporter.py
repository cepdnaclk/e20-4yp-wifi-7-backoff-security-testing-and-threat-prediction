# telemetry/exporters/ns3_file_exporter/exporter.py
"""
ns-3 Telemetry File Exporter

Reads telemetry.jsonl files and publishes to Kafka with at-least-once delivery.

CRITICAL: This exporter uses counter-based delivery confirmation.
State is ONLY saved after ALL messages are confirmed delivered.
This prevents data loss when Kafka is unavailable.

See ADR-WP7.5-01 for design rationale.
"""
import json
import os
import sys
import time
from typing import Optional, Any, Dict

from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient
from pydantic import BaseModel, ValidationError
from dateutil import parser as dtparser


TOPIC = os.getenv("KAFKA_TOPIC", "wifi7.telemetry.v0_1")
BROKERS = os.getenv("KAFKA_BROKERS", "bus-redpanda:9092")
TELEMETRY_FILE = os.getenv("TELEMETRY_FILE")  # must be set
SOURCE = os.getenv("SOURCE", "ns3")
SCHEMA_VERSION = os.getenv("SCHEMA_VERSION", "v0.1")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "0.25"))
FLUSH_TIMEOUT = float(os.getenv("FLUSH_TIMEOUT", "30.0"))

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


def check_broker_health() -> None:
    """
    Verify broker is reachable and topic exists before processing.

    Fails fast with clear error message if:
    - Broker is unreachable
    - Topic does not exist

    This prevents silent data loss when Kafka infrastructure is missing.
    See ADR-WP7.5-02 for rationale.
    """
    print(f"[exporter] checking broker health: {BROKERS}")

    try:
        admin_client = AdminClient({"bootstrap.servers": BROKERS})

        # List topics with timeout
        metadata = admin_client.list_topics(timeout=10)

        # Check if our topic exists
        if TOPIC not in metadata.topics:
            print(f"\n{'='*70}")
            print(f"FATAL ERROR: Kafka topic '{TOPIC}' does not exist")
            print(f"{'='*70}")
            print(f"\nThe exporter cannot publish to a non-existent topic.")
            print(f"This would cause silent data loss.")
            print(f"\nTo fix this, create the topic first:")
            print(f"  make kafka-init")
            print(f"\nOr manually:")
            print(f"  docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \\")
            print(f"    rpk topic create {TOPIC} --brokers localhost:9092")
            print(f"\n{'='*70}")
            raise SystemExit(1)

        print(f"[exporter] health check PASSED: topic '{TOPIC}' exists")

    except Exception as e:
        if "SystemExit" in str(type(e)):
            raise
        print(f"\n{'='*70}")
        print(f"FATAL ERROR: Cannot connect to Kafka broker")
        print(f"{'='*70}")
        print(f"\nBroker: {BROKERS}")
        print(f"Error: {e}")
        print(f"\nEnsure Kafka/Redpanda is running:")
        print(f"  make status")
        print(f"\n{'='*70}")
        raise SystemExit(1)


def main():
    if not TELEMETRY_FILE:
        raise SystemExit("TELEMETRY_FILE env is required (path to telemetry.jsonl)")

    producer = Producer({"bootstrap.servers": BROKERS})
    state = load_state()
    offset = get_offset(state, TELEMETRY_FILE)

    print(f"[exporter] brokers={BROKERS} topic={TOPIC}")
    print(f"[exporter] file={TELEMETRY_FILE} resume_offset={offset}")

    # Health check: verify topic exists before processing
    check_broker_health()

    while True:
        if not os.path.exists(TELEMETRY_FILE):
            time.sleep(1.0)
            continue

        # ========================================================
        # COUNTER-BASED DELIVERY TRACKING
        # ========================================================
        # We use simple counters instead of offset tracking because:
        # 1. min(confirmed_offsets) causes infinite replays
        # 2. max(confirmed_offsets) skips failed messages
        # 3. Simple counts are thread-safe and handle out-of-order callbacks
        # See ADR-WP7.5-01 for detailed rationale.
        # ========================================================

        confirmed_count = 0
        total_sent = 0
        delivery_errors = []

        def delivery_report(err, msg):
            """
            Callback invoked when message delivery completes.

            This callback runs on the producer's background thread.
            We only increment counters (atomic operations) - no file I/O.
            """
            nonlocal confirmed_count
            if err is not None:
                error_msg = f"{err}"
                delivery_errors.append(error_msg)
                print(f"[exporter] ERROR: Message delivery failed: {error_msg}")
            else:
                confirmed_count += 1
                # Log progress every 50 messages
                if confirmed_count % 50 == 0:
                    print(f"[exporter] delivered {confirmed_count} messages")

        with open(TELEMETRY_FILE, "r", encoding="utf-8") as f:
            # Seek to last confirmed position
            f.seek(offset)

            print(f"[exporter] reading from offset {offset}")

            # Read ENTIRE file from offset to end
            while True:
                line = f.readline()
                if not line:
                    break

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

                    # Enqueue message (async, non-blocking)
                    producer.produce(
                        TOPIC,
                        key=key.encode("utf-8"),
                        value=json.dumps(rec.model_dump()).encode("utf-8"),
                        callback=delivery_report,
                    )
                    total_sent += 1

                    # Process callbacks (non-blocking)
                    producer.poll(0)

                    # DO NOT save_offset() here!
                    # That was the bug - saving before delivery confirmed.
                    # State is saved ONLY after ALL messages are confirmed.

                except (json.JSONDecodeError, ValidationError) as e:
                    print(f"[exporter] invalid line skipped: {e}")

            # Capture final file position BEFORE flush
            # This is where we stopped reading (end of new data)
            final_offset = f.tell()

        # ========================================================
        # FLUSH AND VERIFY ALL DELIVERIES
        # ========================================================
        # Wait for ALL pending messages to be delivered.
        # Only save state if ALL messages confirmed successfully.
        # ========================================================

        if total_sent > 0:
            print(f"[exporter] flushing {total_sent} messages (confirmed so far: {confirmed_count})...")
            outstanding = producer.flush(timeout=FLUSH_TIMEOUT)

            # Check for timeout
            if outstanding > 0:
                error_msg = f"{outstanding} messages did not flush within {FLUSH_TIMEOUT}s timeout"
                print(f"[exporter] FATAL: {error_msg}")
                print(f"[exporter] State NOT saved - will retry from offset {offset} on next run")
                raise SystemExit(f"Exporter failed: {error_msg}")

            # Check for delivery errors
            if delivery_errors:
                print(f"[exporter] FATAL: {len(delivery_errors)} delivery error(s):")
                for error in delivery_errors[:10]:  # Show first 10
                    print(f"  - {error}")
                print(f"[exporter] State NOT saved - will retry from offset {offset} on next run")
                raise SystemExit(f"Exporter failed: {len(delivery_errors)} messages not delivered")

            # Verify all messages confirmed
            if confirmed_count != total_sent:
                print(f"[exporter] FATAL: Sent {total_sent} but only confirmed {confirmed_count}")
                print(f"[exporter] State NOT saved - will retry from offset {offset} on next run")
                raise SystemExit(f"Exporter failed: delivery count mismatch")

            # ========================================================
            # ALL MESSAGES DELIVERED SUCCESSFULLY
            # ========================================================
            # NOW and ONLY NOW is it safe to save state.
            # ========================================================
            print(f"[exporter] SUCCESS: All {confirmed_count} messages delivered")
            print(f"[exporter] saving offset={final_offset}")
            save_offset(state, TELEMETRY_FILE, final_offset)
            offset = final_offset  # Update for next iteration
        else:
            print(f"[exporter] no new messages in file")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
