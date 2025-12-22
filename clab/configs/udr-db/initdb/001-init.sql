-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Minimal tables (WP2 skeleton) - final schema will come in WP6
CREATE TABLE IF NOT EXISTS snapshots (
  id bigserial PRIMARY KEY,
  experiment_id text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  topology_json jsonb,
  config_json jsonb,
  git_sha text,
  ns3_version text,
  schema_version text
);

CREATE TABLE IF NOT EXISTS metrics (
  experiment_id text NOT NULL,
  ts timestamptz NOT NULL,
  entity_id text NOT NULL,
  metric_name text NOT NULL,
  value double precision NOT NULL,
  unit text NOT NULL,
  source text NOT NULL,
  ingest_time timestamptz NOT NULL DEFAULT now()
);

-- Convert metrics into a hypertable (safe if repeated)
SELECT create_hypertable('metrics', 'ts', if_not_exists => TRUE);
