import os
from time import time
from collections import defaultdict
from flask import Flask, request, jsonify, Response
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
API_TOKEN = os.environ.get("API_TOKEN", "change-me")

SYSTEM_PROMPT = "Tu es Jarvis, l assistant IA du site Lobicoptech. Tu reponds en francais, de facon concise et utile."

_rate = defaultdict(list)
def rate_ok(ip, max_req=15, window=60):
    now = time()
    _rate[ip] = [t for t in _rate[ip] if now - t < window]
    if len(_rate[ip]) >= max_req:
        return False
    _rate[ip].append(now)
    return True

CHAT_HTML = open(os.path.join(os.path.dirname(__file__), "chat.html"), encoding="utf-8").read() if os.path.exists(os.path.join(os.path.dirname(__file__), "chat.html")) else "<h1>Chat page manquante</h1>"

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "jarvis"})

@app.route("/chat")
def chat_page():
    return Response(CHAT_HTML, mimetype="text/html")

@app.route("/api/chat-web", methods=["POST"])
def chat_web():
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "?").split(",")[0].strip()
    if not rate_ok(ip):
        return jsonify({"error": "Trop de requetes"}), 429
    data = request.get_json() or {}
    messages_in = data.get("messages")
    if not messages_in or not isinstance(messages_in, list):
        return jsonify({"error": "Champ messages requis"}), 400
    messages_in = messages_in[-20:]
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages_in],
            temperature=0.7, max_tokens=1000,
        )
        return jsonify({"response": completion.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def require_token(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.headers.get("X-API-Token") != API_TOKEN:
            return jsonify({"error": "Acces non autorise"}), 401
        return f(*args, **kwargs)
    return wrapper

@app.route("/api/chat", methods=["POST"])
@require_token
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Champ message requis"}), 400
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": SYSTEM_PROMPT},{"role": "user", "content": data["message"]}],
            temperature=0.7, max_tokens=500,
        )
        return jsonify({"response": completion.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
