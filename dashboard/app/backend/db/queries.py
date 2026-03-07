import asyncpg
from datetime import datetime, timezone
from typing import Optional


# ── Experiments ──────────────────────────────────────────────────────────────

async def get_experiments(pool, limit=50, offset=0, prefix: Optional[str] = None):
    """Returns list of experiment summaries joining metrics and gcn_predictions."""
    sql = """
    WITH m AS (
        SELECT
            experiment_id,
            COUNT(*) AS metric_count,
            MIN(ts) AS first_ts,
            MAX(ts) AS last_ts
        FROM metrics
        GROUP BY experiment_id
    ),
    p AS (
        SELECT
            experiment_id,
            COUNT(*) AS segment_count,
            SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) AS attack_segments,
            ROUND(AVG(confidence)::numeric, 4) AS avg_confidence,
            MAX(model_version) AS model_version
        FROM gcn_predictions
        GROUP BY experiment_id
    )
    SELECT
        m.experiment_id,
        m.metric_count,
        m.first_ts,
        m.last_ts,
        COALESCE(p.segment_count, 0) AS segment_count,
        COALESCE(p.attack_segments, 0) AS attack_segments,
        p.avg_confidence,
        p.model_version
    FROM m
    LEFT JOIN p ON m.experiment_id = p.experiment_id
    """
    args = []
    if prefix:
        sql += " WHERE m.experiment_id LIKE $1"
        args.append(prefix + "%")
    sql += " ORDER BY m.last_ts DESC NULLS LAST"
    sql += f" LIMIT {limit} OFFSET {offset}"
    async with pool.acquire() as conn:
        return await conn.fetch(sql, *args)


async def count_experiments(pool, prefix: Optional[str] = None):
    sql = "SELECT COUNT(DISTINCT experiment_id) FROM metrics"
    args = []
    if prefix:
        sql += " WHERE experiment_id LIKE $1"
        args.append(prefix + "%")
    async with pool.acquire() as conn:
        return await conn.fetchval(sql, *args)


