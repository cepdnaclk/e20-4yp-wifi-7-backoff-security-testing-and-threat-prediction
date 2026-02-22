# Grafana Dashboards

This directory contains Grafana dashboard JSON configurations that are automatically provisioned when the containerlab topology is deployed.

---

## Available Dashboards

### 1. GCN Attack Detection (`gcn-attack-detection`)

**File**: `gcn-attack-detection.json`
**Purpose**: Real-time monitoring and analysis of GCN-based WiFi 7 attack detection
**Created**: WP8 Phase 5 (2026-02-10)

**Features:**
- 16 visualization panels
- Real-time attack detection timeline
- Confidence score analysis
- Model performance metrics
- Recent predictions table
- Auto-refresh every 10 seconds

**Access**: http://localhost:3000/d/gcn-attack-detection

**Documentation**: `docs/WP8-PHASE5-GRAFANA-DASHBOARD.md`

**Key Panels:**
- Executive summary (6 stat panels)
- Attack Detection Timeline (time series)
- Confidence Analysis (histogram + line chart)
- Prediction Distribution (pie chart)
- Recent Predictions (table)
- Performance Metrics (time series)

### 2. MLO Attack Scenarios (`mlo-attack-scenarios`)

**File**: `mlo-attack-scenarios.json`
**Purpose**: Compare WiFi 7 MLO backoff manipulation attacks across scenarios
**Created**: WP7.5 (2026-01-05)

**Features:**
- Scenario comparison (Normal, Positive, Negative)
- Backoff manipulation visualization
- Throughput analysis
- Packet loss comparison
- Multi-experiment support

**Access**: http://localhost:3000/d/mlo-attack-scenarios

### 3. Throughput Comparison (`wp6-throughput-compare`)

**File**: `wp6-throughput-compare.json`
**Purpose**: Basic throughput comparison across experiments
**Created**: WP6 (2025-12-23)

**Features:**
- Simple throughput visualization
- Multi-experiment comparison

**Access**: http://localhost:3000/d/wp6-throughput-compare

---

## Usage

### Accessing Dashboards

1. **Start Containerlab**:
   ```bash
   make up
   ```

2. **Access Grafana**:
   - URL: http://localhost:3000
   - Default credentials: `admin` / `admin`

3. **Browse Dashboards**:
   - Home → Dashboards → Browse
   - Or search by name

### Dashboard Auto-Provisioning

Dashboards in this directory are automatically loaded by Grafana on startup via:

```yaml
# clab/configs/grafana/provisioning/dashboards/dashboard.yml
apiVersion: 1
providers:
  - name: 'default'
    folder: ''
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
```

**Note**: Changes to JSON files require Grafana restart to take effect.

---

## Customization

### Modifying Existing Dashboards

**Option 1: Via Grafana UI (Recommended)**

1. Edit dashboard in Grafana web interface
2. Save changes
3. Export JSON: Dashboard Settings → JSON Model
4. Copy JSON and overwrite file in this directory
5. Commit changes to git

**Option 2: Direct JSON Edit**

1. Edit JSON file directly
2. Validate JSON syntax
3. Restart Grafana:
   ```bash
   make down && make up
   ```

### Creating New Dashboards

1. **Create in Grafana UI**:
   - Create new dashboard
   - Add panels and configure
   - Save with unique UID

2. **Export JSON**:
   - Dashboard Settings → JSON Model
   - Copy JSON

3. **Save to Repository**:
   ```bash
   # Save JSON file
   cat > clab/configs/grafana/dashboards/my-dashboard.json
   # Paste JSON, Ctrl+D to finish

   # Commit
   git add clab/configs/grafana/dashboards/my-dashboard.json
   git commit -m "Add my-dashboard Grafana dashboard"
   ```

4. **Restart Grafana**:
   ```bash
   make down && make up
   ```

### Dashboard JSON Structure

```json
{
  "uid": "unique-dashboard-id",
  "title": "Dashboard Title",
  "description": "Dashboard description",
  "tags": ["tag1", "tag2"],
  "timezone": "UTC",
  "schemaVersion": 39,
  "version": 1,
  "editable": true,
  "refresh": "10s",
  "templating": {
    "list": [/* variables */]
  },
  "panels": [/* visualization panels */],
  "annotations": {
    "list": [/* annotations */]
  }
}
```

