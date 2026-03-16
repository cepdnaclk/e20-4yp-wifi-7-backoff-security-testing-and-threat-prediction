# ADR-0008: Use Stable JSONL Telemetry Contract

## Status
Accepted

## Date
2025-12-22

## Context
Need a stable interface format between ns-3 simulation outputs and downstream pipeline stages (exporter, harmonizer, database).

Requirements:
- Easy to produce from C++ simulation
- Easy to consume in Python services
- Streamable (line by line)
- Self-describing
- Versionable

## Decision
Use JSON Lines (`telemetry.jsonl`) as the interface between ns-3 and later pipeline stages.

## Rationale
- **Streaming**: One JSON object per line, easy to append and read incrementally
- **Kafka-friendly**: Each line is a natural Kafka message
- **Debuggable**: Human-readable, easy to inspect with `cat`, `jq`
- **Parseable**: Simple parsing in any language
- **Versioned**: Schema version field allows evolution

## Schema (v0.1)

```json
{
  "experiment_id": "20251223-1200-wifi-example-42",
  "ts": "2025-12-23T12:00:00.000Z",
  "source": "ns3",
  "schema_version": "v0.1",
  "entity_id": "sta1",
  "metric": "throughput_mbps",
  "value": 117.5,
  "unit": "Mbps"
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `experiment_id` | string | Yes | Unique identifier for the experiment run |
| `ts` | string | Yes | ISO 8601 timestamp |
| `source` | string | Yes | Data source (e.g., "ns3") |
| `schema_version` | string | Yes | Schema version for evolution |
| `entity_id` | string | Yes | Entity being measured (sta, ap, link) |
| `metric` | string | Yes | Metric name |
| `value` | float | Yes | Metric value |
| `unit` | string | Yes | Unit of measurement |

## Implementation

### Producer (ns-3 run script)
```bash
echo '{"experiment_id":"'$EXP_ID'","ts":"'$(date -Iseconds)'","source":"ns3","schema_version":"v0.1","entity_id":"sim","metric":"throughput_mbps","value":'$THROUGHPUT',"unit":"Mbps"}' >> telemetry.jsonl
```

### Consumer (Python)
```python
from pydantic import BaseModel

class TelemetryRecord(BaseModel):
    experiment_id: str
    ts: str
    source: str
    schema_version: str
    entity_id: str
    metric: str
    value: float
    unit: str

# Parse
for line in open('telemetry.jsonl'):
    record = TelemetryRecord.parse_raw(line)
```

## Consequences

### Positive
- Clear contract between components
- Easy testing and debugging
- Supports schema evolution via version field
- No binary format complexity

### Negative
- Slightly larger than binary formats
- Need to maintain schema documentation
- All scenarios must conform to contract

### Schema Evolution
When schema changes:
1. Bump `schema_version` to `v0.2`
2. Update producers to emit new schema
3. Update consumers to handle both versions
4. Document changes in ADR update

## Related
- WP3: ns-3 Integration
- WP4: Telemetry Exporter
- ADR-WP4-01: Telemetry contract is JSONL
