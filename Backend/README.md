# EcoSathi Backend

FastAPI backend skeleton for the EcoSathi Sustainability Intelligence Platform. See `Project Details/EcoSathi-Kickoff-Spec.md` at the repo root for the full spec.

## Setup

```bash
cp .env.example .env
# then set GROQ_API_KEY in .env — get a free key at https://console.groq.com/keys
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Verify

- `GET /api/v1/health` — liveness check, no DB required.
- `POST /api/v1/tenants` — create a tenant (`{"name": "...", "slug": "..."}`).
- `GET /api/v1/tenants/me` (with `X-Tenant-Id: <uuid>` header) — tenant-scoping.
- `POST /api/v1/classify` (with `X-Tenant-Id` header, multipart `file=@image.png`) — waste classification via Groq's vision API; writes an audit log row per call.
- `POST /api/v1/recommend` (with `X-Tenant-Id` header, optional multipart `file=@image.png`) — LangGraph orchestration agent; ranked action plan, audit-logs each tool call plus the final decision.
- `/docs` — Swagger UI.

## AI/ML layer

v1 uses only free-tier hosted APIs — no fine-tuning, no custom training pipeline, per the spec. Everything AI-related lives under `app/ai/` (not `app/services/`), separate from plain backend services.

- **Waste classification** (`app/ai/groq_client.py`) — thin wrapper around Groq's vision-capable chat completions, so the provider can be swapped without touching callers. Model id is configurable via `GROQ_VISION_MODEL`. Category taxonomy is currently a fixed global default (`recyclable`/`compostable`/`landfill`/`hazardous`/`e-waste`); real per-tenant category mapping is deferred until a waste-category admin data model exists.
- **Consumption forecasting** — not built yet; will be local scikit-learn regression, no external API key needed.
- **Agent orchestration** (`app/ai/agent/`) — a LangGraph `StateGraph` (`graph.py`) with two tools (`tools.py`): `classify_waste` (real, wraps `groq_client.py`) and `get_usage_forecast` (stubbed — forecasting doesn't exist yet, so it honestly reports unavailable rather than fabricating a number). The orchestration model (`GROQ_ORCHESTRATION_MODEL`, tool-calling capable) decides which tool(s) to invoke, then synthesizes a ranked action plan. The graph structure is fixed and every tool call is captured in `state["trace"]` and audit-logged individually — deterministic and traceable, not a free-form agent loop.
- **Audit log** (`app/models/audit_log.py`, `app/services/audit.py`) — every AI response is recorded (tenant, endpoint, model, confidence, input reference, raw output) before being returned, per the spec's compliance requirement.

`GROQ_API_KEY` is the only external API key v1 needs.

## Status

App factory, versioned routing, tenant data model + scoping dependency, CORS for the Vite frontend, the waste classification endpoint end-to-end (one pilot tenant), the LangGraph-based recommendation/orchestration agent, and AI-output audit logging. Forecasting and a real background task queue are not implemented yet — see `app/services/tasks/stub.py` for the queue seam and `get_usage_forecast` in `app/ai/agent/tools.py` for the forecast seam.
