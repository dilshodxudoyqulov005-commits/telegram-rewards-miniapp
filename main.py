
import os
import time
import json
import hmac
import hashlib
import requests

from urllib.parse import parse_qsl
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL = "@dilshod_ai_yordamchi"


def verify_init_data(init_data):
    if not BOT_TOKEN or not init_data:
        return None

    try:
        data = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = data.pop("hash", "")
        auth_date = int(data.get("auth_date", "0"))

        if not received_hash or time.time() - auth_date > 86400:
            return None

        check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(data.items())
        )

        secret = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        calculated = hmac.new(
            secret,
            check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated, received_hash):
            return None

        return json.loads(data["user"])

    except (ValueError, KeyError, TypeError):
        return None


@app.route("/")
def home():
    return "Bonus Arena server ishlayapti!"


@app.route("/check-subscription", methods=["POST"])
def check_subscription():
    body = request.get_json(silent=True) or {}
    user = verify_init_data(body.get("initData", ""))

    if not user:
        return jsonify({
            "ok": False,
            "error": "Telegram foydalanuvchisi tasdiqlanmadi"
        }), 401

    try:
        response = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember",
            params={
                "chat_id": CHANNEL,
                "user_id": user["id"]
            },
            timeout=15
        )
        result = response.json()

        if not result.get("ok"):
            return jsonify({
                "ok": False,
                "error": "Obunani tekshirib bo‘lmadi"
            }), 502

        member = result["result"]
        status = member.get("status")

        subscribed = (
            status in ("creator", "administrator", "member")
            or (
                status == "restricted"
                and member.get("is_member", False)
            )
        )

        return jsonify({
            "ok": True,
            "subscribed": subscribed
        })

    except requests.RequestException:
        return jsonify({
            "ok": False,
            "error": "Server bilan bog‘lanishda xato"
        }), 502


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
