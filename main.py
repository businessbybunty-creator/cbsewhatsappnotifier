import os
import requests
from bs4 import BeautifulSoup
import psycopg2
from twilio.rest import Client
from urllib.parse import urljoin

# Env vars
CBSE_URL = os.environ.get("CBSE_URL", "https://www.cbse.gov.in/cbsenew/cbse.html")
DATABASE_URL = os.environ.get("DATABASE_URL")
TW_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TW_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
FROM_WHATSAPP = os.environ.get("FROM_WHATSAPP")
TO_WHATSAPP = os.environ.get("TO_WHATSAPP")

def init_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS seen_updates (
            id SERIAL PRIMARY KEY,
            title TEXT UNIQUE,
            link TEXT,
            seen_at TIMESTAMP DEFAULT now()
        );
        """)
    conn.commit()
    conn.close()

def seen_before(title):
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM seen_updates WHERE title = %s LIMIT 1;", (title,))
        res = cur.fetchone()
    conn.close()
    return res is not None

def mark_seen(title, link):
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    with conn.cursor() as cur:
        cur.execute("INSERT INTO seen_updates (title, link) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (title, link))
    conn.commit()
    conn.close()

def get_latest_update():
    r = requests.get(CBSE_URL, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    anchors = soup.find_all("a")
    if not anchors:
        return None, None
    a = anchors[0]
    title = a.get_text(strip=True)
    href = a.get("href", "")
    link = href if href.startswith("http") else urljoin(CBSE_URL, href)
    return title, link

def send_whatsapp(body):
    client = Client(TW_SID, TW_TOKEN)
    return client.messages.create(body=body, from_=FROM_WHATSAPP, to=TO_WHATSAPP).sid

def main():
    init_db()
    title, link = get_latest_update()
    if not title:
        print("No updates found.")
        return
    if seen_before(title):
        print("Already seen:", title)
        return
    message = f"📢 New CBSE Update:\n{title}\n🔗 {link}"
    sid = send_whatsapp(message)
    print("WhatsApp sent, SID:", sid)
    mark_seen(title, link)

if __name__ == "__main__":
    main()
