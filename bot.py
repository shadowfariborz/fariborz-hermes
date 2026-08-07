"""
🤖 Fariborz Bot v6 - Public Bot (runs alongside Hermes)
Features: Admin panel, Game, Dol, Broadcast, Welcome, ACRCloud, AI Chat via Hermes
"""
import os, json, time, base64, sqlite3, threading, uuid, hmac, hashlib, io, math, struct, hashlib as hl
from flask import Flask, request, Response
import requests as http

# ─── Config ───────────────────────────────────────────────────────────
TG_TOKEN = os.environ.get("FARIBORZ_BOT_TOKEN", "")
HERMES_URL = os.environ.get("HERMES_URL", "http://localhost:8000")
API_SECRET = os.environ.get("API_SECRET", "fariborz-hermes-2024")
ADMIN_ID = str(os.environ.get("ADMIN_ID", ""))
ADMIN2_ID = str(os.environ.get("ADMIN2_ID", ""))
BOT_PORT = int(os.environ.get("BOT_PORT", 8001))

ACR_HOST = os.environ.get("ACR_HOST", "")
ACR_ACCESS_KEY = os.environ.get("ACR_ACCESS_KEY", "")
ACR_SECRET_KEY = os.environ.get("ACR_SECRET_KEY", "")

TG = f"https://api.telegram.org/bot{TG_TOKEN}"
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fariborz.db")
os.makedirs(os.path.dirname(DB), exist_ok=True)
lock = threading.Lock()

REQUIRED_CHANNELS = [
    {"username": "@nuxaldev", "url": "https://t.me/nuxaldev", "name": "Nuxaldev 👤"},
    {"username": "@FutureeeProcess", "url": "https://t.me/FutureeeProcess", "name": "Future Process 🚀"},
]
MENTION_PATTERNS = ["فریبرز", "fariborz", "@fariborz_bot", "@nuxal_bot"]
RATE_LIMIT = 3

BOT_USERNAME = ""
try:
    info = http.get(f"{TG}/getMe", timeout=10).json()
    BOT_USERNAME = info.get("result", {}).get("username", "")
except:
    pass

# ─── DB ───────────────────────────────────────────────────────────────
def init_db():
    c = sqlite3.connect(DB)
    c.executescript("""
        CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, val TEXT);
        CREATE TABLE IF NOT EXISTS chat_history (cid TEXT, role TEXT, text TEXT, ts INTEGER);
        CREATE TABLE IF NOT EXISTS scores (uid TEXT PRIMARY KEY, name TEXT, score INTEGER, ts INTEGER);
        CREATE TABLE IF NOT EXISTS bans (uid TEXT PRIMARY KEY, name TEXT, reason TEXT, offense INTEGER, banned_at INTEGER, unban_at INTEGER, perm INTEGER);
        CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, uid TEXT, name TEXT, start_ts INTEGER);
    """); c.commit(); c.close()
init_db()

def kv_get(k):
    c=sqlite3.connect(DB); r=c.execute("SELECT val FROM kv WHERE key=?", (k,)).fetchone(); c.close()
    return r[0] if r else None
def kv_set(k,v):
    with lock: c=sqlite3.connect(DB); c.execute("INSERT OR REPLACE INTO kv VALUES(?,?)", (k,str(v))); c.commit(); c.close()
def kv_del(k):
    with lock: c=sqlite3.connect(DB); c.execute("DELETE FROM kv WHERE key=?", (k,)); c.commit(); c.close()
def kv_json(k):
    v=kv_get(k); return json.loads(v) if v else None
def kv_setj(k,d): kv_set(k, json.dumps(d, ensure_ascii=False))

# ─── Telegram ─────────────────────────────────────────────────────────
def tg(method, **kw):
    try: return http.post(f"{TG}/{method}", json=kw, timeout=15).json()
    except: return {"ok": False}

def send_msg(cid, text, reply=None, parse_mode=None):
    p = {"chat_id": cid, "text": text}
    if reply: p["reply_to_message_id"] = reply
    if parse_mode: p["parse_mode"] = parse_mode
    return tg("sendMessage", **p)

def send_action(cid, act): return tg("sendChatAction", chat_id=cid, action=act)

def send_photo(cid, data, cap=""):
    try: http.post(f"{TG}/sendPhoto", files={"photo": ("img.jpg", data, "image/jpeg")}, data={"chat_id": str(cid), "caption": cap}, timeout=30)
    except: pass

def send_voice(cid, data):
    try: http.post(f"{TG}/sendVoice", files={"voice": ("v.ogg", data, "audio/ogg")}, data={"chat_id": str(cid)}, timeout=30)
    except: pass

