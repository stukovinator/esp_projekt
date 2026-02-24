from flask import Flask, jsonify, request
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

latest_temp = None
last_updated = None

@app.route('/temperature', methods=['GET'])
def get_temp():
    return jsonify({
        "temperature": latest_temp,
        "last_updated": last_updated
    })

@app.route('/temperature', methods=['POST'])
def post_temp():
    global latest_temp, last_updated
    data = request.get_json()
    latest_temp = data.get("temperature")
    last_updated = data.get("timestamp")
    return jsonify({"ok": True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)