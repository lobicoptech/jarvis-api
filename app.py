import os
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
API_TOKEN = os.environ.get("API_TOKEN", "change-me")

def require_token(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.headers.get("X-API-Token") != API_TOKEN:
            return jsonify({"error": "Acces non autorise"}), 401
        return f(*args, **kwargs)
    return wrapper

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "jarvis"})

@app.route("/api/chat", methods=["POST"])
@require_token
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Champ message requis."}), 400
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "Tu es Jarvis, l assistant IA du site Lobicoptech. Reponds en francais, de facon concise."},
                {"role": "user", "content": data["message"]},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        return jsonify({"response": completion.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
