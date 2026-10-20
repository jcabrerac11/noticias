import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Coordenadas y sectores objetivo
SECTORES = [
    "posorja",
    "el morro",
    "progreso",
    "chongón",
    "chongon",
    "cerecita",
    "vía a la costa",
    "via a la costa",
    "vía a playas",
    "via a playas",
]


def obtener_noticias_semana():
    """Conecta a noticias.db y obtiene los registros de los últimos 7 días."""
    if not os.path.exists("noticias.db"):
        print("⚠️ No existe la base de datos noticias.db.")
        return []

    conn = sqlite3.connect("noticias.db")
    cursor = conn.cursor()

    # Verificar si la tabla noticias existe (si usas una tabla estructurada)
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='noticias_detalles'"
    )
    tabla_existe = cursor.fetchone()

    noticias = []

    if tabla_existe:
        # Si tienes una tabla con fecha y título
        limite = (datetime.now(timezone.utc) - timedelta(days=7)).strftime(
            "%Y-%m-%d"
        )
        cursor.execute(
            "SELECT titulo, link, fecha FROM noticias_detalles WHERE fecha >= ?",
            (limite,),
        )
        rows = cursor.fetchall()
        for row in rows:
            noticias.append({"titulo": row[0], "link": row[1], "fecha": row[2]})
    else:
        # Si solo tienes la tabla de enlaces enviados, leemos los enlaces registrados
        cursor.execute("SELECT link FROM enviadas")
        rows = cursor.fetchall()
        for row in rows:
            noticias.append(
                {
                    "titulo": "Noticia monitoreada en la zona",
                    "link": row[0],
                    "fecha": datetime.now().strftime("%Y-%m-%d"),
                }
            )

    conn.close()
    return noticias


def analizar_inteligencia_semanal(noticias_semana):
    """Llama a Gemini para consolidar las noticias y estructurar la inteligencia delictiva."""
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY no configurado.")
        return {
            "grupos_delictivos": ["En identificación"],
            "actividades_ilicitas": ["Sucesos bajo monitoreo"],
            "vinculos_observados": "Sin clave de API configurada.",
            "nivel_riesgo_zona": "Medio",
            "resumen_semanal": "Monitoreo automatizado en curso.",
        }

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    Eres un analista de inteligencia militar/policial en Ecuador.
    Analiza la lista de eventos y noticias recopiladas durante la última semana en los sectores de Posorja, El Morro, Progreso, Chongón, Cerecita, Vía a la Costa y Vía a Playas:

    {json.dumps(noticias_semana, ensure_ascii=False)}

    Responde ÚNICAMENTE en formato JSON válido con las siguientes llaves exactas:
    {{
        "grupos_delictivos": ["Nombre de GDO o grupo 1", "Grupo 2"],
        "actividades_ilicitas": ["Sicariato", "Extorsión", "Robo en ejes viales", "Contrabando marítimo"],
        "vinculos_observados": "Explicación breve de alianzas, disputas de territorio o modus operandi en estos sectores.",
        "nivel_riesgo_zona": "Alto / Medio / Bajo",
        "resumen_semanal": "Síntesis ejecutiva de la situación de seguridad en la zona durante los últimos 7 días."
    }}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        limpio = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(limpio)
    except Exception as e:
        print(f"❌ Error analizando con Gemini: {e}")
        return {
            "grupos_delictivos": ["Información en análisis"],
            "actividades_ilicitas": ["Delitos contra la propiedad y personas"],
            "vinculos_observados": "Procesamiento automático semanal.",
            "nivel_riesgo_zona": "Medio",
            "resumen_semanal": "Reporte generado sin respuesta estructurada de IA.",
        }


def construir_pagina_html(analisis, noticias_semana):
    """Crea el archivo index.html para GitHub Pages."""
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Inteligencia Territorial</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #0b132b; color: #e0e1dd; font-family: 'Segoe UI', Tahoma, sans-serif; }}
        .card-custom {{ background-color: #1c2541; border: 1px solid #3a506b; border-radius: 8px; margin-bottom: 20px; }}
        .badge-alto {{ background-color: #d90429; color: white; }}
        .badge-medio {{ background-color: #f77f00; color: white; }}
        .badge-bajo {{ background-color: #38b000; color: white; }}
    </style>
</head>
<body>
    <div class="container py-4">
        <div class="d-flex justify-content-between align-items-center mb-4 border-bottom border-secondary pb-3">
            <div>
                <h2 class="mb-0">🧠 Dashboard de Inteligencia Territorial</h2>
                <small class="text-muted">Sectores: Posorja | El Morro | Progreso | Chongón | Cerecita | Vía a la Costa | Vía a Playas</small>
            </div>
            <span class="badge badge-alto p-2 fs-6">Riesgo: {analisis.get('nivel_riesgo_zona', 'Medio')}</span>
        </div>

        <div class="row">
            <div class="col-md-6">
                <div class="card card-custom p-3">
                    <h5 class="text-warning">⚠️ Grupos Delictivos (GDOs) Monitoreados</h5>
                    <ul>
                        {"".join([f"<li><b>{g}</b></li>" for g in analisis.get('grupos_delictivos', [])])}
                    </ul>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card card-custom p-3">
                    <h5 class="text-danger">🚨 Modalidades y Actividades Ilícitas</h5>
                    <ul>
                        {"".join([f"<li>{a}</li>" for a in analisis.get('actividades_ilicitas', [])])}
                    </ul>
                </div>
            </div>
        </div>

        <div class="card card-custom p-3">
            <h5 class="text-info">🔗 Análisis de Vínculos y Dinámica Territorial</h5>
            <p>{analisis.get('vinculos_observados', '')}</p>
        </div>

        <div class="card card-custom p-3">
            <h5 class="text-success">📌 Resumen Ejecutivo Semanal</h5>
            <p>{analisis.get('resumen_semanal', '')}</p>
        </div>

        <h4 class="mt-4 mb-3">📰 Registro de Noticias Semanales ({len(noticias_semana)})</h4>
        <div class="list-group">
            {"".join([f'<a href="{n["link"]}" target="_blank" class="list-group-item list-group-item-action bg-dark text-white border-secondary"><b>[{n.get("fecha", "Reciente")}]</b> {n["titulo"]}</a>' for n in noticias_semana])}
        </div>
    </div>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ index.html generado con éxito.")


if __name__ == "__main__":
    print("Leyendo noticias de la base de datos...")
    noticias = obtener_noticias_semana()
    print(f"Total de noticias procesadas: {len(noticias)}")

    print("Generando análisis de inteligencia con Gemini...")
    analisis = analizar_inteligencia_semanal(noticias)

    print("Construyendo página web...")
    construir_pagina_html(analisis, noticias)
    print("Proceso finalizado.")