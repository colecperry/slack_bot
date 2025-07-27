from flask import Flask, request, make_response, jsonify
from datetime import datetime

app = Flask(__name__)
user_updates = {}

@app.route("/standup", methods=["POST"])
def standup():
    user_id = request.form.get("user_id")
    text = request.form.get("text", "").strip()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not text:
        response_text = "👋 What did you work on today?"
    else:
        # Save the update
        user_updates[user_id] = {
            "update": text,
            "timestamp": timestamp
        }
        response_text = f":white_check_mark: Got your update at *{timestamp}*\n> {text}"

    return jsonify({
        "response_type": "ephemeral",  # only the user sees this
        "text": response_text
    })

if __name__ == "__main__":
    app.run(port=3000)
