"""MoE Orchestrator — main entry point for the Mixture-of-Experts pipeline.

This module is the single import point that callers (FastAPI routes, tests)
use to invoke the multi-agent system.  It wraps ``run_supervisor`` with
request validation and structured logging so the route layer stays thin.

Usage::

    from app.ai.orchestrator import run_moe_pipeline

    response: MoEResponse = await run_moe_pipeline(request)
"""

from __future__ import annotations

import logging

from app.ai.agents.central_supervisor import run_supervisor
from app.schemas.agent_io import MoERequest, MoEResponse

logger = logging.getLogger(__name__)


async def run_moe_pipeline(request: MoERequest) -> MoEResponse:
    """Execute the full Mixture-of-Experts pipeline for a single request.

    This is the canonical entry point.  All orchestration logic lives in
    ``central_supervisor.run_supervisor``; this function adds:
      - Structured log bookends (start / finish / error).
      - Re-raises exceptions so the HTTP layer can return a 502.

    Args:
        request: Validated ``MoERequest`` containing the user query,
                 tenant context, and optional telemetry / image.

    Returns:
        ``MoEResponse`` with routing metadata, expert agent outputs,
        synthesised summary, ranked actions, and full execution trace.

    Raises:
        Exception: Any exception from the supervisor or expert agents
                   is propagated unchanged so the caller can handle it.
    """
    logger.info(
        "MoE pipeline start | tenant=%s | query=%r",
        request.tenant_id,
        request.query[:120],
    )
    try:
        response = await run_supervisor(request)
        logger.info(
            "MoE pipeline complete | tenant=%s | agents_used=[waste=%s, resource=%s] | actions=%d | trace_steps=%d",
            request.tenant_id,
            response.waste_compliance is not None,
            response.resource_planning is not None,
            len(response.actions),
            len(response.trace),
        )
        return response
    except Exception:
        logger.exception("MoE pipeline failed | tenant=%s", request.tenant_id)
        raise