def send_document(cid, data, fname="file"):
    try: http.post(f"{TG}/sendDocument", files={"document": (fname, data)}, data={"chat_id": str(cid)}, timeout=30)
    except: pass

def dl_file(fid):
    try:
        i = tg("getFile", file_id=fid)
        if not i.get("ok"): return None
        return http.get(f"https://api.telegram.org/file/bot{TG_TOKEN}/{i['result']['file_path']}", timeout=30).content
    except: return None

# ─── Hermes API ───────────────────────────────────────────────────────
def hermes_chat(message, user_id, user_name, image_b64=None):
    """Direct OpenAI API call (no agent_server needed)"""
    try:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if not api_key:
            return "⚠️ OPENAI_API_KEY تنظیم نشده"
        
        # Build messages
        messages = [{"role": "system", "content": "تو فریبرز هستی، یک ربات فارسی‌زبان دوستانه و باهوش. با فارسی جواب بده مگر اینکه کاربر انگلیسی حرف بزنه."}]
        
        # Load history
        h = kv_get(f"hist_{user_id}")
        if h:
            try:
                history = json.loads(h)
                messages.extend(history[-10:])
            except: pass
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call OpenAI-compatible API
        r = http.post(f"{base_url}/chat/completions", 
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": os.environ.get("LLM_MODEL", "gpt-3.5-turbo"), "messages": messages, "max_tokens": 1500},
            timeout=60)
        
        # Parse JSON safely
        try:
            rj = r.json()
        except:
            # Try to extract JSON from response text
            txt = r.text
            try:
                rj = json.loads(txt[:r.text.find('}{')+1] if '}{' in txt else txt)
            except:
                return f"❌ پاسخ نامعتبر از سرور"
        
        if rj.get("error"):
            return f"⚠️ {rj['error'].get('message', 'خطا')}"
        
        reply = rj.get("choices", [{}])[0].get("message", {}).get("content", "پاسخی دریافت نشد")
        
        # Save history
        messages.append({"role": "assistant", "content": reply[:500]})
        if len(messages) > 20: messages = messages[-20:]
        kv_set(f"hist_{user_id}", json.dumps(messages[-10:], ensure_ascii=False))
        
        return reply
    except Exception as e:
        return f"❌ خطا: {str(e)[:100]}"

def hermes_stt(audio_b64):
    try:
        r = http.post(f"{HERMES_URL}/speech-to-text", json={"token": API_SECRET, "audio_base64": audio_b64}, timeout=60).json()
        return r.get("text")
    except: return None

def hermes_tts(text):
    try:
        r = http.post(f"{HERMES_URL}/text-to-speech", json={"token": API_SECRET, "text": text}, timeout=60).json()
        return r.get("audio_base64")
    except: return None

def hermes_image(prompt):
    try:
        r = http.post(f"{HERMES_URL}/generate-image", json={"token": API_SECRET, "prompt": prompt}, timeout=120).json()
        return r.get("image_base64")
    except: return None

# ─── Persian Date ─────────────────────────────────────────────────────
def persian_date():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone(timedelta(hours=3, minutes=30)))
    gy,gm,gd = now.year,now.month,now.day
    g_d_m = [0,31,59,90,120,151,181,212,243,273,304,334]
    gy2 = gy+1 if gm>2 else gy
    days = 355666+365*gy+(gy2+3)//4-(gy2+99)//100+(gy2+399)//400+gd+g_d_m[gm-1]
    jy = -1595+33*(days//12053); days %= 12053; jy += 4*(days//1461); days %= 1461
    if days>365: jy+=(days-1)//365; days=(days-1)%365
    jm = 1+days//31 if days<186 else 7+(days-186)//30
    jd = 1+days%31 if days<186 else 1+(days-186)%30
    wd = ["یکشنبه","دوشنبه","سه‌شنبه","چهارشنبه","پنجشنبه","جمعه","شنبه"][now.weekday()]
    mn = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور","مهر","آبان","آذر","دی","بهمن","اسفند"]
    return {
        "persian": {"full": f"{wd}، {jd} {mn[jm-1]} {jy}", "weekday": wd, "day": jd, "month": mn[jm-1], "year": jy},
        "time": f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}",
        "hour": now.hour, "minute": now.minute, "second": now.second
    }

# ─── Admin ────────────────────────────────────────────────────────────
def is_admin(uid):
    u = str(uid)
    if u == ADMIN_ID or u == ADMIN2_ID: return True
    admins = kv_json("admin_list") or []
    return any(a.get("userId") == u for a in admins)

