import io
import os
import sqlite3
import urllib.request
from datetime import datetime
import docx
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt, RGBColor
from google import genai
import requests

# 1. Variables de entorno desde GitHub Secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Coordenadas de referencia por sector
COORDENADAS_SECTORES = {
    "posorja": "-2.7061, -80.2464",
    "el morro": "-2.6231, -80.3128",
    "progreso": "-2.3922, -80.3789",
    "chongon": "-2.2483, -80.0811",
    "chongón": "-2.2483, -80.0811",
    "cerecita": "-2.333426, -80270089",
    "ciudad de dios": "-2.074946, -80.004669",
    "san isidro": "-2.348605, -80.277402",
    "san antonio": "-2.532686, -80.391087",
    "safando": "-2.395041, -80.214882",
}


# 2. Tu función para enviar el archivo .docx a Telegram
def enviar_documento_telegram(ruta_archivo, descripcion):
    """Envía un archivo .docx al chat de Telegram"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Error: Faltan las variables TELEGRAM_TOKEN o CHAT_ID.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"

    try:
        with open(ruta_archivo, "rb") as doc:
            files = {"document": doc}
            data = {
                "chat_id": CHAT_ID,
                "caption": descripcion,
                "parse_mode": "HTML",
            }
            res = requests.post(url, data=data, files=files)
            print(f"Respuesta envío documento a Telegram: {res.status_code}")
    except Exception as e:
        print(f"❌ Error al enviar documento: {e}")


def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def extraer_datos_evento(titulo, resumen, sector):
    if not GEMINI_API_KEY:
        return {
            "lugar": sector.capitalize(),
            "tipo_hecho": "Muerte Violenta / Homicidio",
            "victimas": "Por determinar",
            "posible_móvil": "En investigación",
            "resumen_ejecutivo": f"{titulo}. {resumen}",
            "coordenadas": COORDENADAS_SECTORES.get(
                sector.lower(), "-2.1962, -79.8862"
            ),
        }

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    Analiza la siguiente noticia de un presunto homicidio o muerte violenta en Ecuador:
    TITULAR: {titulo}
    CONTENIDO: {resumen}
    SECTOR: {sector}

    Extrae en formato exacto:
    LUGAR_EXACTO: (Dirección o barrio en {sector})
    TIPO_HECHO: (Homicidio intencional / Sicariato / Femicidio / Encontrado sin vida)
    VICTIMAS: (Número de víctimas o detalles)
    POSIBLE_MOVIL: (Ajuste de cuentas, robo, violencia, o En investigación)
    RESUMEN_EJECUTIVO: (Síntesis técnica del suceso en máximo 3 oraciones)
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        raw_text = response.text
        data = {
            "lugar": f"{sector.capitalize()}, Guayas",
            "tipo_hecho": "Homicidio Intencional",
            "victimas": "1 persona",
            "posible_móvil": "En investigación",
            "resumen_ejecutivo": resumen,
            "coordenadas": COORDENADAS_SECTORES.get(
                sector.lower(), "-2.1962, -79.8862"
            ),
        }
        for line in raw_text.split("\n"):
            if line.startswith("LUGAR_EXACTO:"):
                data["lugar"] = line.replace("LUGAR_EXACTO:", "").strip()
            elif line.startswith("TIPO_HECHO:"):
                data["tipo_hecho"] = line.replace("TIPO_HECHO:", "").strip()
            elif line.startswith("VICTIMAS:"):
                data["victimas"] = line.replace("VICTIMAS:", "").strip()
            elif line.startswith("POSIBLE_MOVIL:"):
                data["posible_móvil"] = line.replace(
                    "POSIBLE_MOVIL:", ""
                ).strip()
            elif line.startswith("RESUMEN_EJECUTIVO:"):
                data["resumen_ejecutivo"] = line.replace(
                    "RESUMEN_EJECUTIVO:", ""
                ).strip()
        return data
    except Exception as e:
        print(f"Error procesando con Gemini: {e}")
        return {
            "lugar": sector.capitalize(),
            "tipo_hecho": "Homicidio Intencional",
            "victimas": "1",
            "posible_móvil": "En investigación",
            "resumen_ejecutivo": titulo,
            "coordenadas": COORDENADAS_SECTORES.get(
                sector.lower(), "-2.1962, -79.8862"
            ),
        }


def crear_boletin_word(noticias_violentas, output_filename="boletin_diario.docx"):
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("BOLETÍN DE INTELIGENCIA DE SEGURIDAD")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(18)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(180, 0, 0)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run(
        f"REPORTE ESPECIAL: HOMICIDIOS INTENCIONALES Y MUERTES VIOLENTAS\n"
        f"FECHA DE EMISIÓN: {datetime.now().strftime('%d/%m/%Y')}"
    )
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(10)
    run_sub.font.italic = True

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    if not noticias_violentas:
        p_no = doc.add_paragraph(
            "Sin novedades registradas de homicidios intencionales o muertes violentas en las últimas 24 horas."
        )
        p_no.runs[0].font.name = "Arial"
        doc.save(output_filename)
        return output_filename

    for idx, noticia in enumerate(noticias_violentas, start=1):
        datos = extraer_datos_evento(
            noticia["titulo"], noticia["resumen"], noticia["sector"]
        )

        h_event = doc.add_paragraph()
        r_h = h_event.add_run(f"EVENTO N° {idx}: {datos['tipo_hecho'].upper()}")
        r_h.font.name = "Arial"
        r_h.font.size = Pt(13)
        r_h.font.bold = True
        r_h.font.color.rgb = RGBColor(180, 0, 0)

        table = doc.add_table(rows=5, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        fields = [
            ("Lugar / Sector:", datos["lugar"]),
            ("Coordenadas Aprox.:", datos["coordenadas"]),
            ("Víctimas / Impacto:", datos["victimas"]),
            ("Móvil Presunto:", datos["posible_móvil"]),
            ("Enlace de Origen:", noticia["link"]),
        ]

        for r_idx, (label, val) in enumerate(fields):
            row = table.rows[r_idx]
            cell_lbl, cell_val = row.cells[0], row.cells[1]
            set_cell_background(cell_lbl, "F0F0F0")

            r_l = cell_lbl.paragraphs[0].add_run(label)
            r_l.font.name = "Arial"
            r_l.font.bold = True

            r_v = cell_val.paragraphs[0].add_run(val)
            r_v.font.name = "Arial"

        p_res = doc.add_paragraph()
        p_res.paragraph_format.space_before = Pt(6)
        r_rt = p_res.add_run("Resumen Ejecutivo:\n")
        r_rt.font.bold = True
        r_rb = p_res.add_run(datos["resumen_ejecutivo"])

        if noticia.get("imagen_url"):
            try:
                req = urllib.request.Request(
                    noticia["imagen_url"],
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(req) as response:
                    img_bytes = response.read()

                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.add_run().add_picture(
                    io.BytesIO(img_bytes), width=Inches(4.5)
                )
            except Exception as e:
                print(f"No se pudo cargar la imagen: {e}")

    doc.save(output_filename)
    return output_filename


# 3. Bloque principal que genera el reporte y llama a la función de envío
if __name__ == "__main__":
    print("Iniciando generación de boletín bajo demanda...")

    # Aquí colocas tus noticias filtradas de muertes violentas
    noticias_filtradas = []

    nombre_archivo = "Boletin_Muertes_Violentas.docx"
    crear_boletin_word(noticias_filtradas, output_filename=nombre_archivo)

    # Llamada a la función para enviar el archivo creado a Telegram
    enviar_documento_telegram(
        nombre_archivo,
        "📄 <b>Boletín de Inteligencia Generado</b>\nAdjunto se encuentra el reporte de muertes violentas del día de hoy.",
    )
    print("Proceso finalizado.")