async def get_experiment_summary(pool, experiment_id: str):
    """Single experiment with full prediction stats."""
    sql = """
    SELECT
        COUNT(*) AS segment_count,
        SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) AS attack_segments,
        SUM(CASE WHEN prediction = 0 THEN 1 ELSE 0 END) AS normal_segments,
        ROUND(AVG(confidence)::numeric, 4) AS avg_confidence,
        ROUND(MIN(confidence)::numeric, 4) AS min_confidence,
        ROUND(MAX(confidence)::numeric, 4) AS max_confidence,
        ROUND(AVG(inference_time_ms)::numeric, 2) AS avg_inference_ms,
        MAX(model_version) AS model_version,
        MIN(ts_start) AS ts_start,
        MAX(ts_end) AS ts_end
    FROM gcn_predictions
    WHERE experiment_id = $1
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow(sql, experiment_id)


async def get_experiment_predictions(pool, experiment_id: str):
    sql = """
    SELECT
        id,
        segment_id,
        prediction,
        confidence,
        (probabilities->>0)::numeric AS p_normal,
        (probabilities->>1)::numeric AS p_attack,
        window_start_idx,
        window_end_idx,
        ts_start,
        ts_end,
        inference_time_ms,
        model_version
    FROM gcn_predictions
    WHERE experiment_id = $1
    ORDER BY ts_start
    """
    async with pool.acquire() as conn:
        return await conn.fetch(sql, experiment_id)


async def get_experiment_metric_series(
    pool,
    experiment_id: str,
    metric_name: str,
    entity_id: Optional[str] = None,
    downsample: int = 500,
):
    """Returns time-series data for a single metric, downsampled if needed."""
    if entity_id:
        count_sql = "SELECT COUNT(*) FROM metrics WHERE experiment_id = $1 AND metric_name = $2 AND entity_id = $3"
        args_count = [experiment_id, metric_name, entity_id]
    else:
        count_sql = "SELECT COUNT(*) FROM metrics WHERE experiment_id = $1 AND metric_name = $2"
        args_count = [experiment_id, metric_name]

    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql, *args_count)

    # Downsample by picking every Nth row
    step = max(1, total // downsample) if total else 1

    if entity_id:
        sql = """
        SELECT ts, value, entity_id, unit FROM (
            SELECT ts, value, entity_id, unit, ROW_NUMBER() OVER (ORDER BY ts) AS rn
            FROM metrics WHERE experiment_id = $1 AND metric_name = $2 AND entity_id = $3
        ) sub WHERE rn %% $4 = 0 ORDER BY ts
        """
        args = [experiment_id, metric_name, entity_id, step]
    else:
        sql = """
        SELECT ts, value, entity_id, unit FROM (
            SELECT ts, value, entity_id, unit, ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY ts) AS rn
            FROM metrics WHERE experiment_id = $1 AND metric_name = $2
        ) sub WHERE rn %% $3 = 0 ORDER BY ts
        """
        args = [experiment_id, metric_name, step]

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *args)

    # Also get unit from first row
    unit_sql = "SELECT unit FROM metrics WHERE experiment_id = $1 AND metric_name = $2 LIMIT 1"
    async with pool.acquire() as conn:
        unit = await conn.fetchval(unit_sql, experiment_id, metric_name) or ""

    return rows, unit


async def get_experiment_metrics_summary(pool, experiment_id: str):
    """Summary stats for all 13 metrics."""
    sql = """
    SELECT
        metric_name,
        unit,
        ROUND(AVG(value)::numeric, 4) AS avg_val,
        ROUND(MIN(value)::numeric, 4) AS min_val,
        ROUND(MAX(value)::numeric, 4) AS max_val,
        ROUND(STDDEV(value)::numeric, 4) AS std_val,
        ROUND((MAX(value) - MIN(value))::numeric, 4) AS range_val
    FROM metrics
    WHERE experiment_id = $1 AND entity_id = 'network'
    GROUP BY metric_name, unit
    ORDER BY metric_name
    """
    async with pool.acquire() as conn:
        return await conn.fetch(sql, experiment_id)


# ── Pipeline Status ───────────────────────────────────────────────────────────

async def get_pipeline_status(pool):
    """Compute current pipeline stage states from DB recency."""
    async with pool.acquire() as conn:
        # Latest experiment in metrics
        latest_exp_m = await conn.fetchval(
            "SELECT experiment_id FROM metrics ORDER BY ingest_time DESC LIMIT 1"
        )
        last_ingest = await conn.fetchval("SELECT MAX(ingest_time) FROM metrics")

        # Metrics count for latest experiment
        metrics_count = 0
        if latest_exp_m:
            metrics_count = await conn.fetchval(
                "SELECT COUNT(*) FROM metrics WHERE experiment_id = $1", latest_exp_m
            )

        # Latest experiment in gcn_predictions
        latest_exp_p = await conn.fetchval(
            "SELECT experiment_id FROM gcn_predictions ORDER BY created_at DESC LIMIT 1"
        )
        last_pred = await conn.fetchval("SELECT MAX(created_at) FROM gcn_predictions")

        segment_count = 0
        if latest_exp_p:
            segment_count = await conn.fetchval(
                "SELECT COUNT(DISTINCT segment_id) FROM gcn_predictions WHERE experiment_id = $1",
                latest_exp_p,
            )

        pred_count = await conn.fetchval("SELECT COUNT(*) FROM gcn_predictions") or 0

    now = datetime.now(timezone.utc)

    def seconds_since(ts):
        if not ts:
            return 9999
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (now - ts).total_seconds()

    ns3_age = seconds_since(last_ingest)
    gcn_age = seconds_since(last_pred)

    def stage_state(age, threshold=60):
        if age < threshold:
            return "active"
        elif age < 3600:
            return "idle"
        return "idle"

    return {
        "ns3": {
            "state": stage_state(ns3_age, 60),
            "counter": int(metrics_count),
            "label": "events",
            "last_activity_ts": last_ingest,
        },
        "exporter": {
            "state": stage_state(ns3_age, 60),
            "counter": int(metrics_count),
            "label": "sent",
            "last_activity_ts": last_ingest,
        },
        "kafka": {
            "state": stage_state(ns3_age, 60),
            "counter": int(metrics_count),
            "label": "stored",
            "last_activity_ts": last_ingest,
        },
        "windowizer": {
            "state": stage_state(gcn_age, 120),
            "counter": int(segment_count),
            "label": "segments",
            "last_activity_ts": last_pred,
        },
        "gcn": {
            "state": stage_state(gcn_age, 120),
            "counter": int(segment_count),
            "label": "predictions",
            "last_activity_ts": last_pred,
        },
        "db": {
            "state": "active" if pred_count > 0 else "idle",
            "counter": int(pred_count),
            "label": "total",
            "last_activity_ts": last_pred,
        },
    }, latest_exp_p or latest_exp_m


async def get_new_predictions(pool, after_id: int):
    sql = """
    SELECT id, experiment_id, segment_id, prediction, confidence, created_at, model_version
    FROM gcn_predictions
    WHERE id > $1
    ORDER BY id ASC
    LIMIT 10
    """
    async with pool.acquire() as conn:
        return await conn.fetch(sql, after_id)


# ── Analysis ──────────────────────────────────────────────────────────────────

async def get_analysis_summary(pool, model_version: Optional[str] = None):
    """Cross-experiment TP/TN/FP/FN based on experiment_id naming convention."""
    mv_filter = "AND model_version = $1" if model_version else ""
    args = [model_version] if model_version else []
    sql = f"""
    SELECT
        COUNT(*) AS total_segments,
        SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) AS total_attacks,
        SUM(CASE WHEN prediction = 0 THEN 1 ELSE 0 END) AS total_normals,
        -- True positives: predicted attack AND experiment is an attack
        SUM(CASE WHEN prediction = 1 AND (experiment_id ILIKE '%attack%' OR experiment_id ILIKE '%positive%' OR experiment_id ILIKE '%negative%') THEN 1 ELSE 0 END) AS tp,
        -- True negatives: predicted normal AND experiment is normal
        SUM(CASE WHEN prediction = 0 AND experiment_id ILIKE '%normal%' THEN 1 ELSE 0 END) AS tn,
        -- False positives: predicted attack AND experiment is normal
        SUM(CASE WHEN prediction = 1 AND experiment_id ILIKE '%normal%' THEN 1 ELSE 0 END) AS fp,
        -- False negatives: predicted normal AND experiment is attack
        SUM(CASE WHEN prediction = 0 AND (experiment_id ILIKE '%attack%' OR experiment_id ILIKE '%positive%' OR experiment_id ILIKE '%negative%') THEN 1 ELSE 0 END) AS fn
    FROM gcn_predictions
    WHERE 1=1 {mv_filter}
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow(sql, *args)


