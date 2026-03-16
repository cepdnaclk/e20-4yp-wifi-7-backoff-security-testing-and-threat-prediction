# ADR-0003: Use Containerlab for Lab Environment

## Status
Accepted

## Date
2025-12-22

## Context
Need an orchestration method for the services environment (UDR DB, Grafana, Kafka, etc.) that supports:
- Reproducible deployments
- Network isolation
- Easy service discovery
- CI/CD integration

## Decision
Use Containerlab as the main orchestrator for the lab environment.

## Rationale
- Reproducible lab topology defined in declarative YAML
- Services connected via controlled network (clab-mgmt)
- Easier to extend without ad-hoc docker-compose sprawl
- CI-ready lifecycle management
- Peer-to-peer veth links suitable for dense labs

## Implementation

### Topology File
```yaml
# clab/topo.yml
name: ndt-wifi7-mlo-security

topology:
  nodes:
    udr-db:
      kind: linux
      image: timescale/timescaledb:latest-pg14
    
    grafana:
      kind: linux
      image: grafana/grafana:latest
      binds:
        - configs/grafana/provisioning:/etc/grafana/provisioning:ro
    
    bus-redpanda:
      kind: linux
      image: redpandadata/redpanda:latest
```

### Makefile Targets
```makefile
make up      # Deploy topology
make down    # Destroy topology
make status  # Check status
make logs    # View logs
```

## Consequences

### Positive
- Single command deployment
- Reproducible across team members
- Easy to add new services
- Network isolation by default

### Negative
- All bind-mount paths must exist before deploy
- Learning curve for containerlab
- Path mistakes break deploy early (containerlab validates mounts)

### Mitigations
- Add `.gitkeep` files for empty directories
- Use relative paths from topology file directory
- Document common errors and solutions

## Related
- WP2: Containerlab Skeleton
- ADR-0004: Keep Config as Code