def is_main(uid): return str(uid) == ADMIN_ID

# ─── Channels ─────────────────────────────────────────────────────────
def check_channels(uid):
    for ch in REQUIRED_CHANNELS:
        try:
            r = tg("getChatMember", chat_id=ch["username"], user_id=uid)
            if r.get("ok") and r["result"]["status"] not in ["left","kicked"]: continue
        except: pass
        return False
    return True

# ─── Rate Limit ───────────────────────────────────────────────────────
def rate_ok(uid):
    v = kv_get(f"rl_{uid}")
    if v and (time.time()-float(v)) < RATE_LIMIT: return False
    kv_set(f"rl_{uid}", str(time.time())); return True

# ─── Game ─────────────────────────────────────────────────────────────
def max_score(ms): return int((ms/1000)*15)

def get_ban(uid):
    c=sqlite3.connect(DB); r=c.execute("SELECT * FROM bans WHERE uid=?", (str(uid),)).fetchone(); c.close()
    if not r: return None
    if r[5] and time.time()*1000 > r[5]: return None
    return {"offense":r[3],"perm":r[6]}

def auto_ban(uid, name, reason):
    with lock:
        c=sqlite3.connect(DB)
        row=c.execute("SELECT offense FROM bans WHERE uid=?", (str(uid),)).fetchone()
        off=(row[0] if row else 0)+1
        durs={1:1,2:7,3:30,4:90,5:180,6:365}
        perm=off>6; days=36500 if perm else durs.get(off,365)
        unban=None if perm else time.time()*1000+days*86400000
        c.execute("INSERT OR REPLACE INTO bans VALUES(?,?,?,?,?,?,?)",(str(uid),name,reason,off,int(time.time()*1000),unban,1 if perm else 0))
        c.commit(); c.close()
    return {"offense":off,"days":days,"perm":perm}

def submit_score(uid, name, score):
    with lock:
        c=sqlite3.connect(DB)
        c.execute("INSERT OR REPLACE INTO scores VALUES(?,?,?,?)",(str(uid),name,score,int(time.time())))
        rank=c.execute("SELECT COUNT(*) FROM scores WHERE score>?",(score,)).fetchone()[0]+1
        total=c.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        c.commit(); c.close()
    return {"success":True,"score":score,"rank":rank,"total":total}

def leaderboard():
    c=sqlite3.connect(DB); r=c.execute("SELECT uid,name,score FROM scores ORDER BY score DESC LIMIT 10").fetchall(); c.close()
    return [{"uid":x[0],"name":x[1],"score":x[2]} for x in r]

def validate_init(data, token):
    try:
        from urllib.parse import parse_qs
        p=parse_qs(data); h=p.pop("hash",[None])[0]
        if not h: return None
        s="\n".join(f"{k}={v[0]}" for k,v in sorted(p.items()))
        sk=hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        sig=hmac.new(sk, s.encode(), hashlib.sha256).hexdigest()
        if sig!=h: return None
        u=json.loads(p.get("user",["{}"])[0])
        return {"userId":str(u.get("id","")),"firstName":u.get("first_name","")}
    except: return None

# ─── ACRCloud Song Identification ─────────────────────────────────────
def acr_identify(audio_bytes):
    if not ACR_HOST or not ACR_ACCESS_KEY or not ACR_SECRET_KEY: return None
    import hmac as hm
    http_method="POST"; http_uri="/v1/identify"; dataType="audio"; signatureVersion="1"
    timestamp=str(int(time.time()))
    string_to_sign=f"{http_method}\n{http_uri}\n{ACR_ACCESS_KEY}\n{dataType}\n{signatureVersion}\n{timestamp}"
    signature=base64.b64encode(hm.new(ACR_SECRET_KEY.encode(), string_to_sign.encode(), hl.sha1).digest()).decode()
    form={"access_key":ACR_ACCESS_KEY,"data_type":dataType,"signature_version":signatureVersion,"signature":signature,"timestamp":timestamp,"sample_bytes":str(len(audio_bytes))}
    try:
        r=http.post(f"https://{ACR_HOST}{http_uri}", data=form, files={"sample":("audio",audio_bytes,"audio/mpeg")}, timeout=15).json()
        return r
    except: return None

