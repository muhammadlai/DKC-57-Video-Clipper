"""Approval endpoints — the human-in-the-loop control plane."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from aitzaz_api.core.deps import CurrentUser, DbSession, get_client_ip
from aitzaz_api.schemas.approval import ApprovalCreate, ApprovalDecision, ApprovalResponse
from aitzaz_api.schemas.common import Paginated
from aitzaz_api.services import approval_service

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("", response_model=ApprovalResponse, status_code=201)
def create_approval(
    payload: ApprovalCreate,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> ApprovalResponse:
    approval = approval_service.create_request(
        db,
        user=user,
        action_type=payload.action_type,
        description=payload.description,
        payload=payload.payload,
        task_id=str(payload.task_id) if payload.task_id else None,
        ip=ip,
    )
    return ApprovalResponse.model_validate(approval)


@router.get("", response_model=Paginated[ApprovalResponse])
def list_approvals(
    db: DbSession,
    user: CurrentUser,
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Paginated[ApprovalResponse]:
    approvals, total = approval_service.list_approvals(
        db, user=user, status=status, limit=limit, offset=offset
    )
    return Paginated(
        items=[ApprovalResponse.model_validate(a) for a in approvals],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval(approval_id: str, db: DbSession, user: CurrentUser) -> ApprovalResponse:
    return ApprovalResponse.model_validate(
        approval_service.get_approval(db, user=user, approval_id=approval_id)
    )


@router.post("/{approval_id}/decision", response_model=ApprovalResponse)
def decide(
    approval_id: str,
    payload: ApprovalDecision,
    db: DbSession,
    user: CurrentUser,
    ip: str | None = Depends(get_client_ip),
) -> ApprovalResponse:
    approval = approval_service.decide(
        db,
        user=user,
        approval_id=approval_id,
        decision=payload.decision,
        note=payload.note,
        ip=ip,
    )
    return ApprovalResponse.model_validate(approval)
