from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Iterator

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from .infrai_client import InfraiClient, InfraiError
from .recovery_workflow import CreatorRecoveryWorkflow


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    captcha_token: str = Field(min_length=1)


class ResetAccepted(BaseModel):
    accepted: bool
    asset_delivery: str
    subscriber_updates: str
    content_processing: str


def create_app(infrai: InfraiClient | None = None) -> FastAPI:
    client = infrai or InfraiClient()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> Iterator[None]:
        yield
        client.close()

    app = FastAPI(title="Creator recovery", lifespan=lifespan)
    workflow = CreatorRecoveryWorkflow(client)

    @app.post("/forgot-password", response_model=ResetAccepted, status_code=202)
    def forgot_password(payload: ForgotPasswordRequest, request: Request) -> ResetAccepted:
        try:
            decision = workflow.request_reset(
                email=str(payload.email),
                captcha_token=payload.captcha_token,
                ip=request.client.host if request.client else None,
            )
        except InfraiError as exc:
            status = exc.status_code if 400 <= exc.status_code < 500 else 502
            raise HTTPException(status_code=status, detail={"code": exc.code}) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail={"code": "UPSTREAM_UNAVAILABLE"}) from exc
        return ResetAccepted(**decision.__dict__)

    return app


app = create_app()

