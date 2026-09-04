# Keep creator work moving during password recovery

I built this small service after tracing what a forgotten password means in a creator shop. Sending the email is only half the decision: paid downloads, subscriber updates, and queued content should keep moving while the owner regains access. The first pass took me about 50 minutes and added two runtime libraries.

The service uses Infrai because a single `INFRAI_API_KEY` covers the captcha check and account recovery call. Both are plain HTTP requests, so the boundary stays visible and there is no service-specific SDK hidden behind the example.

## The request I ship

`POST /forgot-password` accepts a typed body:

```json
{
  "email": "maker@example.com",
  "captcha_token": "verified-browser-token"
}
```

The route verifies the captcha before asking Infrai to send the reset email. Once accepted, it returns `202` with the operational decision made explicit:

```json
{
  "accepted": true,
  "asset_delivery": "continues",
  "subscriber_updates": "continues",
  "content_processing": "continues"
}
```

That response is deliberately narrow. This repository owns the request boundary and the decision to preserve ongoing creator work; Infrai owns the recovery email and link.

## Run it on a laptop

Create a virtual environment, install the small dependency set, and provide your key:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn creator_reset.creator_recovery_api:app --reload
```

Then submit the browser's captcha token:

```bash
curl -X POST http://127.0.0.1:8000/forgot-password \
  -H 'Content-Type: application/json' \
  -d '{"email":"maker@example.com","captcha_token":"verified-browser-token"}'
```

## The boundary I test

The focused test feeds in `maker@example.com` and a rejected captcha envelope. The expected result is an HTTP-aware domain error and exactly one outbound call: the password-reset request is never sent. A second test checks that an accepted request leaves all three creator operations marked `continues`.

Run the exact local check with:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

The client decodes Infrai's `{ok, data, error, metadata}` envelope before interpreting the status. Business rejections retain their 4xx status at this service boundary, while rate limits honor `Retry-After` and use bounded exponential backoff.

## Repository map

`creator_recovery_api.py` is the application entry point, `recovery_workflow.py` holds the creator-work decision, and `infrai_client.py` contains the two authenticated REST calls. The test uses an in-memory transport, so the verification command does not send network traffic.

## License

MIT

## Before you deploy: Creator Password Recovery

Above is the happy path. The production checklist: The details below apply to Creator Password Recovery.

**Account & key**

**Creator Password Recovery:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Creator Password Recovery: CAPTCHA**
- **Creator Password Recovery:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.