# ─── Help Text ────────────────────────────────────────────────────────
HELP = """🤖 راهنمای ربات فریبرز 🤖

🔄 کامندها:
🔹 /start - شروع 🚀
🔹 /help - راهنما 📚
🔹 /new - گفتگوی جدید 🔄
🔹 /ping - تست سرعت 🏓
🔹 /dice - تاس 🎲
🔹 /time - ساعت ⏰
🔹 /date - تاریخ 📅
🔹 /dol - پروکسی 🎁
🔹 /game - بازی 🦖
🔹 /top - رتبه‌بندی 🏆

💬 چت: هر متنی → جواب
🎤 ویس → میفهمم
🎵 فایل صوتی → شناسایی آهنگ
🎨 "عکس بساز ..." → عکس
🔊 "ویس بفرست ..." → صدا

⭐ هر سوالی بپرس! 😊"""

# ─── Flask ─────────────────────────────────────────────────────────────
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home(): return "Fariborz Bot v6 (Hermes Powered) ✅"

@app.route("/health", methods=["GET"])
def health(): return '{"status":"ok","bot":"fariborz-v6"}'

@app.route("/setup", methods=["GET"])
def setup():
    url = request.url_root.rstrip("/")
    if url.startswith("http://"): url = "https://"+url[7:]
    r = tg("setWebhook", url=url)
    return f"Webhook: {r}"

@app.route("/dino-game", methods=["GET"])
def dino():
    return Response(DINO_HTML.replace("{{BASE}}", request.url_root.rstrip("/")), content_type="text/html; charset=utf-8")

@app.route("/dino-game/play", methods=["GET"])
def dino_play():
    return Response(DINO_HTML.replace("{{BASE}}", request.url_root.rstrip("/")), content_type="text/html; charset=utf-8")

@app.route("/api/game/leaderboard", methods=["GET"])
def api_lb(): return json.dumps(leaderboard()), 200, {"Content-Type":"application/json","Access-Control-Allow-Origin":"*"}

@app.route("/api/game/session/start", methods=["POST"])
def api_start():
    try:
        b=request.json; auth=validate_init(b.get("initData",""), TG_TOKEN)
        if not auth: return json.dumps({"error":"auth"}),401
        if get_ban(auth["userId"]): return json.dumps({"error":"banned"}),403
        t=str(uuid.uuid4())
        with lock:
            c=sqlite3.connect(DB); c.execute("INSERT INTO sessions VALUES(?,?,?,?)",(t,auth["userId"],auth["firstName"],int(time.time()*1000))); c.commit(); c.close()
        return json.dumps({"token":t})
    except Exception as e: return json.dumps({"error":str(e)}),400

@app.route("/api/game/submit", methods=["POST"])
def api_submit():
    try:
        b=request.json; auth=validate_init(b.get("initData",""), TG_TOKEN)
        if not auth: return json.dumps({"error":"auth"}),401
        if get_ban(auth["userId"]): return json.dumps({"error":"banned"}),403
        t=b.get("token")
        with lock:
            c=sqlite3.connect(DB)
            s=c.execute("SELECT * FROM sessions WHERE token=?", (t,)).fetchone()
            if not s or s[1]!=auth["userId"]: c.close(); return json.dumps({"error":"session"}),400
            c.execute("DELETE FROM sessions WHERE token=?", (t,)); c.commit(); c.close()
        ns=int(b.get("score",0))
        if ns<0: return json.dumps({"error":"bad"}),400
        el=int(time.time()*1000)-s[3]
        if ns>max_score(el): return json.dumps({"error":"inconsistent"}),400
        if ns>2000:
            br=auto_ban(auth["userId"],auth["firstName"],"تقلب")
            try: send_msg(auth["userId"],f"🚫 بن شدید!\n دلیل: تقلب\n دفعه: {br['offense']}\n مدت: {'دائمی' if br['perm'] else str(br['days'])+' روز'}")
            except: pass
            return json.dumps({"error":"banned"}),403
        return json.dumps(submit_score(auth["userId"],auth["firstName"],ns))
    except Exception as e: return json.dumps({"error":str(e)}),400

