#!/usr/bin/env python3
"""
Sakima SMS Webhook Handler
Receives inbound SMS via Surge.app webhook → routes by keyword → replies via Surge API.
"""
import logging
import os
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
import httpx

from handlers.router import route_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Sakima SMS Bot", version="1.0.0")

SURGE_API_KEY = os.environ.get("SURGE_API_KEY", "")
SURGE_API_URL = "https://api.surge.app/messages"  # adjust if different


async def send_sms_reply(to: str, from_number: str, body: str) -> bool:
    """Send reply via Surge.app REST API."""
    if not SURGE_API_KEY:
        logger.warning("SURGE_API_KEY not set — reply not sent")
        return False

    payload = {
        "to": to,
        "from": from_number,
        "body": body,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            SURGE_API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {SURGE_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code >= 400:
            logger.error("Surge API error %s: %s", resp.status_code, resp.text)
            return False
        logger.info("Reply sent to %s: %s", to, body[:60])
        return True


@app.post("/webhook/sms")
async def sms_webhook(request: Request):
    """
    Surge.app inbound SMS webhook.
    Surge posts form-encoded or JSON — handles both.
    """
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)

    logger.info("Inbound SMS: %s", data)

    # Surge.app field names — adjust if their schema differs
    from_number = data.get("from") or data.get("From") or ""
    to_number   = data.get("to")   or data.get("To")   or ""
    body        = data.get("body") or data.get("Body") or ""

    if not from_number or not body:
        logger.warning("Missing from/body in payload: %s", data)
        return PlainTextResponse("ok")

    # Route the message
    reply_text = await route_message(body.strip())

    # Send reply
    await send_sms_reply(from_number, to_number, reply_text)

    return PlainTextResponse("ok")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "sakima-sms"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), reload=False)
