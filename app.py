# app.py
# python app.pye>
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

LATEST = {"raw": None, "voltage": None, "time": None}

@app.route("/", methods=["GET"])
def index():
    return jsonify({"msg":"Flask server OK. POST to /post_value"})

@app.route("/post_value", methods=["POST"])
def post_value():
    data = request.get_json(force=True)
    print("POST received path:", request.path, "method:", request.method)
    print("Data:", data)
    LATEST["raw"] = data.get("raw")
    LATEST["voltage"] = data.get("voltage")
    LATEST["time"] = datetime.now().isoformat()
    return jsonify({"status":"ok","latest":LATEST})

@app.route("/value", methods=["GET"])
def get_value():
    return jsonify(LATEST)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
