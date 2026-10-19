import io
import os
import re
import sqlite3
import urllib.request
from datetime import datetime
from apify_client import ApifyClient
import docx
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor
from google import genai

# Credenciales
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Coordenadas de referencia para cada sector
COORDENADAS_SECTORES = {
    "posorja": "-2.7061, -80.2464",
    "el morro": "-2.6231, -80.3128",
    "progreso": "-2.3922, -80.3789",
    "chongon": "-2.2483, -80.0811",
    "chongón": "-2.2483, -80.0811",
}


def set_cell_background(cell, fill_hex):
    """Aplica color de fondo a una celda de la tabla en Word"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def extraer_datos_evento(titulo, resumen, sector):
    """Usa Gemini para analizar la noticia y estructurar los datos del reporte"""
    if not GEMINI_API_KEY:
        return {
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "lugar": sector.capitalize(),
            "coordenadas": COORDENADAS_SECTORES.get(
                sector.lower(), "-2.1962, -79.8862"
            ),
            "tipo_hecho": "Muerte Violenta / Homicidio Intencional",
            "victimas": "Por determinar",
            "resumen_ejecutivo": f"{titulo}. {resumen}",
            "posible_móvil": "En investigación policial.",
        }

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    Eres un analista de inteligencia operacional policial en Ecuador.
    Analiza la siguiente noticia de un presunto homicidio o muerte violenta en la provincia del Guayas:

    TITULAR: {titulo}
    CONTENIDO: {resumen}
    SECTOR PRINCIPAL: {sector}

    Extrae la información en el siguiente formato exacto (línea por línea):
    LUGAR_EXACTO: (Dirección, barrio o punto de referencia mencionado en {sector})
    TIPO_HECHO: (Homicidio intencional / Sicariato / Femicidio / Encontrado sin vida)
    VICTIMAS: (Número estimado o nombres si constan)
    POSIBLE_MOVIL: (Ajuste de cuentas, robo, violencia interpersonal, o En investigación)
    RESUMEN_EJECUTIVO: (Síntesis técnica del suceso en máximo 3 oraciones)
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        raw_text = response.text

        # Parsing simple de las líneas
        data = {
            "lugar": f"{sector.capitalize()}, Guayas",
            "tipo_hecho": "Homicidio Intencional",
            "victimas": "1 persona (por confirmar)",
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
    """Genera un archivo Word estructurado con las noticias de muertes violentas"""
    doc = Document()

    # Configuración de márgenes
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Encabezado del Documento
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("BOLETÍN DE INTELIGENCIA DE SEGURIDAD")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(18)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(180, 0, 0)  # Rojo oscuro policial

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run(
        f"REPORTE ESPECIAL: HOMICIDIOS INTENCIONALES Y MUERTES VIOLENTAS\n"
        f"FECHA DE EMISIÓN: {datetime.now().strftime('%d de %B de %Y')}"
    )
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(10)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(80, 80, 80)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    if not noticias_violentas:
        p_no = doc.add_paragraph(
            "Sin novedades registradas de homicidios intencionales en las últimas 24 horas en los sectores de Posorja, El Morro, Progreso y Chongón."
        )
        p_no.runs[0].font.name = "Arial"
        doc.save(output_filename)
        return output_filename

    # Iterar sobre cada evento detectado
    for idx, noticia in enumerate(noticias_violentas, start=1):
        datos = extraer_datos_evento(
            noticia["titulo"], noticia["resumen"], noticia["sector"]
        )

        # Encabezado del Evento
        h_event = doc.add_paragraph()
        r_h = h_event.add_run(f"EVENTO N° {idx}: {datos['tipo_hecho'].upper()}")
        r_h.font.name = "Arial"
        r_h.font.size = Pt(13)
        r_h.font.bold = True
        r_h.font.color.rgb = RGBColor(180, 0, 0)

        # Tabla de Ficha Técnica
        table = doc.add_table(rows=5, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        col_widths = [Inches(2.0), Inches(4.5)]

        fields = [
            ("Lugar / Sector:", datos["lugar"]),
            ("Coordenadas Aprox.:", datos["coordenadas"]),
            ("Víctimas / Impacto:", datos["victimas"]),
            ("Móvil Presunto:", datos["posible_móvil"]),
            ("Enlace de Origen:", noticia["link"]),
        ]

        for r_idx, (label, val) in enumerate(fields):
            row = table.rows[r_idx]

            # Celda izquierda (Etiqueta)
            cell_lbl = row.cells[0]
            cell_lbl.width = col_widths[0]
            set_cell_background(cell_lbl, "F0F0F0")
            p_l = cell_lbl.paragraphs[0]
            r_l = p_l.add_run(label)
            r_l.font.name = "Arial"
            r_l.font.size = Pt(9.5)
            r_l.font.bold = True

            # Celda derecha (Valor)
            cell_val = row.cells[1]
            cell_val.width = col_widths[1]
            p_v = cell_val.paragraphs[0]
            r_v = p_v.add_run(val)
            r_v.font.name = "Arial"
            r_v.font.size = Pt(9.5)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

        # Resumen del Hecho
        p_res = doc.add_paragraph()
        r_rt = p_res.add_run("Resumen Ejecutivo del Hecho:\n")
        r_rt.font.bold = True
        r_rt.font.size = Pt(10)
        r_rt.font.name = "Arial"

        r_rb = p_res.add_run(datos["resumen_ejecutivo"])
        r_rb.font.size = Pt(10)
        r_rb.font.name = "Arial"

        # Descarga e Inserción de Fotografía (si está disponible)
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
                run_img = p_img.add_run()
                run_img.add_picture(io.BytesIO(img_bytes), width=Inches(4.5))

                p_cap = doc.add_paragraph()
                p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r_cap = p_cap.add_run(
                    f"Figura {idx}.1: Registro gráfico del hecho / escena captado por la fuente."
                )
                r_cap.font.size = Pt(8.5)
                r_cap.font.italic = True
                r_cap.font.color.rgb = RGBColor(120, 120, 120)
            except Exception as e:
                print(f"No se pudo descargar la imagen: {e}")

        doc.add_paragraph().paragraph_format.space_after = Pt(18)

    doc.save(output_filename)
    return output_filename


# Ejemplo de uso simulado
if __name__ == "__main__":
    noticias_ejemplo = [
        {
            "titulo": "Hallan a persona sin vida con heridas de arma de fuego en Posorja",
            "resumen": "La mañana de este lunes habitantes del barrio Bellavista reportaron el hallazgo de un cuerpo. Policía Nacional acordonó la zona.",
            "sector": "posorja",
            "link": "https://ejemplo.com/noticia-posorja",
            "imagen_url": None,
        }
    ]

    crear_boletin_word(noticias_ejemplo, "Boletin_Muertes_Violentas.docx")
    print("Boletín generado con éxito: Boletin_Muertes_Violentas.docx")