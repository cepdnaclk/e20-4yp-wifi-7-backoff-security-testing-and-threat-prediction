import json
import os
from typing import Optional

from confluent_kafka import Consumer
import psycopg2
from psycopg2.extras import execute_values
from pydantic import BaseModel, ValidationError
from dateutil import parser as dtparser

# Kafka / Redpanda
BROKERS = os.getenv("KAFKA_BROKERS", "bus-redpanda:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "wifi7.telemetry.v0_1")
GROUP_ID = os.getenv("KAFKA_GROUP", "harmonizer-udm-v0")
AUTO_OFFSET_RESET = os.getenv("AUTO_OFFSET_RESET", "earliest")

# Postgres (UDR)
PG_HOST = os.getenv("PG_HOST", "udr-db")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "udr")
PG_USER = os.getenv("PG_USER", "udr")
PG_PASS = os.getenv("PG_PASS", "udr_pass")

# Runtime
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "200"))
POLL_MS = int(os.getenv("POLL_MS", "1000"))


class TelemetryRecord(BaseModel):
    experiment_id: str
    ts: str
    source: str
    schema_version: str
    entity_id: str
    metric: str
    value: float
    unit: str


def main():
    print(f"[harmonizer] brokers={BROKERS} topic={TOPIC} group={GROUP_ID}")
    print(f"[harmonizer] pg={PG_HOST}:{PG_PORT}/{PG_DB}")

    consumer = Consumer({
        "bootstrap.servers": BROKERS,
        "group.id": GROUP_ID,
        "auto.offset.reset": AUTO_OFFSET_RESET,
        "enable.auto.commit": False,
    })
    consumer.subscribe([TOPIC])

    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS
    )
    conn.autocommit = False

    buffer = []

    try:
        while True:
            msg = consumer.poll(POLL_MS / 1000.0)
            if msg is None:
                continue
            if msg.error():
                print(f"[harmonizer] kafka error: {msg.error()}")
                continue

            try:
                payload = msg.value().decode("utf-8")
                raw = json.loads(payload)
                rec = TelemetryRecord(**raw)

                ts = dtparser.parse(rec.ts)  # timestamptz friendly

                buffer.append((
                    rec.experiment_id,
                    ts,
                    rec.entity_id,
                    rec.metric,     # -> metric_name
                    rec.value,
                    rec.unit,
                    rec.source
                ))

                if len(buffer) >= BATCH_SIZE:
                    flush(conn, buffer)
                    buffer.clear()
                    consumer.commit(asynchronous=False)

            except (json.JSONDecodeError, ValidationError) as e:
                print(f"[harmonizer] invalid message skipped: {e}")

            except Exception as e:
                # do not commit offset if db insert failed
                print(f"[harmonizer] processing error (no commit): {e}")

    finally:
        if buffer:
            flush(conn, buffer)
            consumer.commit(asynchronous=False)

        consumer.close()
        conn.close()


def flush(conn, rows):
    # Match your exact table schema:
    # (experiment_id, ts, entity_id, metric_name, value, unit, source, ingest_time default)
    sql = """
      INSERT INTO public.metrics
        (experiment_id, ts, entity_id, metric_name, value, unit, source)
      VALUES %s
      ON CONFLICT (experiment_id, ts, entity_id, metric_name, source)
      DO UPDATE SET
        value = EXCLUDED.value,
        unit = EXCLUDED.unit;
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=1000)
    conn.commit()
    print(f"[harmonizer] inserted/updated {len(rows)} rows")


if __name__ == "__main__":
    main()
