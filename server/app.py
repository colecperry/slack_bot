from flask import Flask, request, make_response, jsonify
from datetime import datetime
import json
import requests

app = Flask(__name__)
user_updates = {}

@app.route("/standup", methods=["POST"])
def standup():
    user_id = request.form.get("user_id")
    trigger_id = request.form.get("trigger_id")
    text = request.form.get("text", "").strip()

    print(f"✅ POST to /standup")
    print(f"User: {user_id}, Text: '{text}', Trigger ID: {trigger_id}")

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

        # You'll need to replace with your bot token
        # For now, return a simple response asking for the token setup
        return jsonify({
            "response_type": "ephemeral",
            "text": "👋 What did you work on today? (Note: Modal functionality requires bot token setup)\n\nFor now, use: `/standup your message here`"
        })
    
    else:
        # Handle direct text input
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save the update
        user_updates[user_id] = {
            "update": text,
            "timestamp": timestamp
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
    payload = json.loads(request.form.get("payload"))
    
    print("Interactive payload:", payload)
    
    if payload["type"] == "view_submission":
        # Handle modal submission
        user_id = payload["user"]["id"]
        values = payload["view"]["state"]["values"]
        standup_text = values["standup_input"]["standup_text"]["value"]
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save the update
        user_updates[user_id] = {
            "update": standup_text,
            "timestamp": timestamp
        }
        
        print(f"Saved standup for {user_id}: {standup_text}")
        
        # Return success response
        return jsonify({
            "response_action": "clear"
        })
    
    return make_response("", 200)

if __name__ == "__main__":
    app.run(port=3000, debug=True)