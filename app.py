import os
from time import time
from collections import defaultdict
from flask import Flask, request, jsonify, Response
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
API_TOKEN = os.environ.get("API_TOKEN", "change-me")

SYSTEM_PROMPT = "Tu es Jarvis, l'assistant IA du site Lobicoptech. Tu réponds en français, de façon concise et utile."

# --- Rate limiting basique en mémoire (par IP) ---
_rate = defaultdict(list)
def rate_ok(ip, max_req=15, window=60):
    now = time()
    _rate[ip] = [t for t in _rate[ip] if now - t < window]
    if len(_rate[ip]) >= max_req:
        return False
    _rate[ip].append(now)
    return True

# --- Page HTML de chat ---
CHAT_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jarvis - Assistant IA</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f5f7;height:100vh;display:flex;flex-direction:column}
  header{background:#1a1a2e;color:white;padding:16px 24px;display:flex;align-items:center;gap:12px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
  .avatar{width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#667eea,#764ba2);display:flex;align-items:center;justify-content:center;font-weight:bold}
  header h1{font-size:18px;font-weight:600}
  header p{font-size:12px;opacity:.7}
  #messages{flex:1;overflow-y:auto;padding:24px;display:flex;flex-direction:column;gap:16px}
  .msg{display:flex;gap:12px;max-width:800px;margin:0 auto;width:100%}
  .msg.user{flex-direction:row-reverse}
  .bubble{padding:12px 16px;border-radius:16px;max-width:75%;line-height:1.5;white-space:pre-wrap;word-wrap:break-word}
  .msg.user .bubble{background:#1a1a2e;color:white}
  .msg.bot .bubble{background:white;color:#222;box-shadow:0 1px 3px rgba(0,0,0,0.08)}
  .welcome{text-align:center;color:#666;margin:40px auto;max-width:500px}
  .welcome h2{font-size:24px;margin-bottom:12px;color:#1a1a2e}
  .welcome p{font-size:14px;line-height:1.6}
  #input-area{background:white;padding:16px 24px;border-top:1px solid #e5e5e5}
  #input-wrapper{max-width:800px;margin:0 auto;display:flex;gap:12px}
  #user-input{flex:1;padding:14px 18px;border:1px solid #ddd;border-radius:24px;font-size:15px;outline:none;font-family:inherit}
  #user-input:focus{border-color:#667eea}
  #send-btn{padding:14px 24px;background:#1a1a2e;color:white;border:none;border-radius:24px;cursor:pointer;font-weight:600;font-size:15px}
  #send-btn:disabled{opacity:.5;cursor:not-allowed}
  .typing{display:inline-flex;gap:4px}
  .typing span{width:8px;height:8px;border-radius:50%;background:#999;animation:bounce 1.4s infinite}
  .typing span:nth-child(2){animation-delay:.2s}
  .typing span:nth-child(3){animation-delay:.4s}
  @keyframes bounce{0%,80%,100%{transform:translateY(0);opacity:.5}40%{transform:translateY(-6px);opacity:1}}
</style>
</head>
<body>
<header>
  <div class="avatar">J</div>
  <div><h1>Jarvis</h1><p>Assistant IA de Lobicoptech</p></div>
</header>
<div id="messages">
  <div class="welcome" id="welcome">
    <h2>Bonjour 👋</h2>
    <p>Je suis Jarvis, votre assistant IA. Posez-moi n'importe quelle question, je suis là pour vous aider.</p>
  </div>
</div>
<div id="input-area">
  <div id="input-wrapper">
    <input id="user-input" type="text" placeholder="Posez votre question..." autocomplete="off">
    <button id="send-btn">Envoyer</button>
  </div>
</div>
<script>
const messagesDiv=document.getElementById('messages');
const input=document.getElementById('user-input');
const btn=document.getElementById('send-btn');
const welcome=document.getElementById('welcome');
const history=[];

function addMessage(role,text){
  if(welcome)welcome.style.display='none';
  const msg=document.createElement('div');
  msg.className='msg '+role;
  const bubble=document.createElement('div');
  bubble.className='bubble';
  bubble.textContent=text;
  msg.appendChild(bubble);
  messagesDiv.appendChild(msg);
  messagesDiv.scrollTop=messagesDiv.scrollHeight;
}
function addTyping(){
  if(welcome)welcome.style.display='none';
  const msg=document.createElement('div');
  msg.className='msg bot';msg.id='typing-indicator';
  msg.innerHTML='<div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>';
  messagesDiv.appendChild(msg);
  messagesDiv.scrollTop=messagesDiv.scrollHeight;
  return msg;
}
async function sendMessage(){
  const text=input.value.trim();
  if(!text)return;
  input.value='';btn.disabled=true;
  addMessage('user',text);
  history.push({role:'user',content:text});
  const typing=addTyping();
  try{
    const res=await fetch('/api/chat-web',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({messages:history})
    });
    const data=await res.json();
    typing.remove();
    if(data.response){
      addMessage('bot',data.response);
      history.push({role:'assistant',content:data.response});
    }else{
      addMessage('bot','❌ '+(data.error||'Erreur inconnue'));
    }
  }catch(e){
    typing.remove();
    addMessage('bot','❌ Erreur réseau : '+e.message);
  }
  btn.disabled=false;input.focus();
}
btn.addEventListener('click',sendMessage);
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}});
input.focus();
</script>
</body>
</html>"""

# --- Routes ---
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
        return jsonify({"error": "Trop de requêtes, patientez une minute."}), 429
    data = request.get_json() or {}
    messages_in = data.get("messages")
    if not messages_in or not isinstance(messages_in, list):
        return jsonify({"error": "Champ 'messages' requis (liste)."}), 400
    messages_in = messages_in[-20:]
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *messages_in],
            temperature=0.7,
            max_tokens=1000,
        )
        return jsonify({"response": completion.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Ancienne route protégée (usage programmatique) ---
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
        return jsonify({"error": "Champ message requis."}), 400
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": data["message"]}],
            temperature=0.7, max_tokens=500,
        )
        return jsonify({"response": completion.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
