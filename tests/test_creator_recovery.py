import json

import httpx
import pytest

from creator_reset.infrai_client import InfraiClient, InfraiError
from creator_reset.recovery_workflow import CreatorRecoveryWorkflow


def test_rejected_captcha_does_not_send_reset_email() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(
            422,
            json={
                "ok": False,
                "data": None,
                "error": {"code": "CAPTCHA_SCORE_TOO_LOW"},
                "metadata": {},
            },
        )

    client = InfraiClient(api_key="test-key", transport=httpx.MockTransport(handler))
    workflow = CreatorRecoveryWorkflow(client)

    with pytest.raises(InfraiError) as rejected:
        workflow.request_reset("maker@example.com", "low-score-token", "203.0.113.8")

    assert rejected.value.status_code == 422
    assert calls == ["/v1/captcha/verify"]
    client.close()


def test_accepted_request_preserves_creator_work() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"ok": True, "data": {}, "error": None, "metadata": {}})

    client = InfraiClient(api_key="test-key", transport=httpx.MockTransport(handler))
    decision = CreatorRecoveryWorkflow(client).request_reset(
        "maker@example.com", "verified-token", "203.0.113.8"
    )

    assert decision.accepted is True
    assert decision.asset_delivery == "continues"
    assert decision.subscriber_updates == "continues"
    assert decision.content_processing == "continues"
    assert calls[1] == ("/v1/auth/password/reset_request", {"email": "maker@example.com"})
    client.close()

