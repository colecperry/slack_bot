# app.py
"""
Flask wrapper for local development.
- Presents HTTP routes for Slack to hit (via ngrok).
- Converts Flask request objects -> simple dicts.
- Delegates to core_slack.* handlers.
"""

from flask import Flask, request, make_response
from dotenv import load_dotenv
from core_slack import handle_standup, handle_interactive

# Load .env for local development (SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET if you add verification here)
load_dotenv()

app = Flask(__name__)

@app.route("/standup", methods=["POST"])
def standup():
    """
    Slash command endpoint for local dev.
    Flask gives 'request.form' as a MultiDict with lists.
    core_* expects a plain dict[str, str], so we rely on Flask's get() behavior,
    then pass request.form directly (it supports .get returning single values).
    """
    status, headers, body = handle_standup(request.form)
    resp = make_response(body, status)
    for k, v in headers.items():
        resp.headers[k] = v
    return resp

@app.route("/interactive", methods=["POST"])
def interactive():
    """
    Slack sends interactive events (like modal submissions) here.
    """
    status, headers, body = handle_interactive(request.form)
    resp = make_response(body, status)
    for k, v in headers.items():
        resp.headers[k] = v
    return resp

if __name__ == "__main__":
    # Run locally, then expose with ngrok so Slack can reach it.
    app.run(port=3000, debug=True)
