# NDT Wi-Fi 7 MLO Security — Custom Dashboard UI Project Summary

**Project:** Custom web dashboard for the NDT digital twin pipeline
**Port:** 8888
**URL:** http://localhost:8888
**Style:** Soft UI / Neumorphism + Claymorphism
**Stack:** React 18 + Vite + TailwindCSS (frontend) | FastAPI + asyncpg (backend) | Multi-stage Docker

---

## Progress

| Task | Status | Notes |
|------|--------|-------|
| T3: Directory structure + uiprojectsummary.md | ✅ Done | All dirs created |
| T4: FastAPI backend | ✅ Done | main.py, db, api, ws, registry, models |
| T5: Frontend scaffold (Vite + design system) | ✅ Done | Tailwind, CSS vars, types, AppContext |
| T6: Layout + common UI components | ✅ Done | TopBar, Sidebar, KpiCard, Badge, LiveIndicator, etc. |
| T7: Pipeline monitor + chart components | ✅ Done | PipelineFlowDiagram, ActivityFeed, 5 chart types |
| T8: Model components + hooks + all 6 sections | ✅ Done | 11 hooks, ConfusionMatrix, 6 sections |
| T9: Docker build + docker-compose | ✅ Done | Multi-stage Dockerfile, docker-compose.dashboard.yml |
| T10: Build image, run, verify | ✅ Done | `tsc` clean, Vite build OK, Docker image verified |

---

## Architecture

```
dashboard/app/
├── Dockerfile           ← Multi-stage: Node build → Python runtime
├── .dockerignore
├── backend/             ← FastAPI + asyncpg (Python 3.11)
│   ├── main.py          ← App factory, CORS, static files, routes (graceful DB startup)
│   ├── requirements.txt ← fastapi, uvicorn, asyncpg, pydantic, PyYAML
│   ├── api/             ← experiments.py, models.py, analysis.py, pipeline.py
│   ├── ws/              ← pipeline.py (WebSocket /ws/pipeline, 2s poll)
│   ├── db/              ← connection.py, queries.py
│   ├── registry/        ← reader.py (reads twin/registry/gcn)
│   └── models/          ← Pydantic response types
└── frontend/            ← React 18 + Vite + TailwindCSS
    └── src/
        ├── context/     ← AppContext.tsx (WebSocket + global state)
        ├── hooks/        ← useApi, useExperiments, useModels, useAnalysis
        ├── components/  ← layout/, common/, pipeline/, charts/, model/
        ├── sections/    ← 6 dashboard sections
        └── types/       ← TypeScript interfaces (experiments, models, analysis, pipeline)
```

## 6 Dashboard Sections

1. **Pipeline Monitor** — Live stage flow: NS-3 → Exporter → Kafka → Windowizer → GCN → DB
2. **Experiment View** — KPI cards, metric time-series, segment predictions table, experiment selector
3. **Model Intelligence** — F1/accuracy/precision/recall/AUC, confusion matrix, inference latency, version list
4. **Run History** — All runs with pass/fail, attack rate bars, sortable table
5. **Attack Analysis** — Detection rates, TP/TN/FP/FN cards, confidence histogram, donut by type
6. **Network Health** — All 13 telemetry metrics with trend indicators + drill-down time-series

## Commands

```bash
make dashboard-build   # Build Docker image
make dashboard-up      # Start on http://localhost:8888
make dashboard-down    # Stop
make dashboard-logs    # Follow logs
make dashboard-status  # Status + recent logs
make dashboard-dev     # Dev mode (backend uvicorn --reload)
```

## Design System

- **Background:** `#e8edf2` (Soft UI surface)
- **Cards:** Raised neumorphic shadows (light top-left, dark bottom-right)
- **Accent:** `#6392fa` (brand blue), `#4caf87` (normal green), `#e85d6a` (attack red)
- **Font:** Inter
- **Border radius:** 20px cards, 14px buttons, 999px pills

---

*Last updated: 2026-02-28 — All tasks complete*
