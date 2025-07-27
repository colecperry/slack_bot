'''
app.py creates a lightweight web server using Flask
'''

from flask import Flask, request, make_response

app = Flask(__name__) # Initialize the app

# route /standup, slack sends a post request to our server
@app.route('/standup', methods=['POST'])
def standup():
    data = request.form  # Slack sends form-encoded data
    print("Received data:", data)

    return make_response("Got it!", 200)

if __name__ == '__main__':
    app.run(port=5000)

