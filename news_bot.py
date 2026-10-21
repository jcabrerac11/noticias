import os
import sqlite3
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
import feedparser
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Sectores principales de la zona de cobertura
SECTORES_PRINCIPALES = [
    "posorja",
    "el morro",
    "progreso",
    "chongón",
    "chongon",
    "cerecita",
    "vía a playas",
    "via a playas",
    "vía a la costa",
    "via a la costa",
]

# Recintos y barrios (nombres comunes que requieren confirmación de provincia/zona)
RECINTOS_SECUNDARIOS = [
    "ciudad de dios",
    "san isidro",
    "san antonio",
    "safando",
    "san lorenzo",
    "vía a san juan",
    "via a san juan",
    "vía a san antonio",
    "via a san antonio",
]

KEYWORDS = SECTORES_PRINCIPALES + RECINTOS_SECUNDARIOS

# Palabras clave de control para confirmar que es de Ecuador / Guayas
CONTEXTO_ECUADOR = ["ecuador", "guayas", "guayaquil", "playas"]

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
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS noticias_detalles (
    link TEXT PRIMARY KEY,
    titulo TEXT,
    fecha TEXT
)
"""
)
cursor.execute("CREATE TABLE IF NOT EXISTS enviadas (link TEXT PRIMARY KEY)")
conn.commit()


def ya_enviada(link):
    cursor.execute("SELECT 1 FROM enviadas WHERE link = ?", (link,))
    return cursor.fetchone() is not None


def registrar_noticia_completa(link, titulo):
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "INSERT OR IGNORE INTO noticias_detalles VALUES (?, ?, ?)",
        (link, titulo, fecha_actual),
    )
    cursor.execute("INSERT OR IGNORE INTO enviadas VALUES (?)", (link,))
    conn.commit()


def registrar_enviada(link):
    cursor.execute("INSERT OR IGNORE INTO enviadas VALUES (?)", (link,))
    conn.commit()


def es_de_ubicacion_interes(texto):
    """Filtra noticias asegurando que correspondan a la zona objetivo en Ecuador/Guayas."""
    texto_lc = texto.lower()

    # 1. Comprobar si menciona alguno de los sectores principales
    tiene_sector_principal = any(
        sp in texto_lc for sp in SECTORES_PRINCIPALES
    )

    # 2. Comprobar si menciona algún recinto de nombre común
    tiene_recinto = any(rec in texto_lc for rec in RECINTOS_SECUNDARIOS)

    # 3. Comprobar contexto nacional/provincial
    tiene_contexto_local = any(ctx in texto_lc for ctx in CONTEXTO_ECUADOR)

    # Regla A: Si menciona un sector principal Y tiene contexto de Ecuador/Guayas -> VÁLIDO
    if tiene_sector_principal and tiene_contexto_local:
        return True

    # Regla B: Si menciona un recinto común (ej. San Antonio), debe mencionar también Guayas/Ecuador o la zona
    if tiene_recinto and (tiene_contexto_local or tiene_sector_principal):
        return True

    return False


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


def es_noticia_reciente(published_parsed, horas_maximas=24):
    """Verifica si la noticia fue publicada dentro de las últimas 24 horas."""
    if not published_parsed:
        return True

    fecha_noticia = datetime.fromtimestamp(
        time.mktime(published_parsed), tz=timezone.utc
    )
    fecha_limite = datetime.now(timezone.utc) - timedelta(hours=horas_maximas)

    return fecha_noticia >= fecha_limite


def buscar_noticias_google():
    """Busca noticias en Google News con filtro exacto de ubicación en Guayas/Ecuador."""
    for kw in KEYWORDS:
        # Búsqueda estructurada exigiendo la palabra exacta + contexto geográfico de Ecuador
        query = urllib.parse.quote(f'"{kw}" (Guayas OR Guayaquil OR Ecuador) when:1d')
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=es-419&gl=EC&ceid=EC:es-419"

        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            link = entry.link
            title = entry.title
            summary = entry.get("summary", "")
            published_parsed = entry.get("published_parsed")

            texto_completo = f"{title} {summary}"

            if not ya_enviada(link):
                if es_noticia_reciente(
                    published_parsed, horas_maximas=24
                ) and es_de_ubicacion_interes(texto_completo):
                    mensaje = (
                        f"📰 <b>Noticia en Prensa ({kw.title()})</b>\n\n"
                        f"{title}\n\n"
                        f"🔗 <a href='{link}'>Leer en el medio original</a>"
                    )
                    enviar_telegram(mensaje)
                else:
                    print(
                        f"🚫 Descartada noticia irrelevante o fuera de zona: {title}"
                    )

                registrar_noticia_completa(link, title)


def buscar_noticias_facebook():
    """Busca publicaciones recientes en Facebook restringidas a la zona."""
    for fb in FACEBOOK_FEEDS:
        if "PEGA_AQUI" in fb["url"]:
            continue

        feed = feedparser.parse(fb["url"])
        for entry in fb.entries if hasattr(fb, 'entries') else feed.entries:
            link = entry.link
            contenido = (
                entry.get("summary", entry.get("title", ""))[:250] + "..."
            )
            published_parsed = entry.get("published_parsed")

            if not ya_enviada(link):
                if es_noticia_reciente(
                    published_parsed, horas_maximas=24
                ) and es_de_ubicacion_interes(contenido):
                    mensaje = (
                        f"🔵 <b>Publicación en Facebook ({fb['nombre']})</b>\n\n"
                        f"{contenido}\n\n"
                        f"🔗 <a href='{link}'>Ver publicación en Facebook</a>"
                    )
                    enviar_telegram(mensaje)
                registrar_noticia_completa(
                    link, f"Facebook ({fb['nombre']}): {contenido[:50]}"
                )


def buscar_noticias_youtube():
    """Busca transmisiones y reportajes de YouTube filtrados por zona."""
    for kw in KEYWORDS:
        query = urllib.parse.quote(
            f'site:youtube.com "{kw}" (Guayas OR Ecuador) when:1d'
        )
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=es-419&gl=EC&ceid=EC:es-419"

        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            link = entry.link
            title = entry.title
            published_parsed = entry.get("published_parsed")

            if not ya_enviada(link):
                if es_noticia_reciente(
                    published_parsed, horas_maximas=24
                ) and es_de_ubicacion_interes(title):
                    mensaje = (
                        f"🔴 <b>Video / Transmisión YouTube ({kw.title()})</b>\n\n"
                        f"{title}\n\n"
                        f"🎬 <a href='{link}'>Ver en YouTube</a>"
                    )
                    enviar_telegram(mensaje)

                registrar_noticia_completa(link, f"YouTube: {title[:60]}")


if __name__ == "__main__":
    print("Iniciando búsqueda de noticias filtradas por ubicación exacta...")
    buscar_noticias_google()
    buscar_noticias_facebook()
    buscar_noticias_youtube()
    print("Búsqueda finalizada.")
