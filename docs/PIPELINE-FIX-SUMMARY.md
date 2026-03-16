# WiFi 7 MLO Security Pipeline - Fix Summary

**Date**: 2026-02-15
**Status**: Data pipeline fixed, Model requires retraining, Dashboard functional

---

## Problem Statement

GCN model v2.0.0 was predicting **100% false positives** - detecting ALL traffic (including normal) as attacks.

---

## Root Causes Identified

### 1. Field Name Mismatch in Delta Converter
**Location**: `security/detector/windowizer/delta_converter.py`

**Problem**:
- Training data used: `mac_tx_delta`, `mac_rx_delta`, `mac_ack_delta`, `mac_retrans_delta`, `mac_drop_delta`, `phy_drop_delta`
- Windowizer was emitting: `mac_total_tx`, `mac_total_rx`, `mac_total_ack`, `mac_total_retrans`, `mac_drop_count`, `phy_drop_count`

**Fix**:
```python
# Added field name mapping
field_name_map = {
    'mac_total_tx': 'mac_tx_delta',
    'mac_total_rx': 'mac_rx_delta',
    'mac_total_ack': 'mac_ack_delta',
    'mac_total_retrans': 'mac_retrans_delta',
    'mac_drop_count': 'mac_drop_delta',
    'phy_drop_count': 'phy_drop_delta'
}
```

### 2. Field Name Mismatch in Feature Processor
**Location**: `twin/gnn/detector/feature_processor.py`

**Problem**:
- Feature processor was looking for old field names (mac_total_tx, etc.)
- Windowizer was now sending new field names (mac_tx_delta, etc.)

**Fix**:
```python
# Updated base_feature_keys
self.base_feature_keys = [
    'net_throughput_mbps',
    'net_avg_delay_ms',
    'net_avg_jitter_ms',
    'net_packet_loss_ratio',
    'net_active_flows',
    'mac_tx_delta',      # Changed from mac_total_tx
    'mac_rx_delta',      # Changed from mac_total_rx
    'mac_ack_delta',     # Changed from mac_total_ack
    'mac_retrans_delta', # Changed from mac_total_retrans
    'mac_drop_delta',    # Changed from mac_drop_count
    'phy_drop_delta',    # Changed from phy_drop_count
    'avg_backoff_slots',
    'channel_busy_ratio'
]
```

---

## Verification Results

### ✅ Data Pipeline - FIXED
```bash
# Kafka segments now have CORRECT field names
$ rpk topic consume wifi7.ml.windowed_features.v1 -n 1

Window fields:
[
  'avg_backoff_slots',
  'channel_busy_ratio',
  'mac_ack_delta',     ✓ CORRECT
  'mac_drop_delta',    ✓ CORRECT
  'mac_retrans_delta', ✓ CORRECT
  'mac_rx_delta',      ✓ CORRECT
  'mac_tx_delta',      ✓ CORRECT
  'net_active_flows',
  'net_avg_delay_ms',
  'net_avg_jitter_ms',
  'net_packet_loss_ratio',
  'net_throughput_mbps',
  'phy_drop_delta',    ✓ CORRECT
  'ts',
  'window_idx'
]
```

### ❌ Model Predictions - STILL BROKEN
```sql
-- Model v2.0.0 predictions (after all fixes)
SELECT experiment_id,
       COUNT(*) as total,
       SUM(CASE WHEN prediction=1 THEN 1 ELSE 0 END) as attacks,
       SUM(CASE WHEN prediction=0 THEN 1 ELSE 0 END) as normal
FROM gcn_predictions
WHERE experiment_id LIKE '20260215-validation%'
GROUP BY experiment_id;

                experiment_id           | total | attacks | normal
-----------------------------------------+-------+---------+--------
 20260215-validation-normal-01          |  101  |   101   |   0    ← WRONG! Should be 0 attacks
 20260215-validation-attack-neg-01      |   25  |    25   |   0    ✓ Correct
 20260215-validation-attack-pos-01      |   21  |    21   |   0    ✓ Correct
```

**Conclusion**: Model itself has a fundamental issue and needs retraining.

---

## Grafana Dashboard Status

### Current Dashboards

#### 1. GCN Attack Detection Dashboard (`gcn-attack-detection.json`)
**Status**: ✅ Functional - Shows all required information

**Available Panels**:
1. **Statistics** (top row):
   - Total Predictions
   - Attacks Detected
   - Attack Rate
   - Avg Confidence
   - Avg Inference Time
   - Active Model (shows v2.0.0)

2. **Timeline Visualizations**:
   - Attack Detection Timeline
   - Prediction Confidence Over Time
   - Inference Performance Over Time
   - Probability Distributions Over Time

3. **Distribution Analysis**:
   - Confidence Score Distribution (histogram)
   - Prediction Distribution (pie chart)
   - Attack Rate by Experiment (bar gauge)

4. **Detailed Views**:
   - Recent Predictions (table with all fields)
   - Model Performance Summary

**Features**:
- ✅ Experiment filter (multi-select dropdown)
- ✅ Model version filter
- ✅ Auto-refresh every 10s
- ✅ Annotations for attack detections
- ✅ Annotations for model version changes

**Access**: http://localhost:3000/d/gcn-attack-detection

#### 2. MLO Attack Scenarios Dashboard (`mlo-attack-scenarios.json`)
**Status**: ✅ Functional - Shows KPI metrics over time

