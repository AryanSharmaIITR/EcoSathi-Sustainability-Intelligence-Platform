<div align="center">

# 🌱 EcoSathi — Sustainability Intelligence Platform

**Turn scattered institutional utility & waste data into a centralized, predictive sustainability engine.**

EcoSathi transforms fragmented institutional utility and waste data into a centralized, predictive analytics engine. Designed for scalable multi-tenancy, it automates ESG reporting while driving measurable reductions in resource waste and recycling contamination.

</div>

---

## ✨ Why EcoSathi?

Institutions — campuses, housing societies, municipal wards — make constant sustainability decisions: *what do I do with this waste item? Is this month's water or energy usage normal?* Today those decisions are made with **no data at the point of action**. The information exists (utility meters, manual logs, item-level waste data), but it's inaccessible the moment someone needs it.

EcoSathi makes that scattered information **queryable and predictive**, giving institutions:

- 📉 **Measurable reductions** in recycling contamination and utility waste
- 📋 A **defensible sustainability-reporting artifact** for compliance & ESG (increasingly a procurement requirement)
- 🔀 A **scalable, multi-tenant product** — a new institution is a new tenant, not new engineering

> This is not a chatbot demo. The bar is: **does EcoSathi change what a facilities manager does on a Tuesday?** That means predictions and recommendations, not just answers.

---

## 🧩 Core Features

The platform is built on three functional pillars:

### 1. 🗑️ Waste Classification
Image-in, disposal-instruction-out. Scan a waste item and get a disposal classification mapped to your tenant's local waste categories — **recyclable, compostable, landfill, hazardous, or e-waste** — powered by a hosted vision/LLM API.

### 2. 📈 Consumption Forecasting
Predict water and energy usage per tenant/building, **flag anomalies against historical baselines**, and surface week-over-week trends so abnormal usage is caught early.

### 3. ⚡ Action Orchestration
An **agent layer** that combines classification and forecasting output into a **ranked, tenant-specific action plan** — exposed via API and a live dashboard. Every recommendation includes an estimated monthly impact.

Every AI output is **traceable to its source** (an input image, a data point, a model version) and **audit-logged** — no black-box answers ship to production.

---

## 📸 Screenshots

| Dashboard | Waste Scan |
| :---: | :---: |
| ![Overview](Project%20Details/overview.png) | ![Waste Scan](Project%20Details/waste_scan.png) |

| Usage Analytics | Actions |
| :---: | :---: |
| ![Usage](Project%20Details/usage.png) | ![Actions](Project%20Details/actions.png) |