---

## Best Practices

### 1. Dashboard Design

- **Keep it focused**: One dashboard per use case
- **Use template variables**: Enable filtering
- **Set sensible defaults**: Auto-select "All" for filters
- **Enable auto-refresh**: For real-time monitoring
- **Use annotations**: Mark important events
- **Document queries**: Add descriptions to panels

### 2. Performance

- **Limit time ranges**: Default to reasonable periods
- **Optimize queries**: Use indexes, avoid full scans
- **Limit table rows**: Cap at 100-500 rows
- **Use aggregations**: Don't fetch raw data unnecessarily
- **Cache queries**: Enable Grafana query caching

### 3. Version Control

- **Always export after changes**: Keep repo in sync
- **Descriptive commit messages**: Explain what changed
- **Test before committing**: Verify dashboard works
- **Document breaking changes**: Update related docs

### 4. Naming Conventions

- **UIDs**: Use kebab-case (e.g., `gcn-attack-detection`)
- **Titles**: Use descriptive names with context
- **Tags**: Include project (ndt), work package (wp8), topic (ml, security)
- **Panel IDs**: Use incremental IDs (1, 2, 3, ...)

---

## Troubleshooting

### Dashboard Not Appearing

**Check:**
1. File is valid JSON: `jq . dashboard.json`
2. File is in correct directory
3. Grafana restarted after adding file
4. No UID conflicts with existing dashboards

**Verify**:
```bash
# Check Grafana logs
docker logs clab-ndt-wifi7-mlo-security-grafana | grep dashboard
```

### Datasource Errors

**Check:**
1. Datasource configured: Configuration → Data Sources
2. Test connection: Click "Test" button
3. Verify credentials in datasource config
4. Check network connectivity from Grafana container

### Panels Show No Data

**Check:**
1. Database has data: Query tables directly
2. Time range covers data period
3. Template variables set correctly
4. SQL query syntax correct
5. Field names match expectations

**Debug**:
```bash
# Check panel query
# Edit panel → Query Inspector → Query tab
# Run query directly against database
```

---

## Datasources

### UDR PostgreSQL

**Name**: `udr_postgres`
**UID**: `udr_postgres`
**Type**: PostgreSQL
**Host**: `clab-ndt-wifi7-mlo-security-udr-db:5432`
**Database**: `udr`

**Tables**:
- `metrics` - Telemetry data from ns-3
- `gcn_predictions` - GCN attack detection results
- `model_registry` - GCN model versions

**Configuration**: `clab/configs/grafana/provisioning/datasources/udr-postgres.yml`

---

## Dashboard Maintenance

### Regular Updates

**Weekly:**
- Review dashboard performance
- Check for slow queries
- Update time range bookmarks
- Test template variables

**Monthly:**
- Archive old dashboards (if no longer used)
- Optimize queries
- Update thresholds based on new baselines
- Document changes in git history

**After Schema Changes:**
- Update affected panel queries
- Test all panels
- Update documentation
- Increment dashboard version

---

## Related Documentation

- `docs/WP8-PHASE5-GRAFANA-DASHBOARD.md` - Complete GCN dashboard docs
- `docs/WP6-GRAFANA-DASHBOARDS.md` - WP6 dashboard documentation
- `docs/CURRENT-STATE.md` - Project status
- Grafana Official Docs: https://grafana.com/docs/

---

## Quick Reference

### Commands

```bash
# View Grafana logs
docker logs clab-ndt-wifi7-mlo-security-grafana

# Restart Grafana
docker restart clab-ndt-wifi7-mlo-security-grafana

# Access Grafana shell
docker exec -it clab-ndt-wifi7-mlo-security-grafana /bin/bash

# List provisioned dashboards
ls -la /etc/grafana/provisioning/dashboards/
```

### URLs

- **Grafana**: http://localhost:3000
- **GCN Dashboard**: http://localhost:3000/d/gcn-attack-detection
- **MLO Dashboard**: http://localhost:3000/d/mlo-attack-scenarios
- **API Health**: http://localhost:3000/api/health

### Credentials

- **User**: `admin`
- **Password**: `admin` (change on first login)

---

**Last Updated**: 2026-02-10
**Dashboards**: 3 (GCN Attack Detection, MLO Scenarios, Throughput Compare)
**Grafana Version**: 10.x+
