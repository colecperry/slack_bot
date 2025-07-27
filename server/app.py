from flask import Flask, request, make_response, jsonify
from datetime import datetime
import json
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
user_updates = {}

# Get Slack Bot Token from environment variable
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')

# Check if token is loaded
if not SLACK_BOT_TOKEN:
    print("⚠️ SLACK_BOT_TOKEN not found in environment variables!")
    print("Make sure you have a .env file with SLACK_BOT_TOKEN=your-token")
else:
    print("✅ Slack bot token loaded successfully")

def open_modal(trigger_id, modal_view):
    """Opens a modal dialog in Slack"""
    url = "https://slack.com/api/views.open"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "trigger_id": trigger_id,
        "view": modal_view
    }
    response = requests.post(url, headers=headers, json=data)
    print("Modal response:", response.json())
    return response.json()

@app.route("/standup", methods=["POST"])
def standup():
    user_id = request.form.get("user_id")
    trigger_id = request.form.get("trigger_id")
    text = request.form.get("text", "").strip()
    user_name = request.form.get("user_name", "")

    print(f"✅ POST to /standup")
    print(f"User: {user_name} ({user_id}), Text: '{text}'")

    if not text:
        # Open a modal to ask for standup info
        modal_view = {
            "type": "modal",
            "callback_id": "standup_modal",
            "title": {
                "type": "plain_text",
                "text": "Daily Standup"
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit"
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel"
            },
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
                    "label": {
                        "type": "plain_text",
                        "text": "Your standup update"
                    }
                }
            ]
        }

        # Open the modal
        result = open_modal(trigger_id, modal_view)
        
        if result.get("ok"):
            # Modal opened successfully - return empty response
            return make_response("", 200)
        else:
            # Fallback if modal fails
            return jsonify({
                "response_type": "ephemeral",
                "text": "👋 What did you work on today?\n\nUse: `/standup your message here`"
            })
    
    else:
        # Handle direct text input (fallback method)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save the update
        user_updates[user_id] = {
            "update": text,
            "timestamp": timestamp,
            "user_name": user_name
        }
        
        response_text = f":white_check_mark: Got your update at *{timestamp}*\n> {text}"
        
        print("Sending response:", response_text)
        return jsonify({
            "response_type": "ephemeral",
            "text": response_text
        })

@app.route("/interactive", methods=["POST"])
def interactive():
    """Handle interactive components like modal submissions"""
    print("🔄 Interactive endpoint hit!")
    print("Request method:", request.method)
    print("Request headers:", dict(request.headers))
    print("Request form data:", dict(request.form))
    
    try:
        payload = json.loads(request.form.get("payload"))
        print("✅ Payload parsed successfully")
        print("Payload type:", payload.get("type"))
        
        if payload["type"] == "view_submission":
            # Handle modal submission
            user_id = payload["user"]["id"]
            user_name = payload["user"]["name"]
            values = payload["view"]["state"]["values"]
            standup_text = values["standup_input"]["standup_text"]["value"]
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Save the update
            user_updates[user_id] = {
                "update": standup_text,
                "timestamp": timestamp,
                "user_name": user_name
            }
            
            print(f"✅ Saved standup for {user_name}: {standup_text}")
            
            # For modal submissions, we need to use response_action: "update" 
            # to show a success message, or post a follow-up message
            return jsonify({
                "response_action": "update",
                "view": {
                    "type": "modal",
                    "title": {
                        "type": "plain_text",
                        "text": "Standup Submitted!"
                    },
                    "close": {
                        "type": "plain_text",
                        "text": "Close"
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f":white_check_mark: Got your update at *{timestamp}*\n\n> {standup_text}"
                            }
                        }
                    ]
                }
            })
        
        return make_response("", 200)
    
    except Exception as e:
        print(f"❌ Error in interactive endpoint: {e}")
        return make_response("Error processing request", 500)

# Optional: Add a route to view all standups
@app.route("/view-standups", methods=["GET"])
def view_standups():
    """Debug route to see all saved standups"""
    return jsonify(user_updates)

if __name__ == "__main__":
    app.run(port=3000, debug=True)