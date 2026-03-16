# WP2: Containerlab Skeleton with Services

## Status: ✅ COMPLETED

## Overview
WP2 established the Containerlab-based lab environment with core services (UDR DB, Grafana) and Makefile automation.

---

## What Was Implemented

### 1. Containerlab Topology
**File:** `clab/topo.yml`

Defines the lab environment with:
- Network topology and service containers
- Bind mounts for configuration
- Service networking

### 2. Service Containers

| Service | Container Name | Port | Purpose |
|---------|---------------|------|---------|
| UDR DB | `clab-ndt-wifi7-mlo-security-udr-db` | 5432 | Postgres/TimescaleDB |
| Grafana | `clab-ndt-wifi7-mlo-security-grafana` | 3000 | Visualization |
| Redpanda | `clab-ndt-wifi7-mlo-security-bus-redpanda` | 9092 | Kafka API (message bus) |

### 3. Configuration as Code
**Directory:** `clab/configs/`

```
clab/configs/
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── udr-postgres.yml
│   │   └── dashboards/
│   │       └── dashboards.yml
│   └── dashboards/
│       └── *.json
└── db/
    └── init.sql
```

### 4. Makefile Targets

```makefile
make up      # Deploy containerlab topology
make down    # Destroy topology and clean resources
make status  # Show node status and ports
make logs    # List containers and log guidance
```

---

## Acceptance Criteria (All Met)

| Criteria | Status |
|----------|--------|
| All containers start cleanly | ✅ |
| UDR DB reachable and has tables | ✅ |
| Grafana accessible at :3000 | ✅ |
| Redpanda accessible at :9092 | ✅ |
| `make up/down/status` work | ✅ |

---

## Database Verification

```bash
# Verify tables exist
docker exec -it clab-ndt-wifi7-mlo-security-udr-db \
  psql -U udr -d udr -c "\dt"

# Output confirmed:
#  public | metrics   | table | udr
#  public | snapshots | table | udr
```

---

## Problems Solved

### Problem 1: Bind Mount Path Not Found
**Error:**
```
Failed to verify bind path: .../clab/clab/configs/grafana/provisioning: no such file or directory
```

**Cause:**
- Containerlab validates bind-mount paths before starting
- Path referenced did not exist
- "Double clab/clab" path issue from incorrect relative paths

**Solution:**
- Ensure all bind-mount directories exist in filesystem
- Keep paths relative to topology file directory
- Add `.gitkeep` files for empty directories

### Problem 2: Grafana Multiple Default Datasources
**Error:**
```
Only one datasource per organization can be marked as default
```

**Cause:** Multiple datasource YAMLs had `isDefault: true`

**Solution:** Only one datasource should have `isDefault: true`

---

## Key Files

### clab/topo.yml (structure)
```yaml
name: ndt-wifi7-mlo-security

topology:
  nodes:
    udr-db:
      kind: linux
      image: timescale/timescaledb:latest-pg14
      # ... config

    grafana:
      kind: linux
      image: grafana/grafana:latest
      binds:
        - configs/grafana/provisioning:/etc/grafana/provisioning:ro
        - configs/grafana/dashboards:/var/lib/grafana/dashboards:ro

    bus-redpanda:
      kind: linux
      image: redpandadata/redpanda:latest
      # ... config
```

### Grafana Datasource (working template)
```yaml
apiVersion: 1
datasources:
  - name: UDR-Timescale
    type: postgres
    access: proxy
    url: udr-db:5432
    database: udr
    user: udr
    secureJsonData:
      password: udr_pass
    jsonData:
      sslmode: "disable"
      postgresVersion: 1600
      timescaledb: true
    isDefault: true
```

---

## Service Wiring

```
┌─────────────────────────────────────────────────────┐
│                 Containerlab Network                 │
│                   (clab-mgmt)                        │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  UDR DB  │  │ Grafana  │  │    Redpanda      │  │
│  │  :5432   │  │  :3000   │  │     :9092        │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │             │                  │            │
│       └─────────────┼──────────────────┘            │
│                     │                               │
└─────────────────────┼───────────────────────────────┘
                      │
              Docker Host Network
```

---

## Lessons Learned

1. **Containerlab validates paths early** - all bind mounts must exist before deploy
2. **Use relative paths** from topology file directory
3. **Config as code** enables reproducible labs
4. **One default datasource** per Grafana organization
5. **`.gitkeep` files** track empty directories in git

---

## Related ADRs
- ADR-0003: Use Containerlab for lab environment
- ADR-0004: Keep config as code
- ADR-0005: Use Postgres as UDR datastore

---

## Next Steps (→ WP3)
- Build ns-3 container with Wi-Fi 7 support
- Create baseline simulation scenario
- Produce telemetry artifacts
