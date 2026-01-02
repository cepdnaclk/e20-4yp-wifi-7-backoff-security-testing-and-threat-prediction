# WP3: ns-3 Container and Baseline Wi-Fi Simulation

## Status: ✅ COMPLETED

## Overview
WP3 established ns-3 simulation capability with Wi-Fi 7 support, producing telemetry artifacts in a standardized format.

---

## What Was Implemented

### 1. ns-3 Docker Container
**File:** `docker/ns3/Dockerfile`

- Base: `ubuntu:22.04`
- Clones `ns-3-dev` repository
- Checks out `ns-3.46.1` (required for Wi-Fi 7 features)
- Builds in optimized mode
- Non-root user (`ns3`) for proper permissions

### 2. Version Verification
```bash
# Inside container
cat /opt/ns-3-dev/VERSION
# Output: 3.46.1
```

**Note:** `./ns3 --version` does not work - use VERSION file instead.

### 3. Baseline Simulation Scripts

**Files:**
- `sim/ns3/scenario/run_baseline.sh` - Basic test run
- `sim/ns3/scenario/run_wifi_example_and_export.sh` - Wi-Fi throughput test

### 4. Artifact Structure
```
sim/ns3/artifacts/<EXP_ID>/
├── meta.txt              # Run metadata
├── ns3_stdout.log        # Simulation stdout
├── ns3_stderr.log        # Simulation stderr
├── example_used.txt      # Which example ran
└── telemetry.jsonl       # Telemetry output
```

### 5. Telemetry Output Format (JSONL)
```json
{"experiment_id":"20251222-2340-wifi-example-42","ts":"2025-12-22T23:40:00.000Z","source":"ns3","schema_version":"v0.1","entity_id":"sim","metric":"throughput_mbps","value":117.5,"unit":"Mbps"}
```

---

## Acceptance Criteria (All Met)

| Criteria | Status |
|----------|--------|
| ns-3 container builds successfully | ✅ |
| Version 3.46.1 confirmed | ✅ |
| Wi-Fi module compiles | ✅ |
| Baseline run produces artifacts | ✅ |
| Telemetry JSONL created | ✅ |
| Same seed = reproducible results | ✅ |

---

## Key Commands

```bash
# Build ns-3 image
make ns3-build

# Run baseline (simple test)
make ns3-run EXP_ID=20251222-1835-baseline-42

# Run Wi-Fi example with telemetry
make ns3-run-example EXP_ID=20251222-2340-wifi-example-42

# Verify output
cat sim/ns3/artifacts/20251222-2340-wifi-example-42/telemetry.jsonl
```

---

## Problems Solved

### Problem 1: `./ns3 list | grep wifi` Returns Nothing
**Cause:** This doesn't mean Wi-Fi is missing - it means no runnable programs are registered that way.

**Solution:** Use `./ns3 show targets` or compile known scratch files directly.

### Problem 2: Copying ns-3 Examples Failed
**Error:** `wifi-example-apps.h` not found

**Cause:** Some examples depend on local headers not installed globally.

**Solution:** Write self-contained scratch programs instead of copying examples.

### Problem 3: API Differences in ns-3.46.1
**Error:** `YansWifiPhyHelper::Default()` not available

**Cause:** Helper APIs change between versions.

**Solution:** Adapt code to match ns-3.46.1 API.

### Problem 4: `--out` Option Confusion
**Error:** Unknown option `--out=/work/...`

**Cause:** ns-3 wrapper options and program options are separated by `--`.

**Solution:** 
- Wrapper options go before target
- Program options go after `--`

### Problem 5: Build Directory Permissions
**Error:** Cannot write to `/opt/ns-3-dev/build`

**Cause:** Container user cannot write to build directories.

**Solution:**
- Create non-root user (`ns3`) in Dockerfile
- Ensure directories are owned/writable:
  - `/opt/ns-3-dev/build`
  - `/opt/ns-3-dev/cmake-cache`
  - `/opt/ns-3-dev/scratch`

