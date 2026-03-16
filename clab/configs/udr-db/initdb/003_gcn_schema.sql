-- GCN Attack Detection Schema
-- WP8: Integration of GCN model for real-time attack detection
-- Created: 2026-02-10

-- ============================================================================
-- Table: gcn_predictions
-- Purpose: Store GCN model predictions (attack vs normal) for telemetry segments
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.gcn_predictions (
    id BIGSERIAL PRIMARY KEY,

    -- Identifiers
    experiment_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    segment_id TEXT NOT NULL,

    -- Time range for this segment
    ts_start TIMESTAMPTZ NOT NULL,
    ts_end TIMESTAMPTZ NOT NULL,

    -- Window indices (for traceability)
    window_start_idx INTEGER NOT NULL,
    window_end_idx INTEGER NOT NULL,

    -- Prediction results
    prediction INTEGER NOT NULL,              -- 0=Normal, 1=Attack
    confidence DOUBLE PRECISION NOT NULL,     -- max(probabilities)
    probabilities JSONB NOT NULL,             -- [p_normal, p_attack]

    -- Model metadata
    model_version TEXT NOT NULL,
    model_path TEXT NOT NULL,

    -- Performance metrics
    inference_time_ms DOUBLE PRECISION,

    -- Provenance
    source TEXT NOT NULL DEFAULT 'gcn-detector',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT prediction_valid CHECK (prediction IN (0, 1)),
    CONSTRAINT confidence_valid CHECK (confidence >= 0 AND confidence <= 1),
    CONSTRAINT window_indices_valid CHECK (window_end_idx >= window_start_idx)
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS gcn_pred_exp_ts_idx
  ON public.gcn_predictions (experiment_id, ts_start DESC);

CREATE INDEX IF NOT EXISTS gcn_pred_entity_ts_idx
  ON public.gcn_predictions (entity_id, ts_start DESC);

CREATE INDEX IF NOT EXISTS gcn_pred_attack_idx
  ON public.gcn_predictions (prediction, ts_start DESC)
  WHERE prediction = 1;

CREATE INDEX IF NOT EXISTS gcn_pred_created_idx
  ON public.gcn_predictions (created_at DESC);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('gcn_predictions', 'ts_start',
                        if_not_exists => TRUE,
                        chunk_time_interval => INTERVAL '1 day');

-- Add compression policy (compress chunks older than 7 days)
SELECT add_compression_policy('gcn_predictions',
                             INTERVAL '7 days',
                             if_not_exists => TRUE);

COMMENT ON TABLE public.gcn_predictions IS
  'GCN model predictions for WiFi 7 attack detection';
COMMENT ON COLUMN public.gcn_predictions.prediction IS
  '0=Normal, 1=Attack';
COMMENT ON COLUMN public.gcn_predictions.confidence IS
  'Maximum probability (confidence score)';
COMMENT ON COLUMN public.gcn_predictions.probabilities IS
  'JSON array: [p_normal, p_attack]';

-- ============================================================================
-- Table: model_registry
-- Purpose: Track deployed GCN models and their metadata
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.model_registry (
    id BIGSERIAL PRIMARY KEY,

    -- Model identification
    version TEXT UNIQUE NOT NULL,
    model_path TEXT NOT NULL,

    -- Model metadata
    metadata JSONB NOT NULL,                  -- Training config, hyperparameters
    performance_metrics JSONB NOT NULL,       -- Test accuracy, F1, precision, recall

    -- Deployment status
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    deployed_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,

    -- Notes
    notes TEXT,

    -- Constraints
    CONSTRAINT version_format CHECK (version ~ '^v\d+\.\d+\.\d+$')
);

-- Only one active model at a time
CREATE UNIQUE INDEX IF NOT EXISTS one_active_model
  ON public.model_registry (is_active)
  WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS model_reg_version_idx
  ON public.model_registry (version);

CREATE INDEX IF NOT EXISTS model_reg_created_idx
  ON public.model_registry (created_at DESC);

COMMENT ON TABLE public.model_registry IS
  'Version control and metadata for deployed GCN models';
COMMENT ON COLUMN public.model_registry.is_active IS
  'Only one model can be active at a time';
COMMENT ON COLUMN public.model_registry.metadata IS
  'JSON containing training dataset, hyperparameters, etc.';
COMMENT ON COLUMN public.model_registry.performance_metrics IS
  'JSON containing test accuracy, F1, precision, recall, ROC-AUC';

-- ============================================================================
-- Grant permissions
-- ============================================================================

GRANT SELECT, INSERT ON public.gcn_predictions TO udr;
GRANT USAGE, SELECT ON SEQUENCE gcn_predictions_id_seq TO udr;

GRANT SELECT, INSERT, UPDATE ON public.model_registry TO udr;
GRANT USAGE, SELECT ON SEQUENCE model_registry_id_seq TO udr;

-- ============================================================================
-- Initial data: Register the baseline model (v1.0.0)
-- ============================================================================

INSERT INTO public.model_registry (
    version,
    model_path,
    metadata,
    performance_metrics,
    is_active,
    deployed_at,
    notes
) VALUES (
    'v1.0.0',
    'twin/registry/gcn/v1.0.0',
    '{
        "in_channels": 16,
        "hidden_channels": 64,
        "num_layers": 2,
        "dropout": 0.3,
        "pooling": "mean",
        "segment_length": 256,
        "training_dataset": "Wifi7_Datasets (3 scenarios)",
        "trained_by": "cobrakali",
        "git_commit": "9f0139f"
    }'::jsonb,
    '{
        "test_accuracy": 0.9523,
        "test_f1": 0.9481,
        "test_precision": 0.9612,
        "test_recall": 0.9354,
        "test_roc_auc": 0.9891
    }'::jsonb,
    TRUE,
    NOW(),
    'Baseline GCN model trained on 3 attack scenarios (Normal, Positive, Negative)'
) ON CONFLICT (version) DO NOTHING;

-- ============================================================================
-- End of GCN schema
-- ============================================================================
