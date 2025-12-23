-- Prevent duplicates on replay
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE indexname = 'uq_metrics_idem'
  ) THEN
    CREATE UNIQUE INDEX uq_metrics_idem
      ON public.metrics (experiment_id, ts, entity_id, metric_name, source);
  END IF;
END$$;

-- Helpful query index for dashboards
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE indexname = 'ix_metrics_exp_metric_ts'
  ) THEN
    CREATE INDEX ix_metrics_exp_metric_ts
      ON public.metrics (experiment_id, metric_name, ts DESC);
  END IF;
END$$;
