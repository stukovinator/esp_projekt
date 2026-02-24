from flask import Flask, jsonify, request

app = Flask(__name__)
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
    app.run(debug=True, host='0.0.0.0') 