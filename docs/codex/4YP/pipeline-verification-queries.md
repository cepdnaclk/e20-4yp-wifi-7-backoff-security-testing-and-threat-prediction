# Pipeline Verification Queries (End-to-End)

This note lists the commands and queries to verify the full pipeline:
ns-3 -> telemetry.jsonl -> exporter -> Kafka -> harmonizer -> DB -> Grafana.

Use these in order when troubleshooting.

---

## 1) Services Up (Containerlab)

```bash
make status
```

Expected: redpanda, grafana, and udr-db are running.

---

## 2) Pipeline Service (Harmonizer)

```bash
make pipeline-status
```

Expected: `ndt-pipeline-harmonizer` is `Up`.

If logs show old errors and you want to replay data:
```bash
make pipeline-down
KAFKA_GROUP=harmonizer-replay-$(date +%s) AUTO_OFFSET_RESET=earliest make pipeline-up
```

---

## 3) Kafka Topic Exists

```bash
make kafka-list
```

Expected: `wifi7.telemetry.v0_1` appears in the list.

If missing:
```bash
make kafka-init
```

---

## 4) Exporter State (File Offsets)

```bash
make exporter-state
```

Expected: your experiment file appears with a non-zero offset.

To re-export a specific experiment:
```bash
make exporter-reset-exp EXP_ID=20260103-1400-mlo-normal-42
make exporter-run EXP_ID=20260103-1400-mlo-normal-42
```

---

## 5) Kafka Has Messages

```bash
docker exec -it clab-ndt-wifi7-mlo-security-bus-redpanda \
  rpk topic consume wifi7.telemetry.v0_1 -o oldest -n 5
```

Expected: JSON messages appear.

---

## 6) Database Has Rows

Total row count:
```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT COUNT(*) FROM metrics;"
```

Per-experiment counts:
```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "
  SELECT experiment_id, COUNT(*) AS row_count
  FROM metrics
  WHERE experiment_id IN (
    '20260103-1400-mlo-normal-42',
    '20260103-1400-mlo-attack-pos-42',
    '20260103-1400-mlo-attack-neg-42'
  )
  GROUP BY experiment_id
  ORDER BY experiment_id;
"
```

Latest rows:
```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "SELECT experiment_id, ts, metric_name, value FROM metrics ORDER BY ts DESC LIMIT 10;"
```

---

## 7) Table Schema (Fields)

```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "\d metrics"
```

Detailed columns:
```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "
  SELECT column_name, data_type, is_nullable, column_default
  FROM information_schema.columns
  WHERE table_schema = 'public' AND table_name = 'metrics'
  ORDER BY ordinal_position;
"
```

---

## 8) Window Reconstruction (MLO)

Each `ts` is one window; each window has 13 metrics.

List window timestamps:
```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "
  SELECT ts, COUNT(*) AS metrics_in_window
  FROM metrics
  WHERE experiment_id = '20260103-1400-mlo-attack-neg-42'
  GROUP BY ts
  ORDER BY ts
  LIMIT 5;
"
```

Full window (all metrics for one timestamp):
```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "
  SELECT metric_name, value, unit
  FROM metrics
  WHERE experiment_id = '20260103-1400-mlo-attack-neg-42'
    AND ts = '2026-01-04 11:52:41.9+00'
  ORDER BY metric_name;
"
```

Rebuild a JSON-style window row:
```bash
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "
  SELECT ts,
         jsonb_object_agg(metric_name, value ORDER BY metric_name) AS window_metrics
  FROM metrics
  WHERE experiment_id = '20260103-1400-mlo-attack-neg-42'
  GROUP BY ts
  ORDER BY ts
  LIMIT 3;
"
```

If you want the original window index, compute it from `start_time` in
`sim/ns3/artifacts/<EXP_ID>/meta.txt` and 0.1s windows.

---

## 9) Grafana Sanity Checks

- The simulation timestamps are in 2026. Adjust the Grafana time picker
  to include those dates.
- If Grafana is empty but DB has rows, the time range is the first thing to check.

---

## 10) Common Recovery Steps

1) Topic missing:
```bash
make kafka-init
```

2) Re-export a single experiment:
```bash
make exporter-reset-exp EXP_ID=20260103-1400-mlo-normal-42
make exporter-run EXP_ID=20260103-1400-mlo-normal-42
```

3) Replay from Kafka into DB:
```bash
make pipeline-down
KAFKA_GROUP=harmonizer-replay-$(date +%s) AUTO_OFFSET_RESET=earliest make pipeline-up
```
