# summary_lambda.py
"""
Daily standup summary Lambda:
- Computes *yesterday* in a chosen timezone (default America/Los_Angeles)
- Scans DynamoDB standup_logs for items with ts between [start_utc, end_utc)
- Groups by user and posts a summary to a Slack channel via chat.postMessage

Env vars required:
  SLACK_BOT_TOKEN      (xoxb-...)
  SUMMARY_CHANNEL_ID   (e.g., C0123456789)
  TABLE_NAME           (e.g., standup_logs)
  TIMEZONE             (optional; default 'America/Los_Angeles')
"""

from __future__ import annotations
import os, json, requests, boto3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo  # stdlib in Python 3.9+

SLACK_BOT_TOKEN   = os.environ["SLACK_BOT_TOKEN"]
TABLE_NAME        = os.environ["TABLE_NAME"]
SUMMARY_CHANNEL   = os.environ["SUMMARY_CHANNEL_ID"]
TZ_NAME           = os.getenv("TIMEZONE", "America/Los_Angeles")

ddb = boto3.resource("dynamodb")
table = ddb.Table(TABLE_NAME)

def _day_range_utc(target_tz: str) -> tuple[str, str, str]:
    """Returns (label, start_utc_iso, end_utc_iso) for *yesterday* in target_tz."""
    tz = ZoneInfo(target_tz)
    now_local = datetime.now(tz)
    y_local = (now_local - timedelta(days=1)).date()
    start_local = datetime(y_local.year, y_local.month, y_local.day, 0, 0, 0, tzinfo=tz)
    end_local   = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    end_utc   = end_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Friendly label like "Tuesday, Aug 12"
    label = y_local.strftime("%A, %b %-d") if os.name != "nt" else y_local.strftime("%A, %b %#d")
    return label, start_utc, end_utc

def _fetch_items_between(start_iso: str, end_iso: str) -> list[dict]:
    """
    SCAN + FilterExpression on ts (fine for small volumes).
    For scale, add a GSI keyed by date and switch to Query.
    """
    from boto3.dynamodb.conditions import Attr
    items: list[dict] = []
    fe = Attr("ts").gte(start_iso) & Attr("ts").lt(end_iso)
    params = {
        "FilterExpression": fe,
        "ProjectionExpression": "user_id, ts, message, user_name",
    }
    resp = table.scan(**params)
    items += resp.get("Items", [])
    while "LastEvaluatedKey" in resp:
        params["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
        resp = table.scan(**params)
        items += resp.get("Items", [])
    return items

def _format_blocks(day_label: str, items: list[dict]) -> list[dict]:
    if not items:
        return [{"type": "section", "text": {"type": "mrkdwn",
                 "text": f"*Standups for {day_label}*\n_No submissions yesterday._"}}]
    from collections import defaultdict
    by_user = defaultdict(list)
    for it in items:
        by_user[(it.get("user_id"), it.get("user_name"))].append(it)
    for k in by_user:
        by_user[k].sort(key=lambda x: x["ts"])  # oldest→newest
    blocks = [{"type": "section", "text": {"type": "mrkdwn",
               "text": f"*Standups for {day_label}*"}}]
    blocks.append({"type": "divider"})
    for (uid, uname), rows in sorted(by_user.items(), key=lambda kv: (kv[0][1] or "", kv[0][0])):
        display = f"<@{uid}>" if uid else (uname or "Unknown user")
        joined = "\n".join(f"• {r['message']}" for r in rows)
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"*{display}*\n{joined}"}})
    return blocks

def _post_blocks(blocks: list[dict]) -> dict:
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}",
               "Content-Type": "application/json"}
    payload = {"channel": SUMMARY_CHANNEL, "blocks": blocks,
               "text": "Daily standup summary"}
    resp = requests.post(url, headers=headers, json=payload, timeout=5)
    j = resp.json()
    print("chat.postMessage:", resp.status_code, j)
    return j

def handler(event, context):
    label, start_utc, end_utc = _day_range_utc(TZ_NAME)
    print("Summary window UTC:", start_utc, "→", end_utc)
    items = _fetch_items_between(start_utc, end_utc)
    print(f"Found {len(items)} items for {label}")
    blocks = _format_blocks(label, items)
    res = _post_blocks(blocks)
    ok = res.get("ok", False)
    return {"statusCode": 200 if ok else 500,
            "body": json.dumps({"ok": ok, "count": len(items)})}
