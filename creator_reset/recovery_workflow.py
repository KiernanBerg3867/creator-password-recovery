from __future__ import annotations

from dataclasses import dataclass

from .infrai_client import InfraiClient


@dataclass(frozen=True)
class RecoveryDecision:
    accepted: bool
    asset_delivery: str
    subscriber_updates: str
    content_processing: str


class CreatorRecoveryWorkflow:
    def __init__(self, infrai: InfraiClient) -> None:
        self._infrai = infrai

    def request_reset(self, email: str, captcha_token: str, ip: str | None) -> RecoveryDecision:
        self._infrai.verify_captcha(captcha_token, ip)
        self._infrai.request_password_reset(email)
        return RecoveryDecision(
            accepted=True,
            asset_delivery="continues",
            subscriber_updates="continues",
            content_processing="continues",
        )