# ─── Main Webhook ─────────────────────────────────────────────────────
@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.json
        if not data: return "OK"

        # Callback queries
        if "callback_query" in data:
            cq = data["callback_query"]; cd = cq["data"]
            cid = cq["message"]["chat"]["id"]; mid = cq["message"]["message_id"]
            if cd == "show_config":
                cfg = kv_get("config") or "خالی"
                if "<pre>" not in cfg: cfg = f"<pre><code>{cfg}</code></pre>"
                tg("editMessageText", chat_id=cid, message_id=mid, text=f"⚙️ ساب:\n\n{cfg}", parse_mode="HTML",
                   reply_markup={"inline_keyboard":[[{"text":"🔙","callback_data":"back_to_dol"}]]})
            elif cd == "back_to_dol":
                dol = kv_get("dol_inline") or "خالی!"
                tg("editMessageText", chat_id=cid, message_id=mid, text=dol,
                   reply_markup={"inline_keyboard":[[{"text":"⚙️ ساب","callback_data":"show_config"}]]})
            tg("answerCallbackQuery", callback_query_id=cq["id"])
            return "OK"

        msg = data.get("message")
        if not msg: return "OK"

        cid = msg["chat"]["id"]; uid = str(msg["from"]["id"])
        name = msg["from"].get("first_name","")
        text = (msg.get("text") or msg.get("caption") or "").strip()
        mid = msg["message_id"]; is_pv = msg["chat"]["type"]=="private"
        is_grp = not is_pv

        if not rate_ok(uid): return "OK"

        # Save groups for broadcast
        if is_grp:
            grps = kv_json("broadcast_groups") or []
            if not any(g["chat_id"]==cid for g in grps):
                grps.append({"chat_id":cid,"title":msg["chat"].get("title",""),"added_at":int(time.time()*1000)})
                kv_setj("broadcast_groups", grps)

        # Welcome / Goodbye
        if msg.get("new_chat_members"):
            for m in msg["new_chat_members"]:
                if str(m["id"]) == BOT_USERNAME: continue
                d = persian_date()
                wd = kv_get("welcome_text")
                if wd:
                    wd = wd.replace("!mention", f'[{m.get("first_name","کاربر")}](tg://user?id={m["id"]})')
                    wd = wd.replace("!firstname", m.get("first_name","کاربر"))
                    wd = wd.replace("!groupname", msg["chat"].get("title","گروه"))
                    send_msg(cid, wd, parse_mode="Markdown")
                else:
                    send_msg(cid, f'👋 خوش آمدی [{m.get("first_name","کاربر")}](tg://user?id={m["id"]})!\n\nگروه {msg["chat"].get("title","")}\n⏰ {d["time"]}\n📅 {d["persian"]["full"]}\n\nهر سوالی داشتی بگو 😊', parse_mode="Markdown")
            return "OK"
        if msg.get("left_chat_member"):
            m = msg["left_chat_member"]; d = persian_date()
            send_msg(cid, f'👋 خداحافظ [{m.get("first_name","کاربر")}](tg://user?id={m["id"]})!\n\n⏰ {d["time"]}\n📅 {d["persian"]["full"]}', parse_mode="Markdown")
            return "OK"

        # Group filter: only respond when mentioned or replied to THIS bot
        if is_grp:
            rf = (msg.get("reply_to_message") or {}).get("from",{})
            my_id = int(BOT_USERNAME) if BOT_USERNAME.isdigit() else None
            if not my_id:
                try: my_id = int(TG_TOKEN.split(":")[0])
                except: my_id = None
            is_reply_bot = rf.get("id") == my_id if my_id else False
            is_ment = any(p.lower() in text.lower() for p in MENTION_PATTERNS)
            if not is_reply_bot and not is_ment: return "OK"
            for p in MENTION_PATTERNS: text = text.replace(p,"").strip()

        # Voice → STT
        if "voice" in msg:
            send_action(cid, "record_voice")
            d = dl_file(msg["voice"]["file_id"])
            if not d: send_msg(cid, "❌ خطا در دانلود صدا", mid); return "OK"
            b64 = base64.b64encode(d).decode()
            stt_text = hermes_stt(b64)
            if not stt_text: send_msg(cid, "❌ نتونستم صدا رو بفهمم", mid); return "OK"
            send_msg(cid, f'🎤 شنیدم: "{stt_text}"', mid)
            text = stt_text

        # Audio file → Song identification
        if "audio" in msg and not text:
            send_action(cid, "upload_audio")
            d = dl_file(msg["audio"]["file_id"])
            if d:
                result = acr_identify(d)
                if result and result.get("status",{}).get("code") == 0:
                    ms = result.get("metadata",{}).get("music",[{}])[0]
                    t = ms.get("title","نامعلوم")
                    ar = ms.get("artists",[{}])[0].get("name","نامعلوم")
                    al = ms.get("album",{}).get("name","نامعلوم")
                    send_msg(cid, f"🎵 *آهنگ پیدا شد!*\n\n🎶 عنوان: {t}\n👤 خواننده: {ar}\n💿 آلبوم: {al}", mid, parse_mode="Markdown")
                else:
                    send_msg(cid, "🎵 نتونستم آهنگ رو شناسایی کنم.", mid)
            else:
                send_msg(cid, "❌ خطا در دانلود فایل", mid)
            return "OK"

        # Image gen
        if text and (text.startswith("عکس") or text.startswith("تصویر") or text.startswith("/generate-image")):
            prompt = text
            for p in ["عکس بساز","عکس بکن","تصویر بساز","تصویر بکن","/generate-image"]: prompt = prompt.replace(p,"").strip()
            if not prompt: send_msg(cid, "🎨 موضوع عکس رو بگو!", mid); return "OK"
            send_action(cid, "upload_photo")
            b64 = hermes_image(prompt)
            if b64: send_photo(cid, base64.b64decode(b64), f"🎨 {prompt}")
            else: send_msg(cid, "❌ نتونستم عکس بسازم", mid)
            return "OK"

        # TTS
        if text and (text.startswith("ویس") or text.startswith("صدا") or text.startswith("/voice")):
            t = text
            for p in ["ویس بفرست","ویس بده","صدا بفرست","صدا بده","/voice"]: t = t.replace(p,"").strip()
            if not t: send_msg(cid, "🔊 متن رو بگو!", mid); return "OK"
            send_action(cid, "record_voice")
            b64 = hermes_tts(t)
            if b64: send_voice(cid, base64.b64decode(b64))
            else: send_msg(cid, "❌ نتونستم صدا بسازم", mid)
            return "OK"

        # ── Commands ────────────────────────────────────────────────
        parts = text.split(None,1) if text.startswith("/") else ["",""]
        cmd = parts[0][1:].lower() if parts[0].startswith("/") else ""
        args = parts[1] if len(parts)>1 else ""

        if cmd=="start": send_msg(cid, f"سلام {name}! 👋\nمن فریبرز هستم.\n\n💬 متن بفرست\n🎤 ویس بفرست\n🎵 آهنگ بفرست\n🎨 \"عکس بساز\"\n🔊 \"ویس بفرست\"", mid); return "OK"
        if cmd=="help": send_msg(cid, HELP, mid); return "OK"
        if cmd=="new":
            with lock: c=sqlite3.connect(DB); c.execute("DELETE FROM chat_history WHERE cid=?", (str(cid),)); c.commit(); c.close()
            send_msg(cid, "🔄 تاریخچه پاک شد!", mid); return "OK"
        if cmd=="ping":
            st=time.time(); pm=tg("sendMessage",chat_id=cid,text="🏓 پینگ...",reply_to_message_id=mid)
            if pm.get("ok"):
                pt=int((time.time()-st)*1000); tg("deleteMessage",chat_id=cid,message_id=pm["result"]["message_id"])
                s="⚡عالی" if pt<100 else "✅خوب" if pt<300 else "🤔متوسط" if pt<600 else "⚠️ضعیف"
                send_msg(cid, f"🏓 *پینگ:* {pt}ms {s}", mid)
            return "OK"
        if cmd=="dice": tg("sendDice",chat_id=cid,emoji="🎲"); return "OK"
        if cmd=="time": d=persian_date(); send_msg(cid, f"⏰ ساعت: {d['time']}", mid); return "OK"
        if cmd=="date": d=persian_date(); send_msg(cid, f"📅 {d['persian']['full']}", mid); return "OK"
        if cmd=="pv":
            try: tg("sendMessage",chat_id=uid,text="سلام! 😊")
            except: send_msg(cid, "❌ بات رو استارت کن!", mid)
            return "OK"
        if cmd=="game":
            base=request.url_root.rstrip("/")
            tg("sendMessage",chat_id=cid,text="🦕 *بازی دایناسور!*",parse_mode="Markdown",
               reply_markup={"inline_keyboard":[[{"text":"🎮 شروع","url":f"{base}/dino-game"}]]},reply_to_message_id=mid)
            return "OK"
        if cmd=="top":
            lb=leaderboard(); t="🏆 *رتبه‌بندی*\n\n"
            if not lb: t+="❌ هنوز کسی بازی نکرده!"
            else:
                medals=["🥇","🥈","🥉"]
                for i,s in enumerate(lb):
                    p=medals[i] if i<3 else f"#{i+1}"
                    me=" 👈" if s["uid"]==uid else ""
                    t+=f"{p} {s['name'] or 'بازیکن'}{me} — {s['score']:,}\n"
            send_msg(cid, t, mid); return "OK"
        if cmd=="dol":
            if is_pv or check_channels(uid):
                dt=kv_get("dol_inline")
                if dt: tg("sendMessage",chat_id=cid,text=dt,reply_markup={"inline_keyboard":[[{"text":"⚙️ ساب","callback_data":"show_config"}]]},reply_to_message_id=mid)
                else: send_msg(cid, "🎁 خالی!", mid)
            else: send_msg(cid, "⚠️ عضو کانال شید:\n📢 @nuxaldev\n🚀 @FutureeeProcess", mid)
            return "OK"

        # ── Admin Commands (PV only) ───────────────────────────────
        if is_pv and is_admin(uid):
            if cmd=="list": send_msg(cid, kv_get("dol_inline") or "خالی."); return "OK"
            if cmd=="adddol":
                if not args: send_msg(cid, "📝 /adddol متن")
                else: kv_set("dol_inline", args); send_msg(cid, "✅ اضافه شد!")
                return "OK"
            if cmd=="broadcast":
                if not args: send_msg(cid, "📝 /broadcast متن")
                else:
                    gs=kv_json("broadcast_groups") or []; sent=0
                    for g in gs:
                        try: tg("sendMessage",chat_id=g["chat_id"],text=args,parse_mode="Markdown"); sent+=1
                        except: pass
                    send_msg(cid, f"📢 {sent}/{len(gs)}")
                return "OK"
            if cmd=="welcome":
                if not args: send_msg(cid, "📝 /welcome متن\nمتغیرها: !mention !firstname !groupname")
                else: kv_set("welcome_text", args); send_msg(cid, "✅ تنظیم شد!")
                return "OK"
            if cmd=="admins" and is_main(uid):
                al="👨‍💼 ادمین‌ها:\n\n"
                if ADMIN_ID: al+=f"👑 اصلی: `{ADMIN_ID}`\n"
                if ADMIN2_ID: al+=f"🌟 دوم: `{ADMIN2_ID}`\n"
                send_msg(cid, al); return "OK"
            if cmd=="panel":
                gs=kv_json("broadcast_groups") or []
                send_msg(cid, f"👨‍💻 پنل ادمین\n📊 گروه‌ها: {len(gs)}\n\n🔧 کامندها:\n/list - لیست دول\n/adddol - اضافه کردن دول\n/broadcast - ارسال همگانی\n/welcome - پیام خوش‌آمد\n/admins - لیست ادمین‌ها")
                return "OK"

        # ── AI Chat (via Hermes) ────────────────────────────────────
        send_action(cid, "typing")
        img = None
        if "photo" in msg:
            pd = dl_file(msg["photo"][-1]["file_id"])
            if pd: img = base64.b64encode(pd).decode()

        # Build reply chain context
        ctx = []; cur = msg
        for _ in range(5):
            rm = cur.get("reply_to_message")
            if not rm: break
            rn = rm.get("from",{}).get("first_name","?")
            rt = (rm.get("text") or rm.get("caption") or "")[:300]
            if "photo" in rm and not img:
                pd = dl_file(rm["photo"][-1]["file_id"])
                if pd: img = base64.b64encode(pd).decode()
                ctx.insert(0, f"[عکس از {rn}]: {rt}")
            elif "voice" in rm: ctx.insert(0, f"[ویس از {rn}]: {rt or '(صوتی)'}")
            else: ctx.insert(0, f"[پیام {rn}]: {rt}")
            cur = rm

        full = text or "این عکس رو توضیح بده"
        if ctx: full = "\n".join(ctx) + f"\n[{name}]: {full}"

        reply = hermes_chat(full, uid, name, img)
        send_msg(cid, reply, mid)

        # Save history
        with lock:
            c=sqlite3.connect(DB)
            c.execute("INSERT INTO chat_history VALUES(?,?,?,?)",(str(cid),"user",full[:500],int(time.time()*1000)))
            c.execute("INSERT INTO chat_history VALUES(?,?,?,?)",(str(cid),"assistant",reply[:500],int(time.time()*1000)))
            c.execute("DELETE FROM chat_history WHERE cid=? AND ts NOT IN (SELECT ts FROM chat_history WHERE cid=? ORDER BY ts DESC LIMIT 40)",(str(cid),str(cid)))
            c.commit(); c.close()

        return "OK"
    except Exception as e: print(f"Error: {e}"); return "OK"