**Available Panels**:
1. Average Backoff Slots (Attack Indicator)
2. Network Throughput (Mbps)
3. Packet Loss Ratio
4. Average Packet Delay
5. Average Jitter
6. MAC Layer Retransmissions
7. Channel Busy Ratio
8. Network Active Flows
9. Key Metrics Summary (table)

**Features**:
- ✅ Experiment filter
- ✅ Entity filter (network/station)
- ✅ Time range selector
- ✅ All KPIs from telemetry data

**Access**: http://localhost:3000/d/mlo-attack-scenarios

### Dashboard Capabilities

#### ✅ What's Currently Shown:
1. **Latest simulation data**: Recent Predictions table shows most recent segments
2. **Prediction details**: Confidence, probabilities, inference time all visible
3. **Model information**: Active Model panel shows version, Model Performance Summary shows stats
4. **KPI visualizations**: MLO Scenarios dashboard has all metrics over time
5. **Comparison**: Can filter by experiment to compare normal vs attack scenarios

#### ⚠️ Known Limitations:
1. **Model predictions are incorrect** (100% false positives on normal traffic)
2. **No unified view** combining predictions + KPIs (requires two dashboards)
3. **No model explainability** (which features drove the prediction)

### Recommended Dashboard Enhancements

#### High Priority:
1. **Create unified dashboard** combining:
   - GCN predictions (top half)
   - KPI metrics (bottom half)
   - Side-by-side comparison for selected experiments

2. **Add alert panel** for abnormal behavior:
   - Alert if attack_rate > 50% for >1 hour
   - Alert if all predictions have confidence >99%
   - Alert if no predictions in last 5 minutes

3. **Add feature importance panel**:
   - Show which features had highest values
   - Highlight features that differ from training baseline

#### Medium Priority:
4. **Add experiment metadata panel**:
   - Show scenario type (normal/positive/negative)
   - Show bias value
   - Show simulation duration

5. **Add model comparison panel**:
   - Compare v1.0.0 vs v2.0.0 predictions
   - Show when model version changed

6. **Add data quality panel**:
   - Show telemetry message rate
   - Show windowizer processing lag
   - Show detector processing lag

---

## Files Modified

### Code Fixes:
1. `/home/cobrakali/github/ndt-wifi7-mlo-security/security/detector/windowizer/delta_converter.py`
   - Added field name mapping after delta conversion

2. `/home/cobrakali/github/ndt-wifi7-mlo-security/twin/gnn/detector/feature_processor.py`
   - Updated base_feature_keys to use delta field names
   - Updated derived feature calculations

### Documentation:
3. `/home/cobrakali/github/ndt-wifi7-mlo-security/docs/GCN-MODEL-ANALYSIS.md`
   - Full investigation and analysis

4. `/home/cobrakali/github/ndt-wifi7-mlo-security/docs/PIPELINE-FIX-SUMMARY.md`
   - This file - comprehensive summary

---

## Testing Data Available

### Validation Experiments:
```bash
# In database - ready for visualization
20260215-validation-normal-01:      26,000 metrics, 101 segments
20260215-validation-attack-neg-01:  26,000 metrics,  25 segments
20260215-validation-attack-pos-01:  26,000 metrics,  21 segments

# Access Grafana dashboards:
http://localhost:3000/d/gcn-attack-detection     # GCN predictions
http://localhost:3000/d/mlo-attack-scenarios     # KPI metrics
```

### Quick Dashboard Demo:
```bash
# 1. Open GCN Attack Detection dashboard
# 2. Set time range to "Last 24 hours"
# 3. In experiment filter, select: 20260215-validation-normal-01
# 4. Observe:
#    - Total Predictions: 101
#    - Attack Rate: 100% (WRONG - should be 0%)
#    - Avg Confidence: >99.9%
#    - Recent Predictions table shows all segments predicted as attack

# 5. Open MLO Attack Scenarios dashboard
# 6. Filter to same experiment
# 7. Observe:
#    - Normal throughput patterns
#    - Low backoff slots (no attack signature)
#    - Low retransmission rate
#    - → Data shows normal behavior, but GCN predicts attack
```

---

## Next Steps

### Immediate (Critical):
1. **Retrain GCN model v2.0.0**
   - Use validation experiments as held-out test set
   - Verify labels are correct
   - Ensure model achieves >90% accuracy on validation set
   - Test before deployment

2. **Validate retrained model**
   - Run validation experiments through pipeline
   - Verify: normal → 0% attacks, attack scenarios → >90% attacks
   - Check confidence distributions

### Short-term:
3. **Create unified Grafana dashboard**
   - Combine predictions + KPIs in one view
   - Add alert panels
   - Add feature importance

4. **Implement model monitoring**
   - Track prediction distribution
   - Alert on anomalies
   - Log feature values for debugging

### Long-term:
5. **Add model explainability**
   - GNN attention weights
   - Feature importance scores
   - Prediction rationale

6. **Automate model validation**
   - CI/CD pipeline for model training
   - Automated testing on validation set
   - Prevent deployment of broken models

---

## Summary

✅ **FIXED**: Data pipeline (windowizer + detector feature extraction)
❌ **BROKEN**: GCN model v2.0.0 (requires retraining)
✅ **WORKING**: Grafana dashboards (showing data correctly)
📊 **AVAILABLE**: 3 validation experiments ready for testing

**The pipeline is now correctly formatted. Once the model is retrained with proper validation, the entire system will work correctly.**

---

**For questions or issues, see**: `docs/GCN-MODEL-ANALYSIS.md`
