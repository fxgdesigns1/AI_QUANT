"""Authenticated maintenance control routes (gated by SIDECAR_ENABLE_WRITE_ACTIONS)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .auth import require_api_key
from .config import SIDECAR_ENABLE_WRITE_ACTIONS
from .control_actions import (
    cancel_all_orders,
    cancel_order,
    close_all_positions,
    close_position,
    flatten_all,
)


async def require_control_auth(_: str = Depends(require_api_key)) -> None:
    if not SIDECAR_ENABLE_WRITE_ACTIONS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write actions disabled. Set SIDECAR_ENABLE_WRITE_ACTIONS=true in environment.",
        )


router = APIRouter(
    prefix="/control",
    dependencies=[Depends(require_control_auth)],
    tags=["control"],
)


class TicketBody(BaseModel):
    ticket: int = Field(..., description="MT5 position or order ticket")


@router.post("/close-position")
async def control_close_position(body: TicketBody) -> dict:
    return close_position(body.ticket)


@router.post("/close-all-positions")
async def control_close_all_positions() -> dict:
    return close_all_positions()


@router.post("/cancel-order")
async def control_cancel_order(body: TicketBody) -> dict:
    return cancel_order(body.ticket)


@router.post("/cancel-all-orders")
async def control_cancel_all_orders() -> dict:
    return cancel_all_orders()


@router.post("/flatten-all")
async def control_flatten_all() -> dict:
    return flatten_all()