# ─── Dino Game HTML ───────────────────────────────────────────────────
DINO_HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no"><title>Dino</title><style>*{margin:0;padding:0;box-sizing:border-box}body{background:#0f0f23;color:#fff;font-family:system-ui;overflow:hidden;height:100vh;display:flex;align-items:center;justify-content:center}#gc{position:relative;width:100%;max-width:400px;height:100vh;max-height:700px}canvas{width:100%;height:100%;display:block;border-radius:12px}#ov{position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none}#sd{position:absolute;top:20px;right:20px;font-size:24px;font-weight:bold;text-shadow:2px 2px 4px rgba(0,0,0,.8)}#ss,#go{position:absolute;top:0;left:0;right:0;bottom:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:rgba(15,15,35,.9);pointer-events:auto;border-radius:12px}#go{display:none}.t{font-size:32px;margin-bottom:20px}.st{font-size:16px;color:#aaa;margin-bottom:30px}.b{background:linear-gradient(135deg,#667eea,#764ba2);border:none;color:#fff;padding:15px 40px;font-size:18px;border-radius:25px;cursor:pointer}.sxt{font-size:48px;margin:20px 0}.rt{font-size:18px;color:#ffd700;margin:10px 0}</style></head><body><div id="gc"><canvas id="c"></canvas><div id="ov"><div id="sd">0</div><div id="ss"><div class="t">🦕 Dino Runner</div><div class="st">بپر و رد شو!</div><button class="b" id="sb">شروع</button></div><div id="go"><div class="t">💀 Game Over</div><div class="sxt" id="fs">0</div><div class="rt" id="rt"></div><button class="b" id="rb">دوباره</button></div></div></div><script>const x=document.getElementById("c").getContext("2d");let gs="waiting",sc=0,d={x:50,y:0,vy:0,j:false},obs=[],spd=5,fc=0,tk=null,nm="";const B="{{BASE}}";function rz(){const ct=document.getElementById("gc");x.canvas.width=ct.clientWidth*2;x.canvas.height=ct.clientHeight*2;x.scale(2,2)}rz();window.addEventListener("resize",rz);function jp(){if(!d.j){d.vy=-12;d.j=true}}document.addEventListener("keydown",e=>{if(e.code==="Space"||e.code==="ArrowUp"){e.preventDefault();if(gs==="playing")jp()}});x.canvas.addEventListener("touchstart",e=>{e.preventDefault();if(gs==="playing")jp()});x.canvas.addEventListener("click",()=>{if(gs==="playing")jp()});function start(){const p=new URLSearchParams(window.location.search);nm=p.get("name")||"بازیکن";fetch(B+"/api/game/session/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({initData:window.Telegram?.WebApp?.initData||""})}).then(r=>r.json()).then(d=>{tk=d.token;go()}).catch(()=>go())}function go(){gs="playing";sc=0;obs=[];spd=5;fc=0;d.y=0;d.vy=0;d.j=false;document.getElementById("ss").style.display="none";document.getElementById("go").style.display="none"}function die(){gs="over";document.getElementById("go").style.display="flex";document.getElementById("fs").textContent=sc.toLocaleString();if(tk)fetch(B+"/api/game/submit",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:tk,score:sc,initData:window.Telegram?.WebApp?.initData||""})}).then(r=>r.json()).then(d=>{if(d.rank)document.getElementById("rt").textContent="رتبه: #"+d.rank+" از "+d.total}).catch(()=>{})}document.getElementById("sb").onclick=start;document.getElementById("rb").onclick=start;function loop(){requestAnimationFrame(loop);if(gs!=="playing")return;fc++;const W=x.canvas.width/2,H=x.canvas.height/2,G=H-60;x.fillStyle="#0f0f23";x.fillRect(0,0,W,H);x.fillStyle="#333";x.fillRect(0,G,W,3);x.fillStyle="#4ade80";x.fillRect(d.x,G-30+d.y,25,30);x.fillStyle="#fff";x.fillRect(d.x+17,G-25+d.y,4,4);d.vy+=.6;d.y+=d.vy;if(d.y>=0){d.y=0;d.vy=0;d.j=false}if(fc%Math.max(40,90-Math.floor(sc/50))===0)obs.push({x:W,h:25+Math.random()*20});x.fillStyle="#ef4444";for(let i=obs.length-1;i>=0;i--){const o=obs[i];o.x-=spd;x.fillRect(o.x,G-o.h,15,o.h);if(o.x<d.x+25&&o.x+15>d.x&&G-o.h<G-30+d.y+30){die();return}if(o.x<-20)obs.splice(i,1)}sc++;document.getElementById("sd").textContent=sc.toLocaleString();if(fc%100===0)spd=Math.min(15,spd+.5)}loop()</script></body></html>"""

if __name__ == "__main__":
    print(f"🤖 Fariborz Bot v6 on port {BOT_PORT}")
    print(f"   Hermes URL: {HERMES_URL}")
    app.run(host="0.0.0.0", port=BOT_PORT)
