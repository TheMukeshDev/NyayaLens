"""Minimal probe endpoint that exercises the API wiring end to end.

Exists to give clients (and tests) a versioned endpoint that performs
Pydantic request validation and returns the standard success envelope.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.common import SuccessResponse

router = APIRouter(tags=["ping"])


class PingRequest(BaseModel):
    message: str = Field(min_length=1, max_length=280)


class PingData(BaseModel):
    reply: str
    received: str


@router.post("/ping", response_model=SuccessResponse[PingData])
def ping(payload: PingRequest) -> SuccessResponse[PingData]:
    return SuccessResponse[PingData](data=PingData(reply=payload.message, received=payload.message))
