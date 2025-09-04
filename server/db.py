# db.py
"""
Creates DynamoDB table connection and helpers for saving and fetching standup entries.

Table schema:
  PK: user_id (S)
  SK: ts (S, ISO e.g., 2025-08-12T22:46:13Z)
"""

import os
import boto3
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key

_TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

def _now_iso() -> str:
    # Always store in UTC for consistency
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def save_standup(user_id: str, message: str, user_name: str | None = None) -> str:
    """Write a standup message row with UTC timestamp as primary key"""
    ts = _now_iso()
    item = {"user_id": user_id, "ts": ts, "message": message}
    if user_name:
        item["user_name"] = user_name
    _TABLE.put_item(Item=item)
    return ts

def get_latest_n(user_id: str, n: int = 1) -> list[dict]:
    """Queries and return the latest N standups for a user sorted by timestamp(0..N items)."""
    resp = _TABLE.query(
        KeyConditionExpression=Key("user_id").eq(user_id),
        ScanIndexForward=False,  # newest first
        Limit=n,
    )
    return resp.get("Items", [])
