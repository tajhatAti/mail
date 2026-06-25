import imaplib
import email
import time
import requests
import os
import threading
from email.header import decode_header
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============ CONFIG ============
EMAIL = os.environ.get("EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
# ================================

# ---- Web Server (Render sleep থেকে বাঁচাতে) ----
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

# ---- Telegram Message পাঠানো ----
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print(f"Telegram Error: {e}")

# ---- Email Check ----
def check_email():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, APP_PASSWORD)
        mail.select("inbox")

        _, messages = mail.search(None, "UNSEEN")

        if messages[0]:
            for num in messages[0].split():
                _, msg_data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                # Subject decode
                raw_subject = decode_header(msg["Subject"])[0]
                subject, enc = raw_subject
                if isinstance(subject, bytes):
                    subject = subject.decode(enc or "utf-8", errors="ignore")

                # Sender
                sender = msg.get("From", "Unknown")

                # Body বের করা
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

                # Body ৩০০ character-এর বেশি হলে কেটে দাও
                if len(body) > 300:
                    body = body[:300] + "..."

                text = f"""
📧 <b>নতুন Email!</b>

👤 <b>From:</b> {sender}
📌 <b>Subject:</b> {subject}

💬 <b>Message:</b>
{body}
                """
                send_telegram(text)
                print(f"✅ Mail পাঠানো হয়েছে: {subject}")
        else:
            print("📭 কোনো নতুন mail নেই")

        mail.logout()

    except Exception as e:
        print(f"❌ Email Error: {e}")
        send_telegram(f"⚠️ Bot Error: {e}")

# ---- Main Loop ----
print("✅ Bot চালু হয়েছে!")
send_telegram("✅ Gmail Bot চালু হয়েছে! এখন থেকে নতুন mail আসলে এখানে দেখাবে।")

while True:
    check_email()
    time.sleep(30)            subject = subject.decode(enc or "utf-8")
        
        sender = msg["From"]
        
        text = f"""
📧 <b>নতুন Email এসেছে!</b>

👤 <b>From:</b> {sender}
📌 <b>Subject:</b> {subject}
        """
        send_telegram(text)
    
    mail.logout()

print("✅ Bot চালু হয়েছে...")
while True:
    try:
        check_email()
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(60)  # প্রতি ৬০ সেকেন্ডে check করবে
