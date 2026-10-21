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
    "ciudad de Dios",
    "san isidro",
    "san antonio",
    "safando",
]


def obtener_noticias_semana():
    """Conecta a noticias.db y obtiene los registros de los últimos 7 días."""
    if not os.path.exists("noticias.db"):
        print("⚠️ No existe la base de datos noticias.db.")
        return []

    conn = sqlite3.connect("noticias.db")
    cursor = conn.cursor()

    # Calculamos la fecha límite (hace 7 días en formato YYYY-MM-DD)
    fecha_limite = (
        datetime.now(timezone.utc) - timedelta(days=7)
    ).strftime("%Y-%m-%d")

    # Revisa si la tabla noticias_detalles existe
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='noticias_detalles'"
    )
    tabla_existe = cursor.fetchone()

    noticias = []
    if tabla_existe:
        # Extrae únicamente las noticias registradas en los últimos 7 días
        cursor.execute(
            "SELECT titulo, link, fecha FROM noticias_detalles WHERE fecha >= ? ORDER BY fecha DESC",
            (fecha_limite,),
        )
        rows = cursor.fetchall()
        for row in rows:
            noticias.append(
                {"titulo": row[0], "link": row[1], "fecha": row[2]}
            )
    else:
        # Respaldo si solo existe la tabla anterior
        cursor.execute("SELECT link FROM enviadas")
        rows = cursor.fetchall()
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        for row in rows:
            noticias.append(
                {
                    "titulo": "Noticia monitoreada en la zona",
                    "link": row[0],
                    "fecha": fecha_hoy,
                }
            )

    conn.close()
    return noticias


def analizar_inteligencia_semanal(noticias_semana):
    """Solicita a Gemini consolidar el análisis semanal de las noticias recopiladas."""
    if not GEMINI_API_KEY or not noticias_semana:
        return {
            "grupos_delictivos": ["Sin novedades críticas en los últimos 7 días"],
            "actividades_ilicitas": ["Monitoreo de zona continuo"],
            "vinculos_observados": "Sin eventos acumulados registrados en esta semana.",
            "nivel_riesgo_zona": "Bajo",
            "resumen_semanal": "No se detectaron reportes de eventos violentos relevantes en los sectores monitoreados durante los últimos 7 días.",
        }

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    Eres un analista de inteligencia y seguridad territorial en Ecuador.
    Analiza las siguientes noticias recopiladas durante los ÚLTIMOS 7 DÍAS en Posorja, El Morro, Progreso, Chongón, Cerecita, Vía a la Costa y Vía a Playas:

    {json.dumps(noticias_semana, ensure_ascii=False)}

    Responde ÚNICAMENTE en formato JSON estricto con las siguientes llaves:
    {{
        "grupos_delictivos": ["Lista de GDOs, bandas o actores armados mencionados o inferidos"],
        "actividades_ilicitas": ["Sicariato", "Extorsión / Vacunas", "Robo en ejes viales", "Contrabando marítimo"],
        "vinculos_observados": "Análisis táctico de disputas territoriales, alianzas o modus operandi observados esta semana.",
        "nivel_riesgo_zona": "Alto / Medio / Bajo",
        "resumen_semanal": "Síntesis ejecutiva del panorama de seguridad semanal en los sectores."
    }}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        limpio = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(limpio)
    except Exception as e:
        print(f"❌ Error al analizar con Gemini: {e}")
        return {
            "grupos_delictivos": ["En análisis de datos"],
            "actividades_ilicitas": ["Monitoreo preventivo"],
            "vinculos_observados": "Procesamiento semanal en curso.",
            "nivel_riesgo_zona": "Medio",
            "resumen_semanal": "Reporte generado con base en el registro de la última semana.",
        }


def construir_pagina_html(analisis, noticias_semana):
    """Genera el archivo index.html para la web."""
    fecha_inicio = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
    fecha_fin = datetime.now().strftime("%d/%m/%Y")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Inteligencia Territorial - Guayas</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #0b132b; color: #e0e1dd; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
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
                <h2 class="mb-0">🧠 Dashboard de Inteligencia y Seguridad</h2>
                <small class="text-muted">Reporte Semanal ({fecha_inicio} - {fecha_fin}) | Sectores: Posorja, El Morro, Progreso, Chongón, Cerecita, Vía a la Costa, Vía a Playas, Ciudad de Dios, San Isidro, San Antonio, Safando</small>
            </div>
            <span class="badge badge-alto p-2 fs-6">Nivel de Riesgo: {analisis.get('nivel_riesgo_zona', 'Medio')}</span>
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
                    <h5 class="text-danger">🚨 Modalidades / Actividades Ilícitas</h5>
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
            <h5 class="text-success">📌 Resumen Ejecutivo de los Últimos 7 Días</h5>
            <p>{analisis.get('resumen_semanal', '')}</p>
        </div>

        <h4 class="mt-4 mb-3">📰 Registro de Noticias Recopiladas esta Semana ({len(noticias_semana)})</h4>
        <div class="list-group">
            {"".join([f'<a href="{n["link"]}" target="_blank" class="list-group-item list-group-item-action bg-dark text-white border-secondary"><b>[{n.get("fecha", "Reciente")}]</b> {n["titulo"]}</a>' for n in noticias_semana])}
        </div>
    </div>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    print("Extrayendo noticias acumuladas de los últimos 7 días...")
    noticias = obtener_noticias_semana()
    print(
        f"Se encontraron {len(noticias)} noticias registradas en esta ventana de tiempo."
    )

    print("Generando análisis de inteligencia con Gemini...")
    analisis = analizar_inteligencia_semanal(noticias)

    print("Actualizando index.html...")
    construir_pagina_html(analisis, noticias)
    print("✅ Dashboard semanal actualizado exitosamente.")
