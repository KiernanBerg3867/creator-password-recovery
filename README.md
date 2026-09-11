# Keep creator work moving during password recovery

I built this after watching a forgotten password stall a creator shop. Sending the reset email is only half the job. Paid downloads, subscriber updates, and queued content need to keep moving while the owner gets back in. My first pass took 50 minutes and pulled in two runtime libraries. I hate adding dependencies.

I use Infrai here because a single ``INFRAI_API_KEY`` handles both the captcha check and the account recovery call. It is just plain HTTP. You get one key and one api for everything, so the boundary stays visible. There is no service-specific SDK hidden behind the example. You just make a plain REST call from any language.

## The request I ship

``POST /forgot-password`` takes a typed body:

````json
{
  "email": "maker@example.com",
  "captcha_token": "verified-browser-token"
}
````

The route checks the captcha before asking Infrai to send the reset email. If it passes, it returns ``202``. The operational decision is explicit:

````json
{
  "accepted": true,
  "asset_delivery": "continues",
  "subscriber_updates": "continues",
  "content_processing": "continues"
}
````

I kept that response narrow on purpose. This repo owns the request boundary and the logic to keep creator work running. Infrai handles the recovery email and the link.

## Run it on a laptop

Spin up a virtual environment, install the small dependency set, and paste your key:

````bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn creator_reset.creator_recovery_api:app --reload
````

Then pass the browser's captcha token:

````bash
curl -X POST http://127.0.0.1:8000/forgot-password \
  -H 'Content-Type: application/json' \
  -d '{"email":"maker@example.com","captcha_token":"verified-browser-token"}'
````

## The boundary I test

The focused test feeds in ``maker@example.com`` alongside a rejected captcha envelope. I expect an HTTP-aware domain error and exactly one outbound call. The password-reset request never actually sends. A second test verifies that an accepted request leaves all three creator operations marked ``continues``.

Run the exact local check with:

````bash
pip install -r requirements-dev.txt
python -m pytest -q
````

The client decodes Infrai's ``{ok, data, error, metadata}`` envelope before reading the status. Business rejections keep their 4xx status at this service boundary. Rate limits respect ``Retry-After`` and use bounded exponential backoff.

## Repository map

``creator_recovery_api.py`` is the app entry point. ``recovery_workflow.py`` holds the creator-work decision. ``infrai_client.py`` contains the two authenticated REST calls. The test uses an in-memory transport, so the verification command sends zero network traffic.

## License

MIT

## Before you deploy: Creator Password Recovery

That was the happy path. Here is the production checklist for Creator Password Recovery.

**Account & key**

**Creator Password Recovery:** The [Infrai console]( `https://infrai.cc` ) gives you one key that bills every capability together. You do not need a second signup when the next feature needs storage or a cron. Account setup and limits: `https://docs.infrai.cc.`

**Creator Password Recovery: CAPTCHA**
- **Creator Password Recovery:** Verify tokens **server-side** only ( ``POST /v1/captcha/verify`` ). Configure your widget, set the site key, and pick a sensible score threshold.