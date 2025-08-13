# core_slack.py
"""
Shared Slack logic (no Flask/Lambda imports here).
- Opens a modal when /standup is used with no text.
- Saves standups to DynamoDB (via db.py) on inline text and on modal submit.
- Responds with ephemeral messages or modal updates.

Environment variables expected:
- SLACK_BOT_TOKEN  : used to call Slack Web API (views.open, chat.postMessage if added later)
"""

from __future__ import annotations

import os
import json
from datetime import datetime
import requests

from db import save_standup, get_latest_n  # DynamoDB helpers

# Bot token for Slack Web API calls
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")


# ---------- Slack Web API helpers ----------

def open_modal(trigger_id: str, modal_view: dict) -> dict:
    """
    Calls Slack's views.open to display a modal.
    Uses a short timeout so the slash command can still return 200 quickly
    (prevents Slack's "dispatch_failed" if the network is slow).
    """
    url = "https://slack.com/api/views.open"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {"trigger_id": trigger_id, "view": modal_view}
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=1.5)
        j = resp.json()
        print("views.open status:", resp.status_code, "ok:", j.get("ok"), "error:", j.get("error"))
        return j
    except requests.exceptions.Timeout:
        # If this times out, we still return 200 to Slack with a fallback message.
        print("views.open TIMEOUT")
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        print("views.open exception:", repr(e))
        return {"ok": False, "error": "exception"}


# ---------- Core handlers (reused by Flask and Lambda) ----------

def handle_standup(form: dict) -> tuple[int, dict, str]:
    """
    Slash command handler for /standup.
    - If user supplies text inline, save immediately and reply ephemerally.
    - If no text, attempt to open a modal (views.open), then return 200 quickly.
    Returns: (status_code, headers_dict, body_string)
    """
    user_id    = form.get("user_id", "")
    user_name  = form.get("user_name", "")
    trigger_id = form.get("trigger_id", "")
    text       = (form.get("text") or "").strip()

    # No inline text → open modal
    if not text:
        modal_view = {
            "type": "modal",
            "callback_id": "standup_modal",
            "title": {"type": "plain_text", "text": "Daily Standup"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "standup_input",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "standup_text",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "What did you work on today?"
                        }
                    },
                    "label": {"type": "plain_text", "text": "Your standup update"}
                }
            ]
        }

        result = open_modal(trigger_id, modal_view)

        if result.get("ok"):
            # Important: return 200 immediately with empty body — Slack is satisfied.
            return 200, {}, ""
        else:
            # Fallback: still return 200 so Slack does not show "dispatch_failed"
            body = {
                "response_type": "ephemeral",
                "text": "Couldn’t open the modal just now. Try again, or type `/standup your update`."
            }
            return 200, {"Content-Type": "application/json"}, json.dumps(body)

    # Inline text path → save to DynamoDB
    ts_saved = save_standup(user_id=user_id, message=text, user_name=user_name)

    # Nice UX: show previous entry if it exists
    latest_two = get_latest_n(user_id, 2)  # newest-first; [0]=this save (most likely), [1]=previous
    prev = latest_two[1] if len(latest_two) == 2 else None

    ack = f":white_check_mark: Saved your update at *{ts_saved}* (UTC)\n> {text}"
    if prev:
        ack += f"\n\n*Previous:* _{prev['ts']}_\n> {prev['message']}"

    return 200, {"Content-Type": "application/json"}, json.dumps({
        "response_type": "ephemeral",
        "text": ack
    })


def handle_interactive(form: dict) -> tuple[int, dict, str]:
    """
    Handles interactive events (e.g., modal submissions).
    Slack posts a form field named 'payload' that is a JSON string.
    On view_submission:
      - Save to DynamoDB.
      - Replace the modal with a success screen showing current + previous entry.
    """
    payload_raw = form.get("payload", "")
    if not payload_raw:
        return 200, {}, ""

    payload = json.loads(payload_raw)

    if payload.get("type") == "view_submission":
        user_id = payload["user"]["id"]
        user_name = payload["user"]["name"]
        values = payload["view"]["state"]["values"]
        standup_text = values["standup_input"]["standup_text"]["value"]

        # Save submission to DynamoDB
        ts_saved = save_standup(user_id=user_id, message=standup_text, user_name=user_name)

        # Fetch previous item (if any)
        latest_two = get_latest_n(user_id, 2)
        prev = latest_two[1] if len(latest_two) == 2 else None

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":white_check_mark: Saved at *{ts_saved}* (UTC)\n\n> {standup_text}"
                }
            }
        ]
        if prev:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Previous:* _{prev['ts']}_\n> {prev['message']}"
                }
            })

        # Respond by updating the modal with a success view
        return 200, {"Content-Type": "application/json"}, json.dumps({
            "response_action": "update",
            "view": {
                "type": "modal",
                "title": {"type": "plain_text", "text": "Standup Submitted!"},
                "close": {"type": "plain_text", "text": "Close"},
                "blocks": blocks
            }
        })

    # For other interactive payload types, simply ACK
    return 200, {}, ""
