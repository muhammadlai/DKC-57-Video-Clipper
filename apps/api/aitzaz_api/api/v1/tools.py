"""Tool endpoints — list registered tools and execute them."""

from __future__ import annotations

from aitzaz_tools.base import ToolError
from fastapi import APIRouter, Depends

from aitzaz_api.core.deps import CurrentUser, DbSession, get_client_ip
from aitzaz_api.core.errors import AppError
from aitzaz_api.schemas.misc import ToolExecuteRequest, ToolExecuteResponse, ToolResponse
from aitzaz_api.services import tool_service

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolResponse])
def list_tools(db: DbSession, user: CurrentUser) -> list[ToolResponse]:
    return [ToolResponse.model_validate(t) for t in tool_service.list_tools(db)]


@router.get("/{slug}", response_model=ToolResponse)
def get_tool(slug: str, db: DbSession, user: CurrentUser) -> ToolResponse:
    row = tool_service.get_tool_row(db, slug)
    if row is None:
        raise AppError(f"Unknown tool: '{slug}'", code="not_found", status_code=404)
    return ToolResponse.model_validate(row)


@router.post("/{slug}/execute", response_model=ToolExecuteResponse)
def execute_tool(
    slug: str,
    payload: ToolExecuteRequest,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> ToolExecuteResponse:
    try:
        result = tool_service.execute_tool(
            db, user=user, slug=slug, input_data=payload.input, actor="user", ip=ip
        )
    except ToolError as exc:
        raise tool_service.tool_error_to_http(exc) from exc
    return ToolExecuteResponse(
        tool=slug,
        ok=result.ok,
        result=result.result,
        error=result.error,
        error_code=result.error_code,
        duration_ms=result.duration_ms,
    )
