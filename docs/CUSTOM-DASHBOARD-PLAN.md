# Custom Web Dashboard — NDT Wi-Fi 7 MLO Security

**Date:** 2026-02-28
**Author:** Planner Agent
**Status:** Ready for Implementation
**Target Path:** `dashboard/app/`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [UI Design System](#3-ui-design-system)
4. [Page Layout and ASCII Wireframes](#4-page-layout-and-ascii-wireframes)
5. [Sections Specification](#5-sections-specification)
6. [Real-Time Pipeline Monitor](#6-real-time-pipeline-monitor)
7. [Backend API Design](#7-backend-api-design)
8. [WebSocket Event Specification](#8-websocket-event-specification)
9. [Frontend Component Tree](#9-frontend-component-tree)
10. [Data Sources and Key SQL Queries](#10-data-sources-and-key-sql-queries)
11. [Docker Setup](#11-docker-setup)
12. [File and Directory Structure](#12-file-and-directory-structure)
13. [Implementation Phases](#13-implementation-phases)

---

## 1. Executive Summary

### What This Is

A custom single-page web application (SPA) that replaces or supplements the Grafana dashboards for the NDT Wi-Fi 7 MLO Security project. This dashboard provides a purpose-built interface tailored to the specific concerns of the digital twin system: real-time pipeline health, per-experiment attack detection results, GCN model intelligence, and cross-run historical comparison.

### Goals

1. Provide a live pipeline stage visualization showing data flow from NS-3 through to GCN predictions with real-time counters.
2. Offer an individual experiment deep-dive view: KPI time evolution, per-segment predictions, confidence scores.
3. Surface GCN model intelligence: active model version, F1/accuracy/precision/recall/AUC, confusion matrix, inference latency distribution.
4. Enable run history and cross-run comparison to quickly identify which runs were attacked versus normal.
5. Deliver an attack detection analysis view: detection rates, confidence histograms, false positive rates.
6. Show all 13 telemetry metrics with trend indicators for network health awareness.

### Key Features

- **Design Style:** Soft UI / Neumorphism with Claymorphic card elements — 3D-looking cards, extruded shadows, rounded corners, muted pastel palette
- **Single page** with collapsible left sidebar to navigate between 6 sections
- **Real-time** via WebSocket for pipeline stage counters and live predictions
- **Zero click to start** — loads the most recent run by default
- **Offline-first for history** — run history loads from DB, no real-time dependency

---

## 2. Architecture Overview

### 2.1 Tech Stack Decisions

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend framework** | React 18 (Vite) | Component model maps well to the card/panel layout; fast HMR during dev |
| **Styling** | Tailwind CSS + custom CSS variables | Utility classes for layout; CSS variables for neumorphic shadow system |
| **Charts** | Recharts | Pure React, composable, no external canvas library needed |
| **WebSocket client** | Native browser WebSocket API | No extra library needed for simple event subscription |
| **Backend framework** | FastAPI (Python) | Already in-project language; async support; built-in WebSocket; OpenAPI docs free |
| **DB client** | asyncpg | Async Postgres driver; works natively with FastAPI's asyncio event loop |
| **Container** | Docker multi-stage (Node build + Python runtime) | Keeps image small; separates build from runtime |

### 2.2 Container Design

```
┌─────────────────────────────────────────────────────────┐
│  dashboard container  (port 8888)                        │
│                                                          │
│  ┌─────────────────┐    ┌─────────────────────────────┐  │
│  │  FastAPI backend │    │  React SPA (static files)   │  │
│  │  /api/*         │    │  served by FastAPI's        │  │
│  │  /ws/*          │    │  StaticFiles mount at /      │  │
│  └────────┬────────┘    └─────────────────────────────┘  │
│           │                                               │
└───────────┼───────────────────────────────────────────────┘
            │  asyncpg  (clab-mgmt network)
            ▼
  clab-ndt-wifi7-mlo-security-udr-db:5432
  database: udr  user: udr  pass: udr_pass
```

The dashboard container joins the existing `clab-mgmt` Docker network (the same network used by harmonizer, windowizer, and gcn-detector). It talks directly to TimescaleDB at `clab-ndt-wifi7-mlo-security-udr-db:5432` using asyncpg. It does NOT talk to Kafka directly — all data is read from the DB.

For the real-time pipeline monitor, the backend polls Docker socket (or relies on DB ingest timestamps) to compute message rates. Polling DB is preferred to avoid Docker socket privileges — a dedicated DB-polling approach with 2s intervals is sufficient.

### 2.3 Data Flow (Dashboard Perspective)

```
TimescaleDB (udr DB)
  metrics table          ──► REST API ──► React panels
  gcn_predictions table  ──► REST API ──► React panels
  model_registry table   ──► REST API ──► Model Intelligence panel

  Pipeline activity      ──► WebSocket ──► Pipeline Monitor
  (computed from DB ingest_time recency)
```

WebSocket sends events when:
- New rows appear in `gcn_predictions` (polled every 2s)
- Pipeline metric ingestion rate changes significantly (polled every 5s)

### 2.4 Network and Port Mapping

| Service | Internal address | Host port |
|---------|-----------------|-----------|
| Dashboard (new) | dashboard:8888 | 8888 |
| TimescaleDB | udr-db:5432 | 5432 |
| Grafana (existing) | grafana:3000 | 3000 |
| Redpanda | bus-redpanda:9092 | 9092 |

---

## 3. UI Design System

### 3.1 Neumorphism / Claymorphism Specification

The visual identity is Soft UI with Claymorphic accents. Every card element uses a double-shadow technique to simulate physical extrusion from the background surface.

#### Base Surface

```
background-color: #e8edf2
```

This mid-grey-blue is the page background. All cards appear pressed into or raised from this surface.

#### Shadow System (CSS Variables)

```css
/* Raised card — appears to float above the surface */
--shadow-raised:
  8px  8px 16px  rgba(166, 180, 200, 0.7),
 -8px -8px 16px  rgba(255, 255, 255, 0.8);

/* Pressed / inset — appears recessed into the surface */
--shadow-inset:
  inset 4px  4px  8px  rgba(166, 180, 200, 0.7),
  inset -4px -4px 8px  rgba(255, 255, 255, 0.8);

/* Floating card (Claymorphic) — stronger, colored shadow */
--shadow-clay:
  12px 12px 24px  rgba(150, 170, 200, 0.6),
  -6px -6px 16px  rgba(255, 255, 255, 0.9),
   0px  4px 12px  rgba(100, 130, 180, 0.2);

/* Active / highlighted state */
--shadow-active:
  6px  6px 12px  rgba(166, 180, 200, 0.5),
 -6px -6px 12px  rgba(255, 255, 255, 0.7),
  inset 0   0     2px rgba(99, 146, 250, 0.3);
```

#### Border Radius

```css
--radius-card:   20px;   /* Main content cards */
--radius-chip:   12px;   /* Small badge/chip elements */
--radius-btn:    14px;   /* Buttons */
--radius-pill:   999px;  /* Status indicators, tags */
--radius-inner:  14px;   /* Inner panels within a card */
```

### 3.2 Color Palette

#### Neutral Surface Colors

```css
--color-bg:          #e8edf2;   /* Page background */
--color-surface:     #edf0f5;   /* Card face */
--color-surface-alt: #dde3eb;   /* Inset areas */
--color-border:      rgba(255,255,255,0.6);
--color-text-primary:   #2d3a4a;
--color-text-secondary: #6b7a8d;
--color-text-muted:     #9aa5b4;
```

#### Semantic Colors (Normal / Attack / Neutral)

```css
/* Normal traffic — calm teal-green */
--color-normal:         #4caf87;
--color-normal-light:   #e3f6ef;
--color-normal-shadow:  rgba(76, 175, 135, 0.3);

/* Attack traffic — warm red-orange */
--color-attack:         #e85d6a;
--color-attack-light:   #fdedf0;
--color-attack-shadow:  rgba(232, 93, 106, 0.3);

/* Unknown / pending — amber */
--color-pending:        #f4a535;
--color-pending-light:  #fef5e4;
--color-pending-shadow: rgba(244, 165, 53, 0.3);

/* Accent (brand blue) */
--color-accent:         #6392fa;
--color-accent-light:   #edf1ff;
--color-accent-shadow:  rgba(99, 146, 250, 0.3);
```

#### Chart Color Palette

```css
--chart-normal:   #4caf87;   /* Line/bar for normal metric */
--chart-attack:   #e85d6a;   /* Line/bar for attack metric */
--chart-neutral:  #6392fa;   /* Neutral metrics (throughput etc.) */
--chart-accent2:  #a068f5;   /* Secondary metric */
--chart-accent3:  #f4a535;   /* Tertiary metric */
--chart-grid:     rgba(110, 130, 160, 0.15);
```

### 3.3 Typography

```css
--font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-size-xs:   11px;
--font-size-sm:   13px;
--font-size-base: 15px;
--font-size-md:   17px;
--font-size-lg:   21px;
--font-size-xl:   28px;
--font-size-kpi:  38px;

--font-weight-normal:   400;
--font-weight-medium:   500;
--font-weight-semibold: 600;
--font-weight-bold:     700;
```

### 3.4 Animation Specification

```css
/* Pipeline stage pulse animation (active data flow) */
@keyframes pipeline-pulse {
  0%   { box-shadow: 0 0 0 0 var(--color-normal-shadow); }
  50%  { box-shadow: 0 0 0 8px transparent; }
  100% { box-shadow: 0 0 0 0 transparent; }
}

/* Ripple for live data indicator */
@keyframes live-ripple {
  0%   { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(2.5); opacity: 0; }
}

/* Data flow arrow animation (horizontal travel) */
@keyframes flow-travel {
  0%   { transform: translateX(-100%); opacity: 0; }
  20%  { opacity: 1; }
  80%  { opacity: 1; }
  100% { transform: translateX(100%); opacity: 0; }
}

/* Card hover lift */
.card:hover {
  transform: translateY(-2px);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

/* Transition duration */
--transition-fast:   150ms ease;
--transition-normal: 250ms ease;
--transition-slow:   400ms ease;
```

---

## 4. Page Layout and ASCII Wireframes

### 4.1 Overall Page Layout

```
┌────────────────────────────────────────────────────────────────────────────┐
│  TOPBAR: Logo + "NDT Wi-Fi 7 MLO Security" | Live indicator | Time         │
├──────────────┬─────────────────────────────────────────────────────────────┤
│              │                                                              │
│  SIDEBAR     │   MAIN CONTENT AREA                                         │
│  (240px)     │   (flex-grow, scrollable)                                   │
│              │                                                              │
│  [collapse]  │                                                              │
│              │                                                              │
│  > Pipeline  │                                                              │
│    Monitor   │                                                              │
│              │                                                              │
│  > Experiment│                                                              │
│    View      │                                                              │
│              │                                                              │
│  > Model     │                                                              │
│    Intel     │                                                              │
│              │                                                              │
│  > Run       │                                                              │
│    History   │                                                              │
│              │                                                              │
│  > Attack    │                                                              │
│    Analysis  │                                                              │
│              │                                                              │
│  > Network   │                                                              │
│    Health    │                                                              │
│              │                                                              │
└──────────────┴─────────────────────────────────────────────────────────────┘
```

**Sidebar collapsed state (48px wide):**
```
┌──┬──────────────────────...
│  │
│ >│
│  │
│ ⊙│
│  │
│ ◈│
│  │
│ ≡│
│  │
│ ◎│
│  │
│ ∿│
```

### 4.2 Top Bar Wireframe

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ⊙ NDT Wi-Fi 7 MLO Security                    ● LIVE   2026-02-28 14:32  │
└────────────────────────────────────────────────────────────────────────────┘
  12px left pad                                  green dot pulses when WS active
```

### 4.3 Section 1: Pipeline Monitor Wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│  PIPELINE MONITOR                                          [Last refresh] │
│                                                                           │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐      │
│  │  NS-3  │───►│Exporter│───►│ Kafka  │───►│Windowiz│───►│  GCN   │      │
│  │        │    │        │    │        │    │  -er   │    │Detector│      │
│  │  ●●●   │    │ ●●●●   │    │ ●●●●   │    │  ●●●   │    │  ●●●   │      │
│  │26.0k   │    │26.0k   │    │26.0k   │    │ 7 seg  │    │ 7 pred │      │
│  │ msgs   │    │sent    │    │stored  │    │        │    │        │      │
│  └────────┘    └────────┘    └────────┘    └────────┘    └────────┘      │
│      ↑ colored border: green=active, grey=idle, red=error                │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  Recent Activity Feed (last 10 events, auto-scroll)              │    │
│  │  14:32:01  [GCN]       Segment 7/7 → ATTACK  conf=0.998         │    │
│  │  14:31:58  [GCN]       Segment 6/7 → ATTACK  conf=0.997         │    │
│  │  14:31:52  [Windowizer] Segment flush: exp_id=20260228-1129-...  │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.4 Section 2: Experiment View Wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│  EXPERIMENT VIEW                                                          │
│                                                                           │
│  [Experiment ID ▼]  20260228-1129-seq2-attack-neg          [Refresh]     │
│                                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  SEGMENTS   │  │ ATTACK RATE │  │  AVG CONF.  │  │  INFERENCE  │    │
│  │     7       │  │   100.0%    │  │   99.8%     │  │   2.3 ms    │    │
│  │  total      │  │ of segments │  │ confidence  │  │  avg/seg    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                                           │
│  ┌──────────────────────────────────────┐  ┌──────────────────────────┐  │
│  │  KPI Time Evolution                  │  │  Segment Predictions     │  │
│  │  [metric selector: throughput ▼]     │  │                          │  │
│  │  ▲                                   │  │  seg  pred  conf  infer  │  │
│  │  │  ___                              │  │  1    ATK   0.998  2.1ms │  │
│  │  │ /   \___    ____                  │  │  2    ATK   0.997  2.3ms │  │
│  │  │          \_/    \__               │  │  3    ATK   0.999  2.2ms │  │
│  │  └──────────────────────► time       │  │  ...                     │  │
│  └──────────────────────────────────────┘  └──────────────────────────┘  │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  Confidence Distribution (histogram, 10 bins 0→1)                │    │
│  │  ██████████████████████ 7 segments at 0.99-1.00 (attack)         │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.5 Section 3: Model Intelligence Wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│  MODEL INTELLIGENCE                                                       │
│                                                                           │
│  ┌─────────────────────────────────────────┐  ┌────────────────────────┐ │
│  │  Active Model: v2.0.0                   │  │  Confusion Matrix      │ │
│  │  Created: 2026-02-15                    │  │                        │ │
│  │  Dataset: data_v2_production (284 scen) │  │      Pred N  Pred A    │ │
│  │  Architecture: 2-layer GCN, 64 hidden   │  │  Act N  107     1      │ │
│  │  Segment length: 256 windows            │  │  Act A    0    87      │ │
│  └─────────────────────────────────────────┘  └────────────────────────┘ │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │  Performance Metrics (from test_results.json)                     │   │
│  │                                                                   │   │
│  │  F1      Accuracy  Precision  Recall    AUC                       │   │
│  │  ████    ████      ████       ████      ████                      │   │
│  │  99.4%   99.5%     98.9%      100%      100%                      │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────┐  │
│  │  Model Version History           │  │  Inference Latency (runtime) │  │
│  │  v2.0.0  ● active                │  │  Min: 1.8ms                  │  │
│  │  v1.0.0  ○ retired               │  │  P50: 2.3ms                  │  │
│  │  v2.1.0  ○ available             │  │  P95: 3.1ms                  │  │
│  └──────────────────────────────────┘  │  Max: 4.2ms                  │  │
│                                        └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.6 Section 4: Run History Wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│  RUN HISTORY                              [Filter: all ▼]  [Refresh]     │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Experiment ID                   Type      Segs  ATK%  Confidence   │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  20260228-1129-seq4-attack-pos   ATTACK    7     100%  99.9%  ●FAIL │ │
│  │  20260228-1129-seq3-normal       NORMAL    7     0%    1.2%   ●PASS │ │
│  │  20260228-1129-seq2-attack-neg   ATTACK    7     100%  99.8%  ●FAIL │ │
│  │  20260228-1129-seq1-normal       NORMAL    7     0%    1.3%   ●PASS │ │
│  │  20260215-validation-attack-pos  ATTACK    7     100%  99.7%         │ │
│  │  20260215-validation-normal-01   NORMAL    7     0%    0.9%          │ │
│  │  ...                                                                 │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────┐  │
│  │  Run Group Summary               │  │  Attack Rate Over Runs       │  │
│  │  Run prefix: 20260228-1129       │  │  ▲                            │  │
│  │  Experiments: 4                  │  │  │  ████  ▒▒▒▒  ████  ▒▒▒▒  │  │
│  │  Attack: 2  Normal: 2            │  │  └──────────────────────►     │  │
│  │  Pass: 4    Fail: 0              │  │    n1    an    n2    ap       │  │
│  └──────────────────────────────────┘  └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.7 Section 5: Attack Detection Analysis Wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ATTACK DETECTION ANALYSIS                                                │
│                                                                           │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                │
│  │  Total Segs   │  │  Attacks Det. │  │  False Pos.   │                │
│  │    56 total   │  │    28 attack  │  │    0 FP       │                │
│  │    (all runs) │  │   50.0% rate  │  │   0.0% FPR    │                │
│  └───────────────┘  └───────────────┘  └───────────────┘                │
│                                                                           │
│  ┌──────────────────────────────────────┐  ┌──────────────────────────┐  │
│  │  Confidence Distribution             │  │  Attack Types Breakdown   │  │
│  │  (all attack predictions)            │  │  Negative bias: 14 segs  │  │
│  │  ▲                                   │  │  Positive bias: 14 segs  │  │
│  │  │  ██████████████████               │  │                          │  │
│  │  │                    ████           │  │  Donut chart             │  │
│  │  └──────────────────────►            │  │                          │  │
│  │   0.0  0.2  0.4  0.6  0.8  1.0      │  └──────────────────────────┘  │
│  └──────────────────────────────────────┘                                 │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  Detection Latency: avg seconds from start to first alert        │    │
│  │  attack-neg: ~25.6s  (first segment detected, 0-25.6s elapsed)   │    │
│  │  attack-pos: ~25.6s  (deterministic: 7 segments × 25.6s/seg)     │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.8 Section 6: Network Health Wireframe

```
┌──────────────────────────────────────────────────────────────────────────┐
│  NETWORK HEALTH METRICS                  Experiment: [selector ▼]        │
│                                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │  Metric                      Current  Trend  Min     Max    Avg   │   │
│  │  net_throughput_mbps          52.3     ↑      18.0   84.0  48.2  │   │
│  │  net_avg_delay_ms              4.2     →       2.1    8.9   4.5  │   │
│  │  net_avg_jitter_ms             0.8     ↓       0.4    2.1   0.9  │   │
│  │  net_packet_loss_ratio         0.01    →       0.0    0.04  0.01 │   │
│  │  net_active_flows              8.0     →       8.0    8.0   8.0  │   │
│  │  mac_total_tx               3.2M      ↑                          │   │
│  │  mac_total_rx               3.1M      ↑                          │   │
│  │  mac_total_ack              3.0M      ↑                          │   │
│  │  mac_total_retrans          41.2k     →                          │   │
│  │  mac_drop_count               2.1k    →                          │   │
│  │  phy_drop_count               1.8k    →                          │   │
│  │  avg_backoff_slots            34.2    ↑  ← KEY attack indicator  │   │
│  │  channel_busy_ratio            0.42   →                          │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  Backoff Slots Time Series  (attack signature visible here)      │    │
│  │  ▲                                                               │    │
│  │  │              ████████████████████                             │    │
│  │  │  ██████████                      ██████████                  │    │
│  │  └──────────────────────────────────────────────────► time      │    │
│    normal range (CW=16-1024)     attack spike (CW+3500 bias)       │    │
│  └──────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Sections Specification

### 5.1 Section 1: Pipeline Monitor

**Purpose:** Show live status of all 6 pipeline stages with message/segment counts.

**Panels:**

| Panel | Data Source | Update Method |
|-------|-------------|---------------|
| Stage flow diagram (6 nodes) | WebSocket `pipeline_status` events | Real-time WebSocket |
| Activity feed (last 10 events) | WebSocket `pipeline_event` events | Real-time WebSocket |
| Last experiment ID processed | WebSocket `pipeline_status` | Real-time WebSocket |

**Stage Nodes:**
1. **NS-3** — shows whether a telemetry.jsonl file was processed recently. Active if metrics were ingested within last 60s.
2. **Exporter** — shows count of Kafka messages tracked via `metrics` ingest_time recency.
3. **Kafka (Redpanda)** — shows count of unique metrics rows in DB from last run. Treated as proxy for Kafka delivery count.
4. **Windowizer** — shows count of segments produced (via `gcn_predictions` segment_id count for most recent experiment).
5. **GCN Detector** — shows count of predictions in `gcn_predictions` for most recent experiment.
6. **DB** — shows total rows in `gcn_predictions` (cumulative).

**Stage State Colors:**
- `active` (data flowing): green border, pulsing animation
- `idle` (no data for >60s): grey border, no animation
- `error` (backend reports issue): red border, shake animation

**Activity Feed:** Each WebSocket `pipeline_event` message contains a `{ts, stage, message, level}` payload. Frontend keeps a circular buffer of 10 entries and auto-scrolls.

### 5.2 Section 2: Experiment View

**Purpose:** Deep-dive into a single experiment's prediction results and metric time series.

**Panels:**

| Panel | Type | Data |
|-------|------|------|
| KPI row: Segments / Attack Rate / Avg Confidence / Avg Inference | Stat cards | REST GET /api/experiments/{id}/summary |
| KPI Time Evolution | Line chart (Recharts) | REST GET /api/experiments/{id}/metrics?metric=X |
| Segment Predictions Table | Sortable table | REST GET /api/experiments/{id}/predictions |
| Confidence Distribution Histogram | Bar chart | Derived from predictions response |

**Experiment Selector:** Dropdown showing all experiment IDs from DB, sorted descending by `ts_start`. On page load, the most recent experiment is selected.

**Metric Selector:** Dropdown with all 13 metric names:
- net_throughput_mbps, net_avg_delay_ms, net_avg_jitter_ms, net_packet_loss_ratio, net_active_flows
- mac_total_tx, mac_total_rx, mac_total_ack, mac_total_retrans, mac_drop_count
- phy_drop_count, avg_backoff_slots, channel_busy_ratio

**Segment Predictions Table Columns:**
- Segment # (1-indexed)
- Prediction label (NORMAL / ATTACK) with color chip
- Confidence % (to 2 decimal places)
- P(Normal) / P(Attack) from probabilities JSONB
- Window range (window_start_idx – window_end_idx)
- Time range (ts_start – ts_end)
- Inference time (ms, to 1 decimal)

### 5.3 Section 3: Model Intelligence

**Purpose:** Show the active GCN model's characteristics and performance metrics.

**Panels:**

| Panel | Data Source |
|-------|-------------|
| Active model info card | REST GET /api/models/active |
| Confusion matrix | REST GET /api/models/{version}/test_results |
| Performance bar chart (F1/Acc/Prec/Recall/AUC) | REST GET /api/models/{version}/test_results |
| Model version history list | REST GET /api/models |
| Runtime inference latency stats | REST GET /api/models/active/inference_stats |

**Active Model Info Card Fields:**
- Version (e.g., v2.0.0)
- Created date
- Dataset name + scenario count
- Architecture: N-layer GCN, H hidden channels, D dropout
- Segment length
- Pooling type

**Confusion Matrix Rendering:**
A 2x2 grid displayed as colored squares:
- TN (top-left): green background, count + label "True Normal"
- FP (top-right): red background, count + label "False Attack"
- FN (bottom-left): orange background, count + label "Missed Attack"
- TP (bottom-right): green background, count + label "True Attack"

Values read from `test_results.json` `confusion_matrix` field: `[[TN, FP], [FN, TP]]`.

**Performance Bar Chart:**
Horizontal bar chart for F1, Accuracy, Precision, Recall, AUC — each bar spans 0–100%, with the value printed at the end.

**Runtime Inference Latency Stats:**
Computed from `gcn_predictions.inference_time_ms` across all rows:
- Min, P50 (median), P95, Max

### 5.4 Section 4: Run History

**Purpose:** List all experiments grouped by run prefix (YYYYMMDD-HHMM), show pass/fail, allow comparison.

**Panels:**

| Panel | Data |
|-------|------|
| Experiment list table | REST GET /api/experiments |
| Run group summary card | Derived from experiment list |
| Attack rate bar chart per run | Derived from experiment list |

**Experiment List Table Columns:**
- Experiment ID (clickable → loads in Experiment View)
- Inferred type (NORMAL / ATTACK) — derived from experiment_id suffix containing "attack" or "normal"
- Segment count
- Attack % (attack segments / total segments * 100)
- Average confidence
- Pass/Fail badge — PASS if type=NORMAL and attack%=0, or type=ATTACK and attack%=100; FAIL otherwise

**Run Group Summary:**
The API groups experiments by `YYYYMMDD-HHMM` prefix. The frontend shows:
- Total experiments in this group
- Normal count, Attack count
- Pass count, Fail count
- Overall pass rate %

**Filter Dropdown:** Options: "All runs", "This run prefix", "Normal only", "Attack only", "Failed only".

### 5.5 Section 5: Attack Detection Analysis

**Purpose:** Cross-experiment statistics on detection performance.

**Panels:**

| Panel | Data |
|-------|------|
| KPI row: Total Segs / Attack Detected / False Positives | REST GET /api/analysis/summary |
| Confidence distribution histogram | REST GET /api/analysis/confidence_histogram |
| Attack type breakdown donut | REST GET /api/analysis/by_experiment_type |
| Detection time estimate | Computed: segments * window_count * window_interval_ms / 1000 |

**KPI Definitions:**
- **Total Segs:** `COUNT(*)` from gcn_predictions
- **Attack Detected:** `COUNT(*) WHERE prediction = 1`
- **False Positives:** `COUNT(*) WHERE prediction = 1 AND experiment_id LIKE '%normal%'`
- **FPR:** False Positives / (False Positives + True Negatives) as %

**Confidence Histogram:**
10 bins spanning 0.0–1.0 (each bin = 0.1 width). Separate bars for prediction=0 (normal, green) and prediction=1 (attack, red).

**Attack Type Breakdown Donut:**
Groups predictions by experiment suffix:
- attack-neg (negative bias attacks)
- attack-pos (positive bias attacks)
- normal (should be 0 attacks in correct model)

**Detection Time Estimate:**
First segment detection latency = `window_start_idx` of first attack prediction * 100ms (window_interval_ms). This is the number of windows consumed before the first complete segment was ready for inference.

### 5.6 Section 6: Network Health

**Purpose:** Show all 13 telemetry metrics for a selected experiment with trend indicators.

**Panels:**

| Panel | Data |
|-------|------|
| Metrics summary table (all 13) | REST GET /api/experiments/{id}/metrics/summary |
| Backoff slots time series (key attack indicator) | REST GET /api/experiments/{id}/metrics?metric=avg_backoff_slots |
| Optional: any metric selector for time series | REST GET /api/experiments/{id}/metrics?metric=X |

**Metrics Summary Table Columns:**
- Metric name
- Current value (last data point)
- Trend arrow: ↑ if last 10% of samples trending up, ↓ if down, → if flat (within 5% change)
- Min, Max, Avg (over entire experiment)

**Trend Computation:**
Compare average of last 10% of data points to average of first 10%. If ratio > 1.05: up. If < 0.95: down. Else: flat.

**Backoff Slots Highlight:**
The `avg_backoff_slots` row is highlighted with a yellow-orange background because it is the primary indicator of backoff manipulation. Normal range: ~16–1024 slots (EDCA window). Attack-positive adds +3500 bias (monopolizes channel). Attack-negative adds -77% (suppresses backoff, starves others).

---

## 6. Real-Time Pipeline Monitor

### 6.1 Pipeline Stage Node Specification

Each stage node is a 120×100px card with:
- Stage icon (SVG, 24×24px)
- Stage name
- Primary counter (large, bold)
- Secondary label (small, muted)
- Status border (2px solid, colored)
- Status indicator dot (8px, colored, pulsing when active)

Between each pair of adjacent stage nodes is an animated arrow connector:
- 48px wide, 2px height, with an arrow head
- A small dot travels from left to right when `active` (CSS animation `flow-travel`, 1.5s linear infinite)
- Dot color matches the source stage color

### 6.2 Stage Activation Logic

The backend computes stage health by polling the DB every 2 seconds. It sends `pipeline_status` WebSocket events.

**Stage 1 — NS-3:**
```sql
SELECT MAX(ingest_time) AS last_ingest FROM metrics;
```
Active if `(NOW() - last_ingest) < 60 seconds`.
Counter = total rows ingested for the most recently seen `experiment_id`.

**Stage 2 — Exporter:**
Derived from Stage 1. Active when NS-3 is active (exporter ran to produce those metrics).
Counter = same as Stage 1 counter (rows published = rows ingested).

**Stage 3 — Kafka:**
```sql
SELECT COUNT(*) FROM metrics
WHERE experiment_id = (SELECT experiment_id FROM metrics ORDER BY ingest_time DESC LIMIT 1);
```
Active if Stage 1 is active.
Counter = messages stored in DB for latest experiment (proxy for Kafka delivery).

**Stage 4 — Windowizer:**
```sql
SELECT COUNT(DISTINCT segment_id) AS segments
FROM gcn_predictions
WHERE experiment_id = (
    SELECT experiment_id FROM gcn_predictions ORDER BY created_at DESC LIMIT 1
);
```
Active if a `gcn_predictions` row was inserted in the last 120 seconds.
Counter = segment count for latest experiment.

**Stage 5 — GCN Detector:**
```sql
SELECT COUNT(*) AS predictions, MAX(created_at) AS last_pred
FROM gcn_predictions
WHERE experiment_id = (
    SELECT experiment_id FROM gcn_predictions ORDER BY created_at DESC LIMIT 1
);
```
Active if `(NOW() - last_pred) < 120 seconds`.
Counter = prediction count for latest experiment.

**Stage 6 — DB:**
```sql
SELECT COUNT(*) AS total_predictions FROM gcn_predictions;
```
Always active if count > 0.
Counter = total predictions stored.

### 6.3 Activity Feed Events

The backend generates `pipeline_event` WebSocket messages from two sources:

1. **New gcn_predictions rows** (polled every 2s):
```sql
SELECT id, experiment_id, segment_id, prediction, confidence, created_at
FROM gcn_predictions
WHERE id > $last_seen_id
ORDER BY id ASC;
```
For each new row: emit a `pipeline_event` with stage=`GCN`, message=`Segment {seg} → {ATTACK|NORMAL}  conf={confidence:.3f}`, ts=created_at.

2. **New metrics rows** (polled every 5s, batched):
```sql
SELECT experiment_id, COUNT(*) AS new_rows, MAX(ingest_time) AS latest
FROM metrics
WHERE ingest_time > NOW() - INTERVAL '10 seconds'
GROUP BY experiment_id;
```
For each active experiment: emit a `pipeline_event` with stage=`Harmonizer`, message=`{new_rows} rows ingested for {experiment_id}`.

### 6.4 WebSocket Connection Lifecycle

1. Client connects to `ws://host:8888/ws/pipeline`
2. Server immediately sends current `pipeline_status` snapshot
3. Server sends `pipeline_status` every 2 seconds
4. Server sends `pipeline_event` when new DB rows detected (max 10 events per poll cycle)
5. Client reconnects automatically after 5 second delay on disconnect

---

## 7. Backend API Design

### 7.1 FastAPI App Structure

Base URL: `http://host:8888`
All REST endpoints under `/api/`
WebSocket at `/ws/pipeline`
Static files (React build) served at `/` (catch-all)

### 7.2 REST Endpoints

#### Experiments

**GET /api/experiments**
List all experiments with summary statistics.
```
Query params:
  limit: int = 50 (max 200)
  offset: int = 0
  prefix: str = None (filter by YYYYMMDD-HHMM prefix)

Response:
{
  "experiments": [
    {
      "experiment_id": "20260228-1129-seq4-attack-pos",
      "inferred_type": "attack",      // "normal" | "attack" | "unknown"
      "first_ts": "2026-02-28T11:29:00Z",
      "last_ts":  "2026-02-28T11:36:00Z",
      "metric_count": 26000,
      "segment_count": 7,
      "attack_segment_count": 7,
      "normal_segment_count": 0,
      "attack_rate": 1.0,
      "avg_confidence": 0.998,
      "model_version": "v2.0.0",
      "pass_fail": "pass"            // "pass" | "fail" | "unknown"
    }
  ],
  "total": 14,
  "limit": 50,
  "offset": 0
}
```

**GET /api/experiments/{experiment_id}/summary**
Single experiment KPI summary.
```
Response:
{
  "experiment_id": "20260228-1129-seq2-attack-neg",
  "segment_count": 7,
  "attack_segment_count": 7,
  "normal_segment_count": 0,
  "attack_rate": 1.0,
  "avg_confidence": 0.9978,
  "min_confidence": 0.996,
  "max_confidence": 0.999,
  "avg_inference_time_ms": 2.3,
  "model_version": "v2.0.0",
  "ts_start": "2026-02-28T11:29:00Z",
  "ts_end": "2026-02-28T11:36:00Z"
}
```

**GET /api/experiments/{experiment_id}/predictions**
All segment predictions for an experiment.
```
Response:
{
  "predictions": [
    {
      "id": 42,
      "segment_id": "20260228-1129-seq2-attack-neg_ap_0_s0",
      "segment_number": 1,
      "prediction": 1,
      "prediction_label": "attack",
      "confidence": 0.998,
      "p_normal": 0.002,
      "p_attack": 0.998,
      "window_start_idx": 0,
      "window_end_idx": 255,
      "ts_start": "2026-02-28T11:29:00Z",
      "ts_end": "2026-02-28T11:35:36Z",
      "inference_time_ms": 2.1
    }
  ]
}
```

**GET /api/experiments/{experiment_id}/metrics**
Time-series data for a specific metric.
```
Query params:
  metric: str (required, one of the 13 feature keys)
  entity_id: str = None (filter by entity, default: first entity found)
  downsample: int = 500 (max points to return, evenly sampled)

Response:
{
  "experiment_id": "...",
  "metric_name": "avg_backoff_slots",
  "entity_id": "ap_0",
  "unit": "slots",
  "points": [
    {"ts": "2026-02-28T11:29:00.100Z", "value": 34.2},
    {"ts": "2026-02-28T11:29:00.200Z", "value": 35.1},
    ...
  ]
}
```

**GET /api/experiments/{experiment_id}/metrics/summary**
Summary stats for all 13 metrics.
```
Response:
{
  "experiment_id": "...",
  "metrics": [
    {
      "metric_name": "avg_backoff_slots",
      "unit": "slots",
      "current": 3534.2,
      "min": 28.0,
      "max": 3890.0,
      "avg": 1842.5,
      "trend": "up"    // "up" | "down" | "flat"
    }
  ]
}
```

#### Models

**GET /api/models**
List all model versions from registry directory.
```
Response:
{
  "models": [
    {
      "version": "v2.0.0",
      "is_active": true,
      "created": "2026-02-15T10:23:27+05:30",
      "dataset": "data_v2_production",
      "scenarios": 284,
      "has_test_results": true
    },
    {
      "version": "v1.0.0",
      "is_active": false,
      "created": null,
      "has_test_results": true
    },
    {
      "version": "v2.1.0",
      "is_active": false,
      "created": null,
      "has_test_results": false
    }
  ],
  "active_version": "v2.0.0"
}
```

**GET /api/models/active**
Active model details.
```
Response:
{
  "version": "v2.0.0",
  "created": "2026-02-15T10:23:27+05:30",
  "dataset": "data_v2_production",
  "scenarios": 284,
  "distribution": "50-50 balanced",
  "architecture": {
    "in_channels": 16,
    "hidden_channels": 64,
    "num_layers": 2,
    "dropout": 0.3,
    "pooling": "mean",
    "segment_length": 256,
    "batch_size": 32
  },
  "test_results": {
    "accuracy": 0.9949,
    "precision": 0.9886,
    "recall": 1.0,
    "f1": 0.9943,
    "auc": 1.0,
    "confusion_matrix": [[107, 1], [0, 87]],
    "best_epoch": 3
  }
}
```

**GET /api/models/{version}/test_results**
Test results for a specific version.
```
Response: same shape as "test_results" above, or {"error": "no test_results.json"} if missing
```

**GET /api/models/active/inference_stats**
Runtime inference statistics computed from DB.
```
Response:
{
  "count": 56,
  "min_ms": 1.8,
  "p50_ms": 2.3,
  "p95_ms": 3.1,
  "max_ms": 4.2,
  "avg_ms": 2.4
}
```

SQL:
```sql
SELECT
  COUNT(*) AS count,
  MIN(inference_time_ms) AS min_ms,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY inference_time_ms) AS p50_ms,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY inference_time_ms) AS p95_ms,
  MAX(inference_time_ms) AS max_ms,
  AVG(inference_time_ms) AS avg_ms
FROM gcn_predictions
WHERE inference_time_ms IS NOT NULL;
```

#### Analysis

**GET /api/analysis/summary**
Cross-experiment detection statistics.
```
Response:
{
  "total_segments": 56,
  "attack_segments": 28,
  "normal_segments": 28,
  "false_positives": 0,
  "false_negatives": 0,
  "true_positives": 28,
  "true_negatives": 28,
  "precision": 1.0,
  "recall": 1.0,
  "fpr": 0.0,
  "fnr": 0.0
}
```

Note: True positive/negative inference uses experiment_id suffix pattern — experiments containing "normal" are labeled negative class, experiments containing "attack" are labeled positive class.

**GET /api/analysis/confidence_histogram**
Confidence distribution split by prediction class.
```
Query params:
  bins: int = 10

Response:
{
  "bins": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
  "normal_counts": [28, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  "attack_counts":  [0,  0, 0, 0, 0, 0, 0, 0, 0, 28]
}
```

**GET /api/analysis/by_experiment_type**
Attack count grouped by inferred experiment type.
```
Response:
{
  "groups": [
    {"type": "attack-neg", "total_segments": 14, "attack_segments": 14},
    {"type": "attack-pos", "total_segments": 14, "attack_segments": 14},
    {"type": "normal",     "total_segments": 28, "attack_segments": 0}
  ]
}
```

#### Pipeline

**GET /api/pipeline/status**
Current pipeline stage status (same data as WebSocket snapshot).
```
Response:
{
  "stages": {
    "ns3":       {"state": "idle",   "counter": 26000, "label": "events"},
    "exporter":  {"state": "idle",   "counter": 26000, "label": "sent"},
    "kafka":     {"state": "idle",   "counter": 26000, "label": "stored"},
    "windowizer":{"state": "idle",   "counter": 7,     "label": "segments"},
    "gcn":       {"state": "idle",   "counter": 7,     "label": "predictions"},
    "db":        {"state": "active", "counter": 56,    "label": "total"}
  },
  "latest_experiment_id": "20260228-1129-seq4-attack-pos",
  "last_updated": "2026-02-28T14:32:01Z"
}
```

### 7.3 WebSocket Endpoint

**WS /ws/pipeline**

After connection, server sends two types of messages:

**Type 1: pipeline_status** (every 2 seconds)
```json
{
  "type": "pipeline_status",
  "ts": "2026-02-28T14:32:01Z",
  "stages": {
    "ns3":        {"state": "idle",   "counter": 26000, "label": "events"},
    "exporter":   {"state": "idle",   "counter": 26000, "label": "sent"},
    "kafka":      {"state": "idle",   "counter": 26000, "label": "stored"},
    "windowizer": {"state": "idle",   "counter": 7,     "label": "segments"},
    "gcn":        {"state": "idle",   "counter": 7,     "label": "predictions"},
    "db":         {"state": "active", "counter": 56,    "label": "total"}
  },
  "latest_experiment_id": "20260228-1129-seq4-attack-pos"
}
```

**Type 2: pipeline_event** (triggered by new DB rows)
```json
{
  "type": "pipeline_event",
  "ts": "2026-02-28T14:32:01Z",
  "stage": "gcn",
  "level": "info",
  "message": "Segment 7/7 → ATTACK  conf=0.998",
  "experiment_id": "20260228-1129-seq4-attack-pos"
}
```

---

## 8. WebSocket Event Specification

### 8.1 All Event Types

| Event Type | Trigger | Frequency |
|-----------|---------|-----------|
| `pipeline_status` | Timer (every 2s) | Always, while connected |
| `pipeline_event` | New `gcn_predictions` row | When new predictions appear |
| `pipeline_event` | New `metrics` batch | When new metrics ingested |
| `connection_ack` | On WebSocket open | Once at connection |
| `error` | Backend exception | On error |

### 8.2 Event Payload Shapes

#### connection_ack
```json
{
  "type": "connection_ack",
  "ts": "2026-02-28T14:32:01Z",
  "server_version": "1.0.0",
  "message": "Connected to NDT pipeline monitor"
}
```

#### pipeline_status (full schema)
```json
{
  "type": "pipeline_status",
  "ts": "2026-02-28T14:32:01Z",
  "stages": {
    "ns3": {
      "state": "idle",
      "counter": 26000,
      "label": "events",
      "last_activity_ts": "2026-02-28T11:36:00Z"
    },
    "exporter": {
      "state": "idle",
      "counter": 26000,
      "label": "sent",
      "last_activity_ts": "2026-02-28T11:36:00Z"
    },
    "kafka": {
      "state": "idle",
      "counter": 26000,
      "label": "stored",
      "last_activity_ts": "2026-02-28T11:36:00Z"
    },
    "windowizer": {
      "state": "idle",
      "counter": 7,
      "label": "segments",
      "last_activity_ts": "2026-02-28T11:41:00Z"
    },
    "gcn": {
      "state": "idle",
      "counter": 7,
      "label": "predictions",
      "last_activity_ts": "2026-02-28T11:41:05Z"
    },
    "db": {
      "state": "active",
      "counter": 56,
      "label": "total predictions",
      "last_activity_ts": "2026-02-28T11:41:05Z"
    }
  },
  "latest_experiment_id": "20260228-1129-seq4-attack-pos",
  "active_model_version": "v2.0.0"
}
```

#### pipeline_event (prediction)
```json
{
  "type": "pipeline_event",
  "ts": "2026-02-28T14:32:01.234Z",
  "stage": "gcn",
  "level": "info",
  "message": "Segment 7/7 \u2192 ATTACK  conf=0.998",
  "experiment_id": "20260228-1129-seq4-attack-pos",
  "prediction": 1,
  "confidence": 0.998,
  "segment_number": 7
}
```

#### pipeline_event (metrics ingest)
```json
{
  "type": "pipeline_event",
  "ts": "2026-02-28T14:32:01.234Z",
  "stage": "harmonizer",
  "level": "info",
  "message": "3380 rows ingested for 20260228-1129-seq4-attack-pos",
  "experiment_id": "20260228-1129-seq4-attack-pos",
  "row_count": 3380
}
```

#### error
```json
{
  "type": "error",
  "ts": "2026-02-28T14:32:01Z",
  "code": "DB_UNAVAILABLE",
  "message": "Cannot connect to TimescaleDB"
}
```

### 8.3 Frontend Component WebSocket Subscriptions

| Component | Subscribes to |
|-----------|--------------|
| `PipelineMonitor` | `pipeline_status`, `pipeline_event` |
| `PipelineStageNode` (all 6) | `pipeline_status` (stage field) |
| `ActivityFeed` | `pipeline_event` |
| `TopBar` (live indicator) | `connection_ack`, `error` |
| All others | REST only (no WebSocket) |

---

## 9. Frontend Component Tree

### 9.1 Complete Hierarchy

```
App
├── TopBar
│   ├── Logo
│   ├── LiveIndicator          (WebSocket connected/disconnected dot)
│   └── CurrentTime
├── Sidebar
│   ├── CollapseButton
│   └── NavItem × 6            (one per section)
└── MainContent
    ├── SectionPipelineMonitor  (section 1)
    │   ├── SectionTitle
    │   ├── PipelineFlowDiagram
    │   │   ├── PipelineStageNode × 6
    │   │   └── FlowConnector × 5
    │   └── ActivityFeed
    │       └── ActivityFeedItem × N
    │
    ├── SectionExperimentView   (section 2)
    │   ├── SectionTitle
    │   ├── ExperimentSelector  (dropdown)
    │   ├── KpiRow
    │   │   └── KpiCard × 4
    │   ├── MetricChart
    │   │   ├── MetricSelector  (dropdown)
    │   │   └── LineChart       (Recharts)
    │   ├── PredictionsTable
    │   │   └── PredictionRow × N
    │   └── ConfidenceHistogram (Recharts BarChart)
    │
    ├── SectionModelIntelligence (section 3)
    │   ├── SectionTitle
    │   ├── ModelInfoCard
    │   ├── ConfusionMatrix
    │   ├── PerformanceBarChart  (Recharts BarChart horizontal)
    │   ├── ModelVersionList
    │   │   └── ModelVersionItem × N
    │   └── InferenceLatencyCard
    │
    ├── SectionRunHistory        (section 4)
    │   ├── SectionTitle
    │   ├── FilterDropdown
    │   ├── ExperimentTable
    │   │   └── ExperimentTableRow × N
    │   ├── RunGroupSummaryCard
    │   └── AttackRateBarChart   (Recharts BarChart)
    │
    ├── SectionAttackAnalysis    (section 5)
    │   ├── SectionTitle
    │   ├── KpiRow
    │   │   └── KpiCard × 3
    │   ├── ConfidenceHistogram  (Recharts BarChart grouped)
    │   ├── AttackTypeDonut      (Recharts PieChart)
    │   └── DetectionTimeCard
    │
    └── SectionNetworkHealth     (section 6)
        ├── SectionTitle
        ├── ExperimentSelector   (shared with section 2 via context)
        ├── MetricsTable
        │   └── MetricTableRow × 13
        └── BackoffSlotsChart    (Recharts LineChart, always shown)
```

### 9.2 State Management

**No external state library** (no Redux, no Zustand) — React built-in useState + useContext is sufficient.

**Global Context:**
```
AppContext provides:
  - wsStatus: "connected" | "disconnected" | "error"
  - pipelineStatus: PipelineStatusPayload | null
  - activityFeed: PipelineEventPayload[]   (circular buffer, max 50)
  - selectedExperimentId: string | null
  - setSelectedExperimentId: (id: string) => void
  - activeSection: SectionId
  - setActiveSection: (id: SectionId) => void
```

**Section-local state (useState):**
- `SectionExperimentView`: experiments list, experiment summary, predictions, metrics data, selected metric, loading flags
- `SectionModelIntelligence`: active model data, model list, inference stats
- `SectionRunHistory`: experiments list, run groups, filter value
- `SectionAttackAnalysis`: analysis summary, histogram data, by-type data
- `SectionNetworkHealth`: metrics summary, backoff time series, selected metric

**Components with no state (pure display):**
- `KpiCard`, `PipelineStageNode`, `FlowConnector`, `ActivityFeedItem`, `PredictionRow`, `MetricTableRow`, `ModelVersionItem`, `ConfusionMatrix`

### 9.3 Data Fetching

All REST calls use the native browser `fetch` API with `async/await` inside `useEffect`. Custom hook pattern:

```
useExperimentSummary(experimentId)       → fetches on mount and id change
useExperimentPredictions(experimentId)   → fetches on id change
useExperimentMetrics(experimentId, metric) → fetches on id/metric change
useModelActive()                         → fetches once on mount
useModels()                              → fetches once on mount
useInferenceStats()                      → fetches once on mount
useExperiments(filter, limit, offset)    → fetches on filter change
useAnalysisSummary()                     → fetches once on mount
useConfidenceHistogram()                 → fetches once on mount
useAttackByType()                        → fetches once on mount
useMetricsSummary(experimentId)          → fetches on id change
```

---

## 10. Data Sources and Key SQL Queries

### 10.1 Experiment List Query

```sql
WITH experiment_stats AS (
    SELECT
        experiment_id,
        MIN(ts) AS first_ts,
        MAX(ts) AS last_ts,
        COUNT(*) AS metric_count
    FROM metrics
    GROUP BY experiment_id
),
prediction_stats AS (
    SELECT
        experiment_id,
        COUNT(*) AS segment_count,
        SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) AS attack_segment_count,
        SUM(CASE WHEN prediction = 0 THEN 1 ELSE 0 END) AS normal_segment_count,
        AVG(confidence) AS avg_confidence,
        MAX(model_version) AS model_version
    FROM gcn_predictions
    GROUP BY experiment_id
)
SELECT
    e.experiment_id,
    e.first_ts,
    e.last_ts,
    e.metric_count,
    COALESCE(p.segment_count, 0) AS segment_count,
    COALESCE(p.attack_segment_count, 0) AS attack_segment_count,
    COALESCE(p.normal_segment_count, 0) AS normal_segment_count,
    CASE
        WHEN p.segment_count > 0
        THEN ROUND((p.attack_segment_count::float / p.segment_count) * 100, 2)
        ELSE NULL
    END AS attack_rate_pct,
    ROUND(p.avg_confidence * 100, 2) AS avg_confidence_pct,
    p.model_version
FROM experiment_stats e
LEFT JOIN prediction_stats p USING (experiment_id)
ORDER BY e.first_ts DESC
LIMIT $1 OFFSET $2;
```

### 10.2 Experiment Summary Query

```sql
SELECT
    p.experiment_id,
    COUNT(*) AS segment_count,
    SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) AS attack_segment_count,
    SUM(CASE WHEN prediction = 0 THEN 1 ELSE 0 END) AS normal_segment_count,
    AVG(confidence) AS avg_confidence,
    MIN(confidence) AS min_confidence,
    MAX(confidence) AS max_confidence,
    AVG(inference_time_ms) AS avg_inference_time_ms,
    MAX(model_version) AS model_version,
    MIN(ts_start) AS ts_start,
    MAX(ts_end) AS ts_end
FROM gcn_predictions p
WHERE experiment_id = $1
GROUP BY p.experiment_id;
```

### 10.3 Segment Predictions Query

```sql
SELECT
    id,
    segment_id,
    prediction,
    confidence,
    probabilities,
    window_start_idx,
    window_end_idx,
    ts_start,
    ts_end,
    inference_time_ms,
    model_version,
    created_at,
    ROW_NUMBER() OVER (ORDER BY ts_start ASC) AS segment_number
FROM gcn_predictions
WHERE experiment_id = $1
ORDER BY ts_start ASC;
```

### 10.4 Metric Time Series Query

```sql
SELECT
    ts,
    value,
    unit,
    entity_id
FROM metrics
WHERE experiment_id = $1
  AND metric_name = $2
  AND entity_id = COALESCE($3, entity_id)
ORDER BY ts ASC;
```

For downsampling to N points (server-side):
```sql
SELECT
    ts,
    value
FROM (
    SELECT
        ts,
        value,
        ROW_NUMBER() OVER (ORDER BY ts ASC) AS rn,
        COUNT(*) OVER () AS total
    FROM metrics
    WHERE experiment_id = $1
      AND metric_name = $2
) sub
WHERE MOD(rn - 1, GREATEST(total / $3, 1)) = 0
   OR rn = total
ORDER BY ts ASC;
```

### 10.5 Metrics Summary Query (All 13 Metrics)

```sql
WITH ordered_metrics AS (
    SELECT
        metric_name,
        value,
        unit,
        ROW_NUMBER() OVER (PARTITION BY metric_name ORDER BY ts DESC) AS rn_desc,
        ROW_NUMBER() OVER (PARTITION BY metric_name ORDER BY ts ASC)  AS rn_asc,
        COUNT(*) OVER (PARTITION BY metric_name) AS total_count
    FROM metrics
    WHERE experiment_id = $1
      AND metric_name = ANY($2::text[])
)
SELECT
    metric_name,
    MAX(unit) AS unit,
    AVG(value) AS avg_value,
    MIN(value) AS min_value,
    MAX(value) AS max_value,
    (ARRAY_AGG(value ORDER BY rn_desc DESC) FILTER (WHERE rn_desc = 1))[1] AS current_value,
    -- Trend: compare last 10% to first 10% of data
    AVG(value) FILTER (WHERE rn_desc <= GREATEST(total_count / 10, 1)) AS last_10pct_avg,
    AVG(value) FILTER (WHERE rn_asc  <= GREATEST(total_count / 10, 1)) AS first_10pct_avg
FROM ordered_metrics
GROUP BY metric_name;
```

### 10.6 Pipeline Status Queries (Backend Polling)

**Latest experiment and ingest recency:**
```sql
SELECT
    experiment_id,
    COUNT(*) AS metric_count,
    MAX(ingest_time) AS latest_ingest,
    EXTRACT(EPOCH FROM (NOW() - MAX(ingest_time))) AS seconds_since_last_ingest
FROM metrics
GROUP BY experiment_id
ORDER BY MAX(ingest_time) DESC
LIMIT 1;
```

**Latest prediction experiment:**
```sql
SELECT
    experiment_id,
    COUNT(*) AS segment_count,
    MAX(created_at) AS latest_pred,
    EXTRACT(EPOCH FROM (NOW() - MAX(created_at))) AS seconds_since_last_pred
FROM gcn_predictions
GROUP BY experiment_id
ORDER BY MAX(created_at) DESC
LIMIT 1;
```

**Total prediction count:**
```sql
SELECT COUNT(*) AS total FROM gcn_predictions;
```

### 10.7 Analysis Summary Query

```sql
SELECT
    COUNT(*) AS total_segments,
    SUM(CASE WHEN prediction = 1 THEN 1 ELSE 0 END) AS attack_segments,
    SUM(CASE WHEN prediction = 0 THEN 1 ELSE 0 END) AS normal_segments,
    -- FP: predicted attack on a "normal" experiment
    SUM(CASE
        WHEN prediction = 1
         AND experiment_id ~* 'normal'
        THEN 1 ELSE 0
    END) AS false_positives,
    -- FN: predicted normal on an "attack" experiment
    SUM(CASE
        WHEN prediction = 0
         AND experiment_id ~* 'attack'
        THEN 1 ELSE 0
    END) AS false_negatives,
    -- TP: predicted attack on an "attack" experiment
    SUM(CASE
        WHEN prediction = 1
         AND experiment_id ~* 'attack'
        THEN 1 ELSE 0
    END) AS true_positives,
    -- TN: predicted normal on a "normal" experiment
    SUM(CASE
        WHEN prediction = 0
         AND experiment_id ~* 'normal'
        THEN 1 ELSE 0
    END) AS true_negatives
FROM gcn_predictions;
```

### 10.8 Confidence Histogram Query

```sql
WITH bins AS (
    SELECT
        prediction,
        confidence,
        WIDTH_BUCKET(confidence, 0, 1.0, 10) - 1 AS bin_idx
    FROM gcn_predictions
    WHERE confidence IS NOT NULL
)
SELECT
    prediction,
    bin_idx,
    COUNT(*) AS count
FROM bins
GROUP BY prediction, bin_idx
ORDER BY prediction, bin_idx;
```

### 10.9 Inference Latency Percentiles Query

```sql
SELECT
    COUNT(*) AS count,
    MIN(inference_time_ms) AS min_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY inference_time_ms) AS p50_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY inference_time_ms) AS p95_ms,
    MAX(inference_time_ms) AS max_ms,
    ROUND(AVG(inference_time_ms)::numeric, 2) AS avg_ms
FROM gcn_predictions
WHERE inference_time_ms IS NOT NULL;
```

### 10.10 New Predictions Polling Query (WebSocket backend)

```sql
SELECT
    id,
    experiment_id,
    segment_id,
    prediction,
    confidence,
    created_at,
    model_version
FROM gcn_predictions
WHERE id > $1
ORDER BY id ASC
LIMIT 10;
```

---

## 11. Docker Setup

### 11.1 Multi-Stage Dockerfile

File path: `dashboard/app/Dockerfile`

**Stage 1 (Node builder):** Build the React SPA with Vite.
**Stage 2 (Python runtime):** FastAPI server that serves the built static files.

```
# Stage 1: Build React frontend
FROM node:20-alpine AS builder

WORKDIR /build

# Copy package files first (cache layer optimization)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy source and build
COPY frontend/ .
RUN npm run build
# Output: /build/dist/

# Stage 2: Python FastAPI backend + static files
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend from builder
COPY --from=builder /build/dist ./static/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8888/api/health')"

EXPOSE 8888

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8888"]
```

### 11.2 Python Requirements

File path: `dashboard/app/backend/requirements.txt`

```
fastapi==0.110.0
uvicorn[standard]==0.27.1
asyncpg==0.29.0
pydantic==2.6.0
python-multipart==0.0.9
aiofiles==23.2.1
PyYAML==6.0.1
```

### 11.3 Docker Compose Service Entry

Add to `docker-compose.pipeline.yml` (new service at bottom):

```yaml
  dashboard:
    build:
      context: ./dashboard/app
      dockerfile: Dockerfile
    image: ndt/dashboard:local
    container_name: ndt-dashboard
    restart: unless-stopped
    networks:
      - clab-mgmt
    environment:
      PG_HOST: ${PG_HOST:-udr-db}
      PG_PORT: ${PG_PORT:-5432}
      PG_DB: ${PG_DB:-udr}
      PG_USER: ${PG_USER:-udr}
      PG_PASS: ${PG_PASS:-udr_pass}
      # Path to GCN model registry (mounted from host)
      GCN_REGISTRY_PATH: /app/registry
      # CORS allowed origins (set to * for lab use)
      CORS_ORIGINS: "*"
    volumes:
      # Mount model registry read-only for config.yaml / test_results.json access
      - ./twin/registry/gcn:/app/registry:ro
    ports:
      - "8888:8888"
    depends_on:
      - harmonizer
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### 11.4 Containerlab Topology Addition (Optional)

If adding dashboard to `clab/topo.yml` directly (alternative to docker-compose), add to the `nodes` section:

```yaml
    dashboard:
      kind: linux
      image: ndt/dashboard:local
      mgmt-ipv4: 172.30.20.50
      ports:
        - "8888:8888"
      env:
        PG_HOST: udr-db
        PG_PORT: "5432"
        PG_DB: udr
        PG_USER: udr
        PG_PASS: udr_pass
        GCN_REGISTRY_PATH: /app/registry
```

**Recommendation:** Use the `docker-compose.pipeline.yml` approach (not containerlab) to keep the dashboard consistent with windowizer and gcn-detector lifecycle management.

### 11.5 Makefile Targets

Add to `Makefile`:

```makefile
# =============================================================================
# Dashboard (Custom Web UI)
# =============================================================================

.PHONY: dashboard-build dashboard-run dashboard-stop dashboard-logs

DASHBOARD_IMAGE=ndt/dashboard:local

dashboard-build:
	@echo "Building dashboard image (frontend + backend)..."
	@docker build -t $(DASHBOARD_IMAGE) dashboard/app/

dashboard-run:
	@echo "Starting dashboard..."
	@docker compose -f docker-compose.pipeline.yml up -d dashboard

dashboard-stop:
	@docker compose -f docker-compose.pipeline.yml stop dashboard

dashboard-logs:
	@docker compose -f docker-compose.pipeline.yml logs -f dashboard
```

Dashboard accessible at: `http://localhost:8888`

### 11.6 Volume Mounts

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./twin/registry/gcn` | `/app/registry` | Read model configs and test_results.json |

No other volume mounts needed — DB access is via network connection.

### 11.7 Build-Time Environment

The React frontend needs to know the API base URL at build time (Vite env vars):

File: `dashboard/app/frontend/.env.production`
```
VITE_API_BASE_URL=
VITE_WS_BASE_URL=
```

Both left empty means relative URLs (`/api/...` and `ws://same-host/ws/...`), which works because FastAPI serves both the API and the static files on port 8888.

File: `dashboard/app/frontend/.env.development`
```
VITE_API_BASE_URL=http://localhost:8888
VITE_WS_BASE_URL=ws://localhost:8888
```

---

## 12. File and Directory Structure

### 12.1 Complete File Tree

```
dashboard/
├── app/
│   ├── Dockerfile                           # Multi-stage build
│   ├── .dockerignore                        # Exclude node_modules, __pycache__
│   │
│   ├── backend/                             # FastAPI Python backend
│   │   ├── main.py                          # App factory, CORS, static files, routes
│   │   ├── requirements.txt                 # Python deps (fastapi, asyncpg, etc.)
│   │   │
│   │   ├── api/                             # REST route handlers
│   │   │   ├── __init__.py
│   │   │   ├── experiments.py               # /api/experiments routes
│   │   │   ├── models.py                    # /api/models routes
│   │   │   ├── analysis.py                  # /api/analysis routes
│   │   │   └── pipeline.py                  # /api/pipeline/status route
│   │   │
│   │   ├── ws/                              # WebSocket handlers
│   │   │   ├── __init__.py
│   │   │   └── pipeline.py                  # /ws/pipeline WebSocket
│   │   │
│   │   ├── db/                              # Database layer
│   │   │   ├── __init__.py
│   │   │   ├── connection.py                # asyncpg pool setup
│   │   │   └── queries.py                   # All SQL query functions
│   │   │
│   │   ├── registry/                        # Model registry reader
│   │   │   ├── __init__.py
│   │   │   └── reader.py                    # Read config.yaml + test_results.json
│   │   │
│   │   └── models/                          # Pydantic response models
│   │       ├── __init__.py
│   │       ├── experiments.py               # ExperimentSummary, PredictionRow, etc.
│   │       ├── models.py                    # ModelInfo, TestResults, etc.
│   │       ├── analysis.py                  # AnalysisSummary, Histogram, etc.
│   │       └── pipeline.py                  # PipelineStatus, PipelineEvent, etc.
│   │
│   └── frontend/                            # React frontend
│       ├── package.json                     # npm deps (react, vite, recharts, tailwind)
│       ├── package-lock.json
│       ├── vite.config.ts                   # Vite config with proxy for dev
│       ├── tailwind.config.ts               # Tailwind CSS config
│       ├── tsconfig.json                    # TypeScript config
│       ├── index.html                       # Entry HTML
│       ├── .env.development                 # Dev API URL
│       ├── .env.production                  # Prod (empty = relative URLs)
│       │
│       └── src/
│           ├── main.tsx                     # React DOM render entry
│           ├── App.tsx                      # Root component, routing, context
│           ├── index.css                    # Global styles, CSS variables
│           │
│           ├── context/
│           │   └── AppContext.tsx           # Global state context + WebSocket mgr
│           │
│           ├── hooks/                       # Data fetching hooks
│           │   ├── useExperiments.ts
│           │   ├── useExperimentSummary.ts
│           │   ├── useExperimentPredictions.ts
│           │   ├── useExperimentMetrics.ts
│           │   ├── useMetricsSummary.ts
│           │   ├── useModelActive.ts
│           │   ├── useModels.ts
│           │   ├── useInferenceStats.ts
│           │   ├── useAnalysisSummary.ts
│           │   ├── useConfidenceHistogram.ts
│           │   └── useAttackByType.ts
│           │
│           ├── components/
│           │   ├── layout/
│           │   │   ├── TopBar.tsx
│           │   │   ├── Sidebar.tsx
│           │   │   ├── SidebarNavItem.tsx
│           │   │   └── MainContent.tsx
│           │   │
│           │   ├── common/
│           │   │   ├── KpiCard.tsx          # Stat card (value + label)
│           │   │   ├── SectionTitle.tsx
│           │   │   ├── LoadingSpinner.tsx
│           │   │   ├── ErrorBanner.tsx
│           │   │   ├── LiveIndicator.tsx    # Pulsing green dot
│           │   │   └── Badge.tsx            # Colored pill badge
│           │   │
│           │   ├── pipeline/
│           │   │   ├── PipelineFlowDiagram.tsx
│           │   │   ├── PipelineStageNode.tsx
│           │   │   ├── FlowConnector.tsx
│           │   │   └── ActivityFeed.tsx
│           │   │
│           │   ├── charts/
│           │   │   ├── MetricLineChart.tsx  # Recharts LineChart wrapper
│           │   │   ├── ConfidenceHistogram.tsx
│           │   │   ├── PerformanceBarChart.tsx
│           │   │   ├── AttackRateBarChart.tsx
│           │   │   └── AttackTypeDonut.tsx
│           │   │
│           │   └── model/
│           │       ├── ConfusionMatrix.tsx
│           │       ├── ModelInfoCard.tsx
│           │       └── ModelVersionItem.tsx
│           │
│           ├── sections/
│           │   ├── SectionPipelineMonitor.tsx
│           │   ├── SectionExperimentView.tsx
│           │   ├── SectionModelIntelligence.tsx
│           │   ├── SectionRunHistory.tsx
│           │   ├── SectionAttackAnalysis.tsx
│           │   └── SectionNetworkHealth.tsx
│           │
│           └── types/
│               ├── experiments.ts           # TypeScript interfaces
│               ├── models.ts
│               ├── analysis.ts
│               └── pipeline.ts
│
└── grafana/                                 # (existing) Grafana dashboards
    └── ...
```

### 12.2 Key File Purposes

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app with lifespan DB pool init, CORS, static file mount, router inclusion |
| `backend/db/connection.py` | asyncpg pool: created at startup, shared via app state |
| `backend/db/queries.py` | All SQL query functions (async def get_experiments(), etc.) |
| `backend/ws/pipeline.py` | WebSocket handler with 2s polling loop, sends status + events |
| `backend/registry/reader.py` | Reads `GCN_REGISTRY_PATH` env var, reads config.yaml + test_results.json |
| `frontend/src/context/AppContext.tsx` | WebSocket connection management, global state |
| `frontend/src/index.css` | All CSS variable definitions (colors, shadows, radius, animations) |

---

## 13. Implementation Phases

### Phase 1: Backend Foundation (Est. 4-6 hours)

**Goal:** Working FastAPI backend with DB connection, all REST endpoints, WebSocket stub.

**Deliverables:**
1. Directory structure created (`dashboard/app/backend/`, `dashboard/app/frontend/`)
2. `backend/main.py` — FastAPI app with CORS, health endpoint `/api/health`
3. `backend/db/connection.py` — asyncpg pool initialized from env vars
4. `backend/db/queries.py` — all SQL query functions (no business logic)
5. `backend/api/experiments.py` — `/api/experiments`, `/api/experiments/{id}/summary`, `/api/experiments/{id}/predictions`, `/api/experiments/{id}/metrics`, `/api/experiments/{id}/metrics/summary`
6. `backend/api/models.py` — `/api/models`, `/api/models/active`, `/api/models/{version}/test_results`, `/api/models/active/inference_stats`
7. `backend/api/analysis.py` — `/api/analysis/summary`, `/api/analysis/confidence_histogram`, `/api/analysis/by_experiment_type`
8. `backend/api/pipeline.py` — `/api/pipeline/status`
9. `backend/ws/pipeline.py` — WebSocket `/ws/pipeline` with 2s polling loop
10. `backend/registry/reader.py` — reads model registry files from `GCN_REGISTRY_PATH`
11. `backend/models/` — all Pydantic response models

**Verification:**
```bash
cd dashboard/app
pip install -r backend/requirements.txt
PG_HOST=localhost PG_PORT=5432 PG_DB=udr PG_USER=udr PG_PASS=udr_pass \
  GCN_REGISTRY_PATH=../../twin/registry/gcn \
  uvicorn backend.main:app --host 0.0.0.0 --port 8888 --reload

# Test endpoints
curl http://localhost:8888/api/health
curl http://localhost:8888/api/experiments | python3 -m json.tool
curl http://localhost:8888/api/models/active | python3 -m json.tool
curl http://localhost:8888/api/analysis/summary | python3 -m json.tool
# WebSocket test:
# Open browser console: new WebSocket("ws://localhost:8888/ws/pipeline")
```

---

### Phase 2: Frontend Scaffold and Design System (Est. 4-6 hours)

**Goal:** React app with Vite, Tailwind, CSS design system, layout structure (sidebar + sections), and static mock data rendering.

**Deliverables:**
1. `frontend/package.json` — dependencies: react 18, vite 5, tailwindcss 3, recharts 2, typescript 5
2. `frontend/vite.config.ts` — proxy `/api` and `/ws` to `http://localhost:8888` for dev
3. `frontend/tailwind.config.ts` — theme extension with custom CSS variable references
4. `frontend/src/index.css` — all CSS variables (colors, shadows, radius, animations per Section 3)
5. `frontend/src/App.tsx` — root component with AppContext provider, sidebar + main layout
6. `frontend/src/context/AppContext.tsx` — WebSocket connection, global state
7. `frontend/src/components/layout/TopBar.tsx` — logo, live indicator, time
8. `frontend/src/components/layout/Sidebar.tsx` — collapsible, 6 nav items
9. `frontend/src/components/common/KpiCard.tsx` — neumorphic stat card
10. `frontend/src/components/common/Badge.tsx` — color-coded pill badge
11. All 6 section files in `frontend/src/sections/` — skeleton structure with `SectionTitle` and placeholder content
12. `frontend/src/types/` — all TypeScript interfaces

**Verification:**
```bash
cd dashboard/app/frontend
npm install
npm run dev
# Open http://localhost:5173
# Should see: TopBar, collapsible sidebar with 6 nav items, each section shows title + placeholder
# Sidebar collapses to icon-only mode on button click
# TopBar live indicator shows disconnected state initially
```

---

### Phase 3: Pipeline Monitor and Charts (Est. 6-8 hours)

**Goal:** Working Pipeline Monitor section with real WebSocket data, and reusable chart components.

**Deliverables:**
1. `frontend/src/components/pipeline/PipelineFlowDiagram.tsx` — 6-node horizontal flow with FlowConnectors
2. `frontend/src/components/pipeline/PipelineStageNode.tsx` — stage card with state colors, pulsing animation, counter
3. `frontend/src/components/pipeline/FlowConnector.tsx` — arrow with traveling dot animation
4. `frontend/src/components/pipeline/ActivityFeed.tsx` — scrollable event log with timestamp + colored stage labels
5. `frontend/src/sections/SectionPipelineMonitor.tsx` — complete, wired to AppContext WebSocket data
6. `frontend/src/components/charts/MetricLineChart.tsx` — Recharts LineChart with proper axes, grid, tooltip
7. `frontend/src/components/charts/ConfidenceHistogram.tsx` — Recharts BarChart with two series (normal/attack)
8. `frontend/src/components/charts/PerformanceBarChart.tsx` — horizontal bars for F1/Acc/etc.
9. `frontend/src/components/charts/AttackRateBarChart.tsx` — bar chart per experiment
10. `frontend/src/components/charts/AttackTypeDonut.tsx` — Recharts PieChart

**Verification:**
- Pipeline Monitor shows 6 stage nodes
- With pipeline running, stages change color (active → green)
- Activity feed shows new GCN predictions as they arrive
- MetricLineChart renders with correct time axis and values when passed mock data
- All chart components render without errors in Storybook (or simple test page)

---

### Phase 4: All Sections Wired to Backend (Est. 8-10 hours)

**Goal:** All 6 sections fully wired to REST API and WebSocket, with real data from TimescaleDB.

**Deliverables:**
1. All hooks in `frontend/src/hooks/` — implement fetch logic with loading/error states
2. `SectionExperimentView.tsx` — experiment selector, KPI row, metric chart, predictions table, confidence histogram — all wired to API
3. `SectionModelIntelligence.tsx` — model info card, confusion matrix, performance bars, version list, inference latency card — all wired to API
4. `SectionRunHistory.tsx` — experiment table with pass/fail, run group summary, attack rate chart — wired to API
5. `SectionAttackAnalysis.tsx` — KPI row, confidence histogram, donut chart, detection time card — wired to API
6. `SectionNetworkHealth.tsx` — metrics table with trends, backoff slots chart — wired to API
7. `frontend/src/components/model/ConfusionMatrix.tsx` — 2x2 grid with colored cells
8. `frontend/src/components/model/ModelInfoCard.tsx` — structured model details card
9. `frontend/src/components/model/ModelVersionItem.tsx` — version entry with active/retired badges

**Verification:**
```bash
# With TimescaleDB running and populated (make pipeline-up && ./run_scenarios.sh):
npm run dev
# Section 2: Select any experiment — should see segment count, attack rate, confidence
# Section 2: Select avg_backoff_slots metric — chart shows spike for attack experiments
# Section 3: Shows v2.0.0 as active model with F1=99.4%, confusion matrix matches test_results.json
# Section 4: Shows all experiments with correct pass/fail badges
# Section 5: Shows analysis summary with correct FP count
# Section 6: Shows all 13 metrics for selected experiment
```

---

### Phase 5: Docker Build, Integration, and Polish (Est. 4-6 hours)

**Goal:** Docker image builds cleanly, joins `clab-mgmt`, serves correctly on port 8888. Visual polish pass.

**Deliverables:**
1. `dashboard/app/Dockerfile` — multi-stage (Node builder + Python runtime)
2. `dashboard/app/.dockerignore`
3. `docker-compose.pipeline.yml` — add `dashboard` service
4. `Makefile` — add `dashboard-build`, `dashboard-run`, `dashboard-stop`, `dashboard-logs` targets
5. `frontend/src/index.css` — final polish pass: hover effects, transition durations, responsive min-width
6. `frontend/src/App.tsx` — ensure scroll behavior: sidebar fixed, main content scrollable
7. `frontend/src/components/common/LoadingSpinner.tsx` — neumorphic loading state
8. `frontend/src/components/common/ErrorBanner.tsx` — error display with retry button
9. Visual polish: ensure all cards use `--shadow-clay`, hover lift, consistent border-radius
10. Ensure experiment selector in Section 2 and Section 6 are synced via AppContext `selectedExperimentId`

**Verification:**
```bash
# Build and run in Docker:
make dashboard-build
make pipeline-up   # (or ensure containerlab is up)
make dashboard-run

# Open http://localhost:8888
# Verify: Dashboard loads, connects to WebSocket (live indicator green)
# Verify: All sections show real data from TimescaleDB
# Verify: Selecting experiment in Section 2 also updates Section 6

# Run a new scenario to test real-time monitor:
./run_scenarios.sh
# Pipeline Monitor should show stages activating in sequence
# Activity feed should show new predictions appearing live
```

---

## ADR Candidates

These decisions made during planning should be documented as ADRs after implementation:

1. **Dashboard uses FastAPI backend** — rationale: consistent language (Python), async WebSocket, serves both API and static files from one container
2. **DB polling instead of Kafka subscription for pipeline monitor** — rationale: simpler, no new Kafka consumer group, sufficient 2s granularity for lab use
3. **React/Vite/Recharts frontend** — rationale: lightweight, no complex state management needed, Recharts maps well to this use case
4. **Multi-stage Docker build** — rationale: separates Node build environment from Python runtime, keeps image small
5. **Relative URL approach** — rationale: FastAPI serves both static files and API on same port, so no CORS needed in production

---

## Related Documentation

- `docs/CURRENT-STATE.md` — full project state
- `docs/BLUEPRINT.md` — `dashboard/app/` in repository structure (Section 4)
- `docs/ALL-ADRS.md` — ADR-0005 (Postgres), ADR-WP6-01 (Grafana provisioning as code)
- `clab/configs/udr-db/initdb/003_gcn_schema.sql` — exact `gcn_predictions` schema
- `clab/configs/udr-db/initdb/001-init.sql` — exact `metrics` schema
- `security/detector/windowizer/config.yaml` — 13 feature keys and their names
- `twin/registry/gcn/v2.0.0/config.yaml` — model config structure
- `twin/registry/gcn/v1.0.0/test_results.json` — test_results.json field names
- `docker-compose.pipeline.yml` — existing services to extend
- `Makefile` — existing targets to extend
- `run_scenarios.sh` — experiment_id naming convention (YYYYMMDD-HHMM-seqN-label)