### Problem 6: Root-Owned Artifacts
**Cause:** Container ran as root, creating files host user can't delete.

**Solution:** Run with `--user "$(id -u):$(id -g)"` in Makefile.

---

## Implementation Details

### Dockerfile Key Sections
```dockerfile
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    git cmake g++ python3 python3-pip ...

# Clone and checkout specific version
RUN git clone https://gitlab.com/nsnam/ns-3-dev.git /opt/ns-3-dev
WORKDIR /opt/ns-3-dev
RUN git checkout ns-3.46.1

# Build
RUN ./ns3 configure --enable-examples --enable-tests
RUN ./ns3 build

# Create non-root user
RUN useradd -m ns3
RUN chown -R ns3:ns3 /opt/ns-3-dev/build /opt/ns-3-dev/cmake-cache /opt/ns-3-dev/scratch
USER ns3
```

### Run Script Structure
```bash
#!/bin/bash
EXP_ID=$1
ARTIFACT_DIR=/work/sim/ns3/artifacts/$EXP_ID

mkdir -p $ARTIFACT_DIR

# Run simulation
./ns3 run scratch/wifi-simple > $ARTIFACT_DIR/ns3_stdout.log 2> $ARTIFACT_DIR/ns3_stderr.log

# Extract throughput and create telemetry
THROUGHPUT=$(grep "Throughput" $ARTIFACT_DIR/ns3_stdout.log | awk '{print $2}')

echo '{"experiment_id":"'$EXP_ID'","ts":"'$(date -Iseconds)'","source":"ns3","schema_version":"v0.1","entity_id":"sim","metric":"throughput_mbps","value":'$THROUGHPUT',"unit":"Mbps"}' > $ARTIFACT_DIR/telemetry.jsonl
```

---

## Architecture at WP3

```
┌─────────────────────────────────────────┐
│         Host Machine (Kali)              │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │      ns-3 Container                 │ │
│  │      (ndt/ns3:local)                │ │
│  │                                     │ │
│  │  /work (bind mount) ←──────────────┼─┼── Repo root
│  │      │                              │ │
│  │      └── sim/ns3/artifacts/         │ │
│  │              └── <EXP_ID>/          │ │
│  │                  └── telemetry.jsonl│ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │      Containerlab Services          │ │
│  │      (separate, not connected yet)  │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

## What ns-3.46.1 Supports (Confirmed)

| Feature | Status |
|---------|--------|
| Build from ns-3-dev checkout | ✅ |
| Run scratch programs | ✅ |
| Wi-Fi module builds | ✅ |
| Measurable throughput output | ✅ |
| Telemetry export automation | ✅ |

---

## What Didn't Work (and Why)

| Approach | Why It Failed |
|----------|---------------|
| `./ns3 --version` | Not supported by wrapper |
| `./ns3 list \| grep wifi` | Not reliable discovery method |
| Copy single example .cc file | Missing dependency headers |
| `--out=/work/...` as wrapper option | Not a wrapper option |

---

## Lessons Learned

1. **Pin ns-3 version** in Dockerfile for reproducibility
2. **Self-contained scratch programs** are more reliable than copying examples
3. **Helper APIs differ** between versions - always test compile
4. **Non-root container user** prevents permission issues
5. **Telemetry contract** must be stable for downstream components

---

## Related ADRs
- ADR-0006: Keep ns-3 as separate container
- ADR-0007: Standardize experiment outputs as artifacts
- ADR-0008: Use stable JSONL telemetry contract
- ADR-0009: Use ns-3.46.1 for Wi-Fi 7
- ADR-0010: Prefer scratch programs over copying examples
- ADR-0011: Avoid `./ns3 list` for discovery
- ADR-0012: Fix permissions by design

---

## Next Steps (→ WP4)
- Build telemetry exporter (file → Kafka)
- Publish telemetry.jsonl to Redpanda
- Verify messages arrive in topic