async def get_confidence_histogram(pool, bins: int = 10):
    sql = """
    WITH bins AS (
        SELECT
            prediction,
            WIDTH_BUCKET(confidence, 0, 1.0001, $1) AS bin_idx,
            COUNT(*) AS cnt
        FROM gcn_predictions
        GROUP BY prediction, bin_idx
    )
    SELECT prediction, bin_idx, cnt FROM bins ORDER BY prediction, bin_idx
    """
    async with pool.acquire() as conn:
        return await conn.fetch(sql, bins)


async def get_attack_by_type(pool):
    sql = """
    SELECT
        CASE
            WHEN experiment_id ILIKE '%attack-neg%' OR experiment_id ILIKE '%negative%' THEN 'attack-neg'
            WHEN experiment_id ILIKE '%attack-pos%' OR experiment_id ILIKE '%positive%' THEN 'attack-pos'
            WHEN experiment_id ILIKE '%normal%' THEN 'normal'
            ELSE 'unknown'
        END AS exp_type,
        COUNT(*) AS total_segments,
        SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) AS attack_segments
    FROM gcn_predictions
    GROUP BY exp_type
    ORDER BY exp_type
    """
    async with pool.acquire() as conn:
        return await conn.fetch(sql)


async def get_inference_stats(pool):
    sql = """
    SELECT
        COUNT(*) AS count,
        MIN(inference_time_ms) AS min_ms,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY inference_time_ms::float) AS p50_ms,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY inference_time_ms::float) AS p95_ms,
        MAX(inference_time_ms) AS max_ms,
        ROUND(AVG(inference_time_ms)::numeric, 2) AS avg_ms
    FROM gcn_predictions
    WHERE inference_time_ms IS NOT NULL
    """
    async with pool.acquire() as conn:
        return await conn.fetchrow(sql)
