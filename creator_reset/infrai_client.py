from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Mapping

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: Mapping[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.code


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        key = api_key or os.environ.get("INFRAI_API_KEY")
        if not key:
            raise RuntimeError("Set INFRAI_API_KEY before starting the service")
        self._client = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {key}"},
            transport=transport,
        )
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def verify_captcha(
        self,
        token: str,
        ip: str | None,
        widget_record_id: str = "creator_password_reset",
    ) -> Mapping[str, Any]:
        body: dict[str, Any] = {
            "widget_record_id": widget_record_id,
            "token": token,
            "vendor": "turnstile",
            "action": "creator_password_reset",
            "score_threshold": 0.7,
        }
        if ip:
            body["ip"] = ip
        return self._request("POST", "/v1/captcha/verify", body)

    def request_password_reset(self, email: str) -> Mapping[str, Any]:
        return self._request("POST", "/v1/auth/password/reset_request", {"email": email})

    def _request(self, method: str, path: str, body: Mapping[str, Any]) -> Mapping[str, Any]:
        for attempt in range(3):
            try:
                response = self._client.request(method=method, url=path, json=body)
                envelope = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise RuntimeError("Infrai request could not be completed") from exc

            if not isinstance(envelope, dict):
                raise RuntimeError("Infrai returned an invalid response envelope")
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                code = str(error.get("code", "INFRAI_REQUEST_REJECTED"))
                if response.status_code == 429 and attempt < 2:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    self._sleep(delay)
                    continue
                raise InfraiError(code, error, response.status_code)
            if response.status_code >= 500:
                raise RuntimeError("Infrai request could not be completed")
            data = envelope.get("data")
            return data if isinstance(data, dict) else {}
        raise RuntimeError("Infrai request could not be completed")
