import imaplib
import email
import time
import requests
import os
import threading
import random
import string
from email.header import decode_header
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============ CONFIG ============
EMAIL = os.environ.get("EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OWNER_CHAT_ID = os.environ.get("CHAT_ID")

# ============ STATE ============
seen_ids = set()
authorized_users = set()
pending_otp = {}
last_update_id = 0

# ============ Web Server ============
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, *args):
        pass

def run_server():
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ============ Telegram ============
def send_message(chat_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print(f"Telegram Error: {e}")

def send_to_owner(message):
    send_message(OWNER_CHAT_ID, message)

# ============ OTP ============
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

# ============ Commands ============
def get_updates():
    global last_update_id
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url, params={
            "offset": last_update_id + 1,
            "timeout": 10
        })
        data = res.json()
        updates = data.get("result", [])

        for update in updates:
            last_update_id = update["update_id"]
            message = update.get("message", {})
            chat_id = str(message.get("chat", {}).get("id", ""))
            text = message.get("text", "")

            if not chat_id or not text:
                continue

            # /start
            if text == "/start":
                if chat_id == str(OWNER_CHAT_ID):
                    authorized_users.add(chat_id)
                    send_message(chat_id,
                        "✅ <b>Bot Online আছে!</b>\n\n"
                        "📧 Gmail connected\n"
                        "🔔 নতুন mail আসলে এখানে দেখাবে"
                    )
                else:
                    otp = generate_otp()
                    pending_otp[chat_id] = otp
                    send_message(chat_id,
                        "🔐 <b>Authorization দরকার!</b>\n\n"
                        "Owner-কে বলো OTP দিতে।\n"
                        "OTP পেলে এখানে পাঠাও।"
                    )
                    send_to_owner(
                        f"⚠️ <b>নতুন Login Request!</b>\n\n"
                        f"Chat ID: <code>{chat_id}</code>\n"
                        f"🔑 OTP: <b>{otp}</b>\n\n"
                        f"তোমার হলে OTP দাও, না হলে ignore করো।"
                    )

            # OTP verify
            elif chat_id in pending_otp:
                if text.strip() == pending_otp[chat_id]:
                    authorized_users.add(chat_id)
                    del pending_otp[chat_id]
                    send_message(chat_id,
                        "✅ <b>Access দেওয়া হয়েছে!</b>\n\n"
                        "এখন থেকে নতুন mail এখানে আসবে। 📧"
                    )
                    send_to_owner(f"✅ Chat ID <code>{chat_id}</code> কে access দেওয়া হয়েছে।")
                else:
                    send_message(chat_id, "❌ ভুল OTP! আবার চেষ্টা করো।")

    except Exception as e:
        print(f"Update Error: {e}")

# ============ Email Check ============
def check_email():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, APP_PASSWORD)
        mail.select("inbox")

        _, messages = mail.search(None, "ALL")
        all_ids = messages[0].split()

        # শুধু নতুন IDs
        new_ids = [i for i in all_ids if i not in seen_ids]

        if not new_ids:
            print("📭 কোনো নতুন mail নেই")
            mail.logout()
            return

        for num in new_ids:
            seen_ids.add(num)

            _, msg_data = mail.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            raw_subject = decode_header(msg["Subject"])[0]
            subject, enc = raw_subject
            if isinstance(subject, bytes):
                subject = subject.decode(enc or "utf-8", errors="ignore")

            sender = msg.get("From", "Unknown")

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                        except:
                            pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode(errors="ignore")
                except:
                    pass

            if len(body) > 300:
                body = body[:300] + "..."

            text = f"""
📧 <b>নতুন Email!</b>

👤 <b>From:</b> {sender}
📌 <b>Subject:</b> {subject}

💬 <b>Message:</b>
{body}
            """
            for user_id in authorized_users:
                send_message(user_id, text)
            print(f"✅ Mail পাঠানো: {subject}")

        mail.logout()

    except Exception as e:
        print(f"❌ Email Error: {e}")

# ============ STARTUP ============
print("✅ Bot চালু হয়েছে!")
authorized_users.add(str(OWNER_CHAT_ID))

# পুরনো mail skip
try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL, APP_PASSWORD)
    mail.select("inbox")
    _, messages = mail.search(None, "ALL")
    if messages[0]:
        for i in messages[0].split():
            seen_ids.add(i)
    mail.logout()
    print(f"📬 {len(seen_ids)}টা পুরনো mail skip করা হয়েছে")
except Exception as e:
    print(f"Startup Error: {e}")

send_to_owner("✅ <b>Gmail Bot চালু হয়েছে!</b>\n\n/start দিয়ে status check করো।")

# ============ MAIN LOOP ============
while True:
    get_updates()
    check_email()
    time.sleep(30)
