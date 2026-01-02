# ADR-0006: Keep ns-3 as Separate Container

## Status
Accepted

## Date
2025-12-22

## Context
Need to decide how to integrate ns-3 simulation with the lab environment. Options considered:
1. Embed ns-3 inside containerlab topology
2. Run ns-3 as separate Docker container
3. Run ns-3 directly on host

## Decision
Run ns-3 in a separate Docker image (`ndt/ns3:local`) with repo bind-mounted, rather than embedding ns-3 directly inside containerlab.

## Rationale
- **Debugging**: Much easier to debug ns-3 issues in isolation
- **Lifecycle**: ns-3 toolchain is heavy and has different lifecycle than services
- **Decoupling**: Avoids coupling ns-3 build/runtime problems to lab network problems
- **Iteration**: Can iterate on ns-3 without restarting services
- **Build time**: ns-3 takes 10+ minutes to build; services start in seconds

## Implementation

### Dockerfile
```dockerfile
# docker/ns3/Dockerfile
FROM ubuntu:22.04

# Install dependencies and clone ns-3
RUN git clone https://gitlab.com/nsnam/ns-3-dev.git /opt/ns-3-dev
WORKDIR /opt/ns-3-dev
RUN git checkout ns-3.46.1

# Build ns-3
RUN ./ns3 configure --enable-examples
RUN ./ns3 build

# Non-root user for permissions
RUN useradd -m ns3
RUN chown -R ns3:ns3 /opt/ns-3-dev/build /opt/ns-3-dev/scratch
USER ns3
```

### Usage
```bash
# Build
make ns3-build

# Run with repo mounted
docker run --rm \
  -v $(PWD):/work \
  --user "$(id -u):$(id -g)" \
  ndt/ns3:local \
  ./run_experiment.sh
```

## Consequences

### Positive
- Clear separation of concerns
- Can update ns-3 without affecting services
- Easier CI caching of ns-3 image
- Simpler debugging

### Negative
- Two execution planes: containerlab services and ns-3 runner
- Integration (ns-3 → Kafka) happens via file-based exporter
- Need separate build/run commands for ns-3
- Not on same network as services by default

### Architecture
```
┌─────────────────────────────────────┐
│         Host Machine                 │
│                                      │
│  ┌──────────────────────────────┐   │
│  │    ns-3 Container             │   │
│  │    (ndt/ns3:local)            │   │
│  │    /work ← repo mount         │   │
│  └──────────────────────────────┘   │
│              │                       │
│              │ writes telemetry.jsonl│
│              ▼                       │
│  ┌──────────────────────────────┐   │
│  │    Containerlab Services      │   │
│  │    (clab-mgmt network)        │   │
│  │    - Redpanda                 │   │
│  │    - TimescaleDB              │   │
│  │    - Grafana                  │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

## Related
- WP3: ns-3 Integration
- ADR-0009: Use ns-3.46.1 for Wi-Fi 7
- ADR-0010: Prefer scratch programs
