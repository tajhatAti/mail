import imaplib
import email
import time
import requests
import os
import threading
from email.header import decode_header
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone

EMAIL = os.environ.get("EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# আগে যে mail IDs পাঠানো হয়েছে সেগুলো মনে রাখবে
seen_ids = set()

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

def check_email():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, APP_PASSWORD)
        mail.select("inbox")

        # সব mail খোঁজো
        _, messages = mail.search(None, "ALL")
        all_ids = messages[0].split()

        # শুধু নতুন IDs (seen_ids-এ নেই এমন)
        new_ids = [i for i in all_ids if i not in seen_ids]

        for num in new_ids:
            seen_ids.add(num)  # মনে রাখো

            # প্রথমবার চালু হলে পুরনো mail skip করো
            if len(seen_ids) == len(all_ids) and len(new_ids) == len(all_ids):
                print("🔄 First run — পুরনো mail skip করছি")
                break

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
            send_telegram(text)
            print(f"✅ Mail পাঠানো হয়েছে: {subject}")

        mail.logout()

    except Exception as e:
        print(f"❌ Error: {e}")
        send_telegram(f"⚠️ Bot Error: {e}")

print("✅ Bot চালু হয়েছে!")
send_telegram("✅ Gmail Bot চালু হয়েছে!")

# প্রথম run-এ সব পুরনো mail seen_ids-এ ভরো
try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL, APP_PASSWORD)
    mail.select("inbox")
    _, messages = mail.search(None, "ALL")
    for i in messages[0].split():
        seen_ids.add(i)
    mail.logout()
    print(f"📬 {len(seen_ids)}টা পুরনো mail skip করা হয়েছে")
except:
    pass

while True:
    check_email()
    time.sleep(30)
