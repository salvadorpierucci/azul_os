"""Generación de presupuesto en formato Word (.docx) con fotos grandes de mobiliario.

Reemplaza generate_pdf_cliente para el presupuesto que ve el cliente.
Las fotos van abajo del texto de cada item, en grande.
"""
import io
import os
from docx import Document
from docx.shared import Cm, Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

GOLD = RGBColor(0xC5, 0xA8, 0x80)
NAVY = RGBColor(0x3A, 0x58, 0x74)
DARK_NAVY = RGBColor(0x2A, 0x40, 0x60)
LIGHT_GOLD_HEX = "F5F0E8"
LIGHT_NAVY_HEX = "E8EDF2"
COMPANY = "Azul Livings Luján"


def _fmt_money(val: float) -> str:
    return f"${int(round(val)):,}".replace(",", ".")


def generate_word_cliente(ppto_data: dict, lugares_raw: list, mob_fotos: dict = None) -> io.BytesIO:
    mob_fotos = mob_fotos or {}
    doc = Document()

    # Margenes
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2)
        section.right_margin = Cm(2)

    # Estilo base
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)

    # ─── HEADER ───
    p = doc.add_paragraph()
    run = p.add_run(COMPANY.upper())
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = NAVY
    p.space_after = Pt(2)

    p = doc.add_paragraph()
    run = p.add_run("Presupuesto de Alquiler")
    run.font.size = Pt(10)
    run.font.color.rgb = GOLD
    p.space_after = Pt(8)

    # Linea separadora (simulada con borde inferior)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)

    # Tabla de info del cliente
    info = doc.add_table(rows=3, cols=4)
    info.style = "Table Grid"
    info.alignment = WD_TABLE_ALIGNMENT.LEFT

    info_data = [
        ("Cliente:", ppto_data.get("cliente_nombre") or "—", "Fecha evento:", ppto_data.get("fecha_evento") or "—"),
        ("Tipo:", ppto_data.get("tipo_evento") or "—", "Invitados:", str(ppto_data.get("cantidad_invitados") or "—")),
        ("Localidad:", ppto_data.get("localidad") or "—", "Logística:", "—"),
    ]
    for row_idx, (l1, v1, l2, v2) in enumerate(info_data):
        cells = info.rows[row_idx].cells
        for cell_idx, text in enumerate([l1, v1, l2, v2]):
            para = cells[cell_idx].paragraphs[0]
            run = para.add_run(text)
            if cell_idx % 2 == 0:
                run.bold = True
            run.font.size = Pt(10)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # ─── TABLA DE ITEMS ───
    # Encabezado
    tbl = doc.add_table(rows=1, cols=3)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    for i, label in enumerate(["Item", "Cantidad", "Subtotal"]):
        para = hdr[i].paragraphs[0]
        run = para.add_run(label)
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = NAVY
        # Sombrear celda header
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "3A5874")
        hdr[i]._tc.get_or_add_tcPr().append(shading)
        # Text color blanco
        for run in para.runs:
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for lugar in lugares_raw:
        # Fila nombre del lugar
        row = tbl.add_row()
        cell = row.cells[0]
        # Mergear las 3 celdas
        row.cells[1].merge(row.cells[2])
        para = cell.paragraphs[0]
        run = para.add_run(lugar.get("nombre", "General"))
        run.bold = True
        run.font.size = Pt(11)
        # Sombrear
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "F5F0E8")
        cell._tc.get_or_add_tcPr().append(shading)
        shading2 = OxmlElement("w:shd")
        shading2.set(qn("w:fill"), "F5F0E8")
        row.cells[1]._tc.get_or_add_tcPr().append(shading2)

        for prod in lugar.get("productos", []):
            key = prod.get("catalogo_key", "")
            qty = prod.get("cantidad", 1)
            # Calcular subtotal (usar precio del mob si existe, sino 0)
            precio = 0
            if mob_fotos and key in mob_fotos:
                # No tenemos precio aca, el subtotal viene del presupuesto
                pass
            subtotal_str = ""  # El cliente no ve precios por item, solo el total final

            row = tbl.add_row()
            row.cells[0].paragraphs[0].add_run(key).font.size = Pt(10)
            row.cells[1].paragraphs[0].add_run(str(qty)).font.size = Pt(10)
            row.cells[2].paragraphs[0].add_run("").font.size = Pt(10)

            # Foto grande abajo del texto del item
            foto_path = mob_fotos.get(key)
            if foto_path and os.path.exists(foto_path):
                try:
                    # Insertar foto en la celda del item, centrada, grande
                    photo_para = row.cells[0].add_paragraph()
                    photo_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = photo_para.add_run()
                    run.add_picture(foto_path, width=Cm(8))
                except Exception:
                    pass

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ─── TOTALES ───
    if ppto_data.get("costo_logistica") and ppto_data["costo_logistica"] > 0:
        log_label = "Flete / Traslado"
        tot_para = doc.add_paragraph()
        tot_para.paragraph_format.space_after = Pt(2)
        r1 = tot_para.add_run(f"{log_label}:  ")
        r1.font.size = Pt(10)
        r2 = tot_para.add_run(_fmt_money(ppto_data["costo_logistica"]))
        r2.font.size = Pt(10)

    # Total final
    tot_para = doc.add_paragraph()
    tot_para.paragraph_format.space_before = Pt(6)
    r1 = tot_para.add_run("TOTAL:  ")
    r1.bold = True
    r1.font.size = Pt(14)
    r1.font.color.rgb = NAVY
    r2 = tot_para.add_run(_fmt_money(ppto_data.get("total", 0)))
    r2.bold = True
    r2.font.size = Pt(14)
    r2.font.color.rgb = NAVY

    # Seña
    senia_para = doc.add_paragraph()
    senia_para.paragraph_format.space_before = Pt(6)
    run = senia_para.add_run("Seña del 50% para confirmar la reserva")
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    # Guardar al buffer
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def generate_word_completo(ppto_data: dict, lugares_raw: list, mob_prices: dict, mob_fotos: dict = None) -> io.BytesIO:
    """Version completa (owner): igual que cliente pero con precios por item."""
    mob_fotos = mob_fotos or {}
    doc = Document()

    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2)
        section.right_margin = Cm(2)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)

    # ─── HEADER ───
    p = doc.add_paragraph()
    run = p.add_run(COMPANY.upper())
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = NAVY
    p.space_after = Pt(2)

    p = doc.add_paragraph()
    run = p.add_run("Presupuesto de Alquiler — Detalle Completo")
    run.font.size = Pt(10)
    run.font.color.rgb = GOLD
    p.space_after = Pt(8)

    # Info
    info = doc.add_table(rows=3, cols=4)
    info.style = "Table Grid"
    info_data = [
        ("Cliente:", ppto_data.get("cliente_nombre") or "—", "Fecha evento:", ppto_data.get("fecha_evento") or "—"),
        ("Tipo:", ppto_data.get("tipo_evento") or "—", "Invitados:", str(ppto_data.get("cantidad_invitados") or "—")),
        ("Localidad:", ppto_data.get("localidad") or "—", "Distancia km:", str(ppto_data.get("distancia_km") or "0")),
    ]
    for row_idx, (l1, v1, l2, v2) in enumerate(info_data):
        cells = info.rows[row_idx].cells
        for cell_idx, text in enumerate([l1, v1, l2, v2]):
            para = cells[cell_idx].paragraphs[0]
            run = para.add_run(text)
            if cell_idx % 2 == 0:
                run.bold = True
            run.font.size = Pt(10)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # ─── TABLA CON PRECIOS ───
    tbl = doc.add_table(rows=1, cols=4)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    for i, label in enumerate(["Foto", "Item", "Cantidad", "Subtotal"]):
        para = hdr[i].paragraphs[0]
        run = para.add_run(label)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "3A5874")
        hdr[i]._tc.get_or_add_tcPr().append(shading)

    for lugar in lugares_raw:
        row = tbl.add_row()
        row.cells[1].merge(row.cells[2]).merge(row.cells[3])
        cell = row.cells[0]
        para = cell.paragraphs[0]
        run = para.add_run(lugar.get("nombre", "General"))
        run.bold = True
        run.font.size = Pt(11)
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "F5F0E8")
        cell._tc.get_or_add_tcPr().append(shading)

        for prod in lugar.get("productos", []):
            key = prod.get("catalogo_key", "")
            qty = prod.get("cantidad", 1)
            precio_unit = mob_prices.get(key, 0)
            subtotal = qty * precio_unit

            row = tbl.add_row()
            # Celda foto: si hay foto la pone, sino texto
            foto_path = mob_fotos.get(key)
            if foto_path and os.path.exists(foto_path):
                try:
                    photo_para = row.cells[0].paragraphs[0]
                    photo_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = photo_para.add_run()
                    run.add_picture(foto_path, width=Cm(3))
                except Exception:
                    row.cells[0].paragraphs[0].add_run("")
            else:
                row.cells[0].paragraphs[0].add_run("")

            row.cells[1].paragraphs[0].add_run(key).font.size = Pt(10)
            row.cells[2].paragraphs[0].add_run(str(qty)).font.size = Pt(10)
            row.cells[3].paragraphs[0].add_run(_fmt_money(subtotal)).font.size = Pt(10)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Totales
    tot_para = doc.add_paragraph()
    r = tot_para.add_run(f"Mobiliario: {_fmt_money(ppto_data.get('subtotal_mobiliario', 0))}")
    r.font.size = Pt(10)
    tot_para.paragraph_format.space_after = Pt(2)

    if ppto_data.get("costo_logistica") and ppto_data["costo_logistica"] > 0:
        log_para = doc.add_paragraph()
        r = log_para.add_run(f"Flete / Traslado: {_fmt_money(ppto_data['costo_logistica'])}")
        r.font.size = Pt(10)
        log_para.paragraph_format.space_after = Pt(2)

    total_para = doc.add_paragraph()
    total_para.paragraph_format.space_before = Pt(6)
    r1 = total_para.add_run("TOTAL: ")
    r1.bold = True
    r1.font.size = Pt(14)
    r1.font.color.rgb = NAVY
    r2 = total_para.add_run(_fmt_money(ppto_data.get("total", 0)))
    r2.bold = True
    r2.font.size = Pt(14)
    r2.font.color.rgb = NAVY

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