| Reports | Logo |
| :---: | :---: |
| ![Reports](Project%20Details/Reports.png) | ![Logo](Project%20Details/logo.png) |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** (backend)
- **Node.js 18+** & **npm** (frontend)
- **PostgreSQL** (data layer)
- A free **Groq API key** → [console.groq.com/keys](https://console.groq.com/keys)

> **v1 uses only free-tier hosted APIs** — no fine-tuning, no custom training pipeline. Groq's key is the **only external AI API key** needed.

### 1. Backend (FastAPI)

```bash
cd Backend

cp .env.example .env
# then set GROQ_API_KEY in .env

pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Run migrations (optional, after DB is up):

```bash
alembic upgrade head
```

The API is served at `http://localhost:8000`, with interactive docs at [`/docs`](http://localhost:8000/docs).

### 2. Frontend (React + Vite)

```bash
cd Ecosathi

cp .env.example .env   # points VITE_API_BASE_URL at the backend

npm install
npm run dev
```

Open the dashboard at `http://localhost:5173`.

---

## 🧭 Quick API Tour

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/health` | `GET` | Liveness check (no DB required) |
| `/api/v1/tenants` | `POST` | Create a tenant (`{ "name": "...", "slug": "..." }`) |
| `/api/v1/tenants/me` | `GET` | Tenant scoping (uses `X-Tenant-Id` header) |
| `/api/v1/classify` | `POST` | Waste classification via multipart `file=@image.png` |
| `/api/v1/recommend` | `POST` | LangGraph orchestration → ranked action plan |

Tenant data is **isolated** with row-level scoping — requests pass an `X-Tenant-Id` header so one tenant's data never leaks into another's predictions or dashboards.

---

## 🏗️ Architecture

```
┌────────────────────────────┐
│   React (Vite) Dashboard   │  React + TailwindCSS + Recharts
│   TS + React Query         │
└─────────────┬──────────────┘
              │  REST (typed Pydantic schemas)
┌─────────────▼──────────────┐
│       FastAPI Gateway      │  /api/v1, async endpoints
│      (multi-tenant)        │
└──────┬──────────┬──────────┘
       │          │
┌──────▼───┐ ┌────▼───────────┐
│  Classify │ │  Orchestration  │  LangGraph StateGraph
│ (Groq)   │ │  Agent          │  deterministic, tool-calling
└──────────┘ └────┬────────────┘
                  │
        ┌─────────▼─────────┐
        │  Forecasting      │  scikit-learn regression
        │  (per tenant)     │  (retrain scheduled)
        └─────────┬─────────┘
                  │
┌─────────────────▼─────────────────┐
│      PostgreSQL (tenant-scoped)    │  usage, audit-log, reports
└───────────────────────────────────┘
```

### Tech Stack

| Layer | Tech |
| :--- | :--- |
| **Frontend** | React 19, Vite, TypeScript, TailwindCSS 4, Recharts, TanStack Query |
| **Backend** | FastAPI, Pydantic v2, SQLAlchemy (async), Alembic |
| **AI/ML** | Groq vision API (classification), scikit-learn (forecasting), LangGraph (agent orchestration) |
| **Data** | PostgreSQL with row-level tenant scoping |
| **Tooling** | Ruff, pytest, oxlint, uv/venv |

---

## 🧠 How the AI Layer Works

Everything AI-related lives under `Backend/app/ai/`, separate from plain backend services:

- **[Waste classification](Backend/app/ai/groq_client.py)** — a thin wrapper around Groq's vision-capable chat completions, so the provider can be swapped without touching callers. The model ID is configurable via `GROQ_VISION_MODEL`.
- **[Agent orchestration](Backend/app/ai/agent/)** — a LangGraph `StateGraph` with two tools: `classify_waste` (real) and `get_usage_forecast` (honestly reports availability). The orchestration model decides which tool(s) to invoke, then synthesizes a **ranked action plan**. The graph is **fixed and every tool call is traced and audit-logged** — deterministic, not a free-form agent loop.
- **[Audit logging](Backend/app/services/audit.py)** — every AI response (tenant, endpoint, model, confidence, input reference, raw output) is recorded before it's returned, satisfying the compliance requirement.
- **RAG knowledge base** — CPCB regulations (hazardous waste, recycling, e-waste, plastic waste, solid waste) grounded in the retrieval pipeline.

---

## 📁 Project Structure

```
├── Backend/               # FastAPI REST API
│   ├── app/
│   │   ├── ai/            # AI/ML layer (classification, RAG, agent, orchestration)
│   │   ├── api/v1/        # Versioned REST routes
│   │   ├── core/          # Config & logging
│   │   ├── db/            # Session & base models
│   │   ├── models/        # SQLAlchemy models (tenant, usage, alerts, reports...)
│   │   ├── schemas/       # Pydantic request/response models
│   │   └── services/      # Audit, alert engine, telemetry
│   ├── alembic/           # DB migrations
│   └── tests/
├── Ecosathi/              # React + Vite + TypeScript frontend
│   └── src/
│       ├── components/    # UI components (overview, usage, layout)
│       ├── layouts/       # App shell & sidebar
│       ├── pages/         # Overview, Usage, Waste Scans, Actions, Reports, Alerts, Settings
│       ├── lib/           # API client, helpers
│       └── types/
└── Project Details/       # Screenshots & kickoff spec
```

**Frontend pages:** Overview, Usage, Waste Scans, Actions, Reports, Alerts, Settings — each wired to the typed API via TanStack Query.

---

## 🗺️ Roadmap

- **Phase 1 — Foundation:** Tenant data model, FastAPI skeleton, waste classification end-to-end for one pilot tenant
- **Phase 2 — Core Features:** Classification + scanner UI, forecasting + scheduled retrain, dashboard v1
- **Phase 3 — Orchestration & Hardening:** Recommendation agent chaining classification + forecasting, end-to-end audit logging, tenant isolation review
- **Phase 4 — Pilot Launch:** Onboard 1–2 pilot tenants, instrument recommendation-acceptance & forecast-accuracy

---

## 🔒 Security & Compliance

- **Tenant Isolation** is treated as a security requirement, not a data-modeling nicety — row-level scoping throughout.
- **Audit trail** of every AI output (what was shown, when, based on what input) for defensible compliance.
- **Confidence/source fields** on every AI response from day one.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.

---

<div align="center">
Made with 💚 for a more sustainable tomorrow.
</div>
