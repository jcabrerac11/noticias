import os
import sqlite3
import urllib.parse
import feedparser
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

KEYWORDS = ["posorja", "el morro", "progreso", "chongón", "chongon"]

conn = sqlite3.connect("noticias.db")
cursor = conn.cursor()
cursor.execute(
    "CREATE TABLE IF NOT EXISTS enviadas (link TEXT PRIMARY KEY)"
)
conn.commit()


def ya_enviada(link):
    cursor.execute("SELECT 1 FROM enviadas WHERE link = ?", (link,))
    return cursor.fetchone() is not None


def registrar_enviada(link):
    cursor.execute("INSERT INTO enviadas VALUES (?)", (link,))
    conn.commit()


def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Error: Faltan las variables TELEGRAM_TOKEN o CHAT_ID.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    requests.post(url, data=payload)


def buscar_noticias():
    for kw in KEYWORDS:
        query = urllib.parse.quote(f"{kw} Ecuador")
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=es-419&gl=EC&ceid=EC:es-419"

        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            link = entry.link
            title = entry.title

            if not ya_enviada(link):
                mensaje = (
                    f"📰 <b>Nueva Noticia ({kw.capitalize()})</b>\n\n"
                    f"{title}\n\n"
                    f"🔗 <a href='{link}'>Leer noticia completa</a>"
                )
                enviar_telegram(mensaje)
                registrar_enviada(link)


if __name__ == "__main__":
    buscar_noticias()
