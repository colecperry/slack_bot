# lambda_function.py
"""
AWS Lambda HTTP handler (for API Gateway "HTTP API" or "REST API").

Responsibilities here (not in core_slack):
1) Obtain the exact raw body as Slack sent it (decode if base64).
2) Verify Slack signing secret against that raw body.
3) Parse form-encoded (slash command) or extract the 'payload' JSON string (interactive).
4) Route to the correct core handler based on path or content.
5) Return the {statusCode, headers, body} structure expected by API Gateway.

Environment variables required in Lambda:
- SLACK_SIGNING_SECRET : used for request verification
- SLACK_BOT_TOKEN      : used by core_slack.open_modal() if you open a modal
"""

import os
import hmac
import hashlib
import base64
import time
import json
import urllib.parse

from core_slack import handle_standup, handle_interactive

SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]

def _hdr(headers: dict, name: str) -> str:
    """
    API Gateway may pass headers with different cases (X-Header vs x-header).
    This helper normalizes access.
    """
    return headers.get(name) or headers.get(name.lower()) or ""

def _verify_slack_signature(headers: dict, raw_body: str) -> bool:
    """
    Slack signing guide:
      base_string = "v0:{timestamp}:{raw_body}"
      my_sig = "v0=" + HMAC_SHA256(signing_secret, base_string)
      Compare my_sig to header X-Slack-Signature.
    Reject if the timestamp is older than 5 minutes to prevent replay attacks.
    """
    timestamp = _hdr(headers, "X-Slack-Request-Timestamp")
    sig_from_slack = _hdr(headers, "X-Slack-Signature")

    if not timestamp or not sig_from_slack:
        return False

    # Reject stale requests (> 5 minutes)
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False

    base_string = f"v0:{timestamp}:{raw_body}".encode("utf-8")
    expected_sig = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode("utf-8"),
        base_string,
        hashlib.sha256
    ).hexdigest()

    # Constant-time compare to prevent timing attacks
    try:
        return hmac.compare_digest(expected_sig, sig_from_slack)
    except Exception:
        return False

def _response(status: int, headers: dict | None = None, body: str = "") -> dict:
    """
    Format the Lambda proxy integration response.
    - 'body' must be a string (JSON-encoded if returning JSON).
    - You can set headers like Content-Type.
    """
    return {"statusCode": status, "headers": headers or {}, "body": body}

def handler(event, context):
    """
    Main Lambda entrypoint. 'event' is the HTTP request from API Gateway.
    Key fields we use:
      event["body"]             : raw request body (string or base64)
      event["isBase64Encoded"]  : whether 'body' needs base64 decoding
      event["headers"]          : dict of HTTP headers
      event["rawPath"] or ["path"]: the URL path (e.g., "/standup", "/interactive")
    """
    # 1) Get the exact raw body; decode if base64 to match Slack's signature.
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    # 2) Verify Slack signature BEFORE parsing (must use the exact raw body).
    headers = event.get("headers", {}) or {}
    if not _verify_slack_signature(headers, body):
        # Returning 401 helps you spot signature issues in CloudWatch logs.
        return _response(401, {}, "bad signature")

    # 3) Parse the form-encoded body into a simple dict[str, str].
    #    Slack slash commands are 'application/x-www-form-urlencoded'.
    parsed = urllib.parse.parse_qs(body)  # values like {"text": ["hello"]}
    form = {k: (v[0] if isinstance(v, list) and v else "") for k, v in parsed.items()}

    # 4) Route by path if provided; otherwise route by presence of fields.
    raw_path = event.get("rawPath") or event.get("path") or "/"

    if raw_path.endswith("/standup"):
        status, hdrs, resp_body = handle_standup(form)
        return _response(status, hdrs, resp_body)

    if raw_path.endswith("/interactive"):
        status, hdrs, resp_body = handle_interactive(form)
        return _response(status, hdrs, resp_body)

    # Fallback routing by content (useful if you mapped root path to this Lambda)
    if "command" in form:
        status, hdrs, resp_body = handle_standup(form)
        return _response(status, hdrs, resp_body)

    if "payload" in form:
        status, hdrs, resp_body = handle_interactive(form)
        return _response(status, hdrs, resp_body)

    # If we get here, it wasn't one of our endpoints.
    return _response(404, {}, "not found")
