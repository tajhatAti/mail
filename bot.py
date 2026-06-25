import imaplib
import email
import time
import requests
import os
from email.header import decode_header

# Config (Environment variable থেকে নেবে)
EMAIL = os.environ.get("EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    })

def check_email():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL, APP_PASSWORD)
    mail.select("inbox")
    
    # Unseen mail খোঁজো
    _, messages = mail.search(None, "UNSEEN")
    
    for num in messages[0].split():
        _, msg_data = mail.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        
        # Subject decode
        subject, enc = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(enc or "utf-8")
        
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
