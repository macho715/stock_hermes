# System Architecture

## Purpose

stock-pred-v5 is a **dual-market (US + KRX) client-side ML stock dashboard** with a REC (Recommendation) tab that displays stock-candidate screening results from stock_rtx4060_unified. All ML inference runs in-browser; no server-side prediction.

## Runtime Components

| Component | File | Role |
|-----------|------|------|
| Main Dashboard | src/StockPredV5.jsx | State, tab bar, sidebar, REC integration |
| REC Panel | src/components/RecommendationPanel.jsx | FILE/API fetch, filter tabs, sort |
| REC Card | src/components/RecommendationCard.jsx | Entry/stop/TP2/RR rendering |
| Verdict Badge | src/components/RiskGateBadge.jsx | Color-coded verdict label |
| Build Config | vite.config.js | Vite port, /api proxy |
| Dashboard Data | public/dashboard_snapshot.json | Static smoke-test snapshot |

## Component Topology

```mermaid
flowchart TD
    subgraph Dashboard["stock-pred-v5"]
        Main[StockPredV5.jsx] --> Tabs[Tab Bar: SIGNAL/MODELS/BACKTEST/REC]
        Main --> Sidebar[Right Sidebar]
        Tabs --> REC["REC tab"]
        Sidebar --> REC
        REC --> RP[RecommendationPanel]
        RP --> RC[RecommendationCard]
        RC --> RGB[RiskGateBadge]
    end
    subgraph DataSource["stock_rtx4060_unified"]
        API[Flask :5151] --> SNAP[dashboard_snapshot.json]
    end
    RP -.->|"API mode"| API
    RP -.->|"FILE mode"| SNAP
```

## Request Flow (REC tab API mode)

```mermaid
sequenceDiagram
    participant U as User
    participant REC as REC tab
    participant Vite as Vite :5173
    participant Pxy as /api proxy
    participant Flask as Flask :5151
    participant RE as RecommendationEngine

    U->>REC: click REC tab
    REC->>Vite: fetch /api/recommend?track=S&top=5
    Vite->>Pxy: /api/recommend
    Pxy->>Flask: GET /api/recommend
    Flask->>RE: engine.run()
    RE-->>Flask: dashboard_snapshot.v1
    Flask-->>Pxy: JSON
    Pxy-->>Vite: JSON
    Vite-->>REC: JSON
    REC-->>U: rendered cards
```

## Module Dependency Map

```mermaid
graph TD
    StockPredV5.jsx --> RecommendationPanel
    RecommendationPanel --> RecommendationCard
    RecommendationCard --> RiskGateBadge
    vite.config.js --> Proxy[/api → 127.0.0.1:5151]
```

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Framework | React | 18.3 | UI components |
| Build | Vite | 5.4 | Dev server + HMR |
| Charts | recharts | 2.12 | Signal/MODELS/BACKTEST |
| API | Flask | 3+ | REC recommendation API |
| API | flask-cors | 4+ | CORS for localhost:5173 |
| Fonts | JetBrains Mono | CDN | Monospace aesthetic |

## Cross-Project Interface

| Upstream | Interface | Purpose |
|----------|-----------|---------|
| stock_rtx4060_unified | Flask API :5151 or dashboard_snapshot.json | Stock-candidate screening results |
| Vite proxy | /api → 127.0.0.1:5151 | Routes REC tab fetch to Flask |
