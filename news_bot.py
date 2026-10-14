import os
import sqlite3
import urllib.parse
import feedparser
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

KEYWORDS = ["Posorja", "El Morro", "Progreso", "Chongón", "Chongon", "Cerecita", "Vía a Playas", "Vía a la Costa"]

FACEBOOK_FEEDS = [
    {
        "nombre": "RD NOTICIAS ECUADOR",
        "url": "https://fetchrss.com/feed/1xH4z8ASAFsI1xH4gKDzrEj5.rss1",
    },
    {
        "nombre": "NOTICIAS POSORJA 1",
        "url": "https://fetchrss.com/feed/1xH4z8ASAFsI1xH5AI46cDjO.rss",
    },
    {
        "nombre": "NOTICIAS POSORJA 2",
        "url": "https://fetchrss.com/feed/1xH4z8ASAFsI1xH5CjArF558.rss",
    },
    {
        "nombre": "NOTICIAS POSORJA 3",
        "url": "https://fetchrss.com/feed/1xH4z8ASAFsI1xH5Fe3Og78N.rss",
    },
]
# Base de datos SQLite local
conn = sqlite3.connect("noticias.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS enviadas (link TEXT PRIMARY KEY)")
conn.commit()


def ya_enviada(link):
    cursor.execute("SELECT 1 FROM enviadas WHERE link = ?", (link,))
    return cursor.fetchone() is not None


def registrar_enviada(link):
    cursor.execute("INSERT INTO enviadas VALUES (?)", (link,))
    conn.commit()


def enviar_telegram(mensaje):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Error: Faltan las variables TELEGRAM_TOKEN o CHAT_ID.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        res = requests.post(url, data=payload)
        print(f"Respuesta de Telegram: {res.status_code}")
    except Exception as e:
        print(f"Error enviando mensaje: {e}")


def buscar_noticias_google():
    """Busca noticias generales en Google News"""
    for kw in KEYWORDS:
        query = urllib.parse.quote(f"{kw} Ecuador")
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=es-419&gl=EC&ceid=EC:es-419"

        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            link = entry.link
            title = entry.title

            if not ya_enviada(link):
                mensaje = (
                    f"📰 <b>Noticia en Prensa ({kw.capitalize()})</b>\n\n"
                    f"{title}\n\n"
                    f"🔗 <a href='{link}'>Leer en el medio original</a>"
                )
                enviar_telegram(mensaje)
                registrar_enviada(link)


def buscar_noticias_facebook():
    """Busca publicaciones en las páginas públicas de Facebook configuradas"""
    for fb in FACEBOOK_FEEDS:
        if "PEGA_AQUI" in fb["url"]:
            continue  # Salta si no has puesto una URL válida aún

        feed = feedparser.parse(fb["url"])
        for entry in feed.entries:
            link = entry.link
            # Tomamos los primeros 250 caracteres del post para el resumen
            contenido = (
                entry.get("summary", entry.get("title", ""))[:250] + "..."
            )

            if not ya_enviada(link):
                mensaje = (
                    f"🔵 <b>Publicación en Facebook ({fb['nombre']})</b>\n\n"
                    f"{contenido}\n\n"
                    f"🔗 <a href='{link}'>Ver publicación en Facebook</a>"
                )
                enviar_telegram(mensaje)
                registrar_enviada(link)


if __name__ == "__main__":
    print("Iniciando búsqueda de noticias...")
    buscar_noticias_google()
    buscar_noticias_facebook()
    print("Búsqueda finalizada.")
