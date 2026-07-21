"""Generación de presupuesto en formato Word (.docx).

Estructura: primero todo el texto (tabla sin fotos), luego sección de fotos
con el nombre del mobiliario y su foto en grande.
"""
import io
import os
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

GOLD = RGBColor(0xC5, 0xA8, 0x80)
NAVY = RGBColor(0x3A, 0x58, 0x74)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY = RGBColor(0x99, 0x99, 0x99)
COMPANY = "Azul Livings Luján"


def _fmt_money(val: float) -> str:
    return f"${int(round(val)):,}".replace(",", ".")


def _shade_cell(cell, hex_color: str):
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shading)


def _header_block(doc, ppto_data: dict, subtitle: str):
    p = doc.add_paragraph()
    run = p.add_run(COMPANY.upper())
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = NAVY
    p.paragraph_format.space_after = Pt(2)

    p = doc.add_paragraph()
    run = p.add_run(subtitle)
    run.font.size = Pt(10)
    run.font.color.rgb = GOLD
    p.paragraph_format.space_after = Pt(8)

    info = doc.add_table(rows=3, cols=4)
    info.style = "Table Grid"
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


def _totales_block(doc, ppto_data: dict, show_mobiliario: bool = False):
    if show_mobiliario:
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

    senia_para = doc.add_paragraph()
    senia_para.paragraph_format.space_before = Pt(6)
    run = senia_para.add_run("Seña del 50% para confirmar la reserva")
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = GREY


def _fotos_section(doc, lugares_raw: list, mob_fotos: dict):
    """Sección de fotos: nombre del mobiliario + foto grande, una por página."""
    # Recopilar items únicos que tienen foto
    items_con_foto = []
    vistos = set()
    for lugar in lugares_raw:
        for prod in lugar.get("productos", []):
            key = prod.get("catalogo_key", "")
            if key and key not in vistos:
                foto_path = mob_fotos.get(key)
                if foto_path and os.path.exists(foto_path):
                    items_con_foto.append((key, foto_path))
                    vistos.add(key)

    if not items_con_foto:
        return

    # Salto de página antes de la sección de fotos
    doc.add_page_break()

    # Título de la sección
    p = doc.add_paragraph()
    run = p.add_run(" Fotos del mobiliario")
    run.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = NAVY
    p.paragraph_format.space_after = Pt(12)

    for nombre, foto_path in items_con_foto:
        # Nombre del mobiliario
        p = doc.add_paragraph()
        run = p.add_run(nombre)
        run.bold = True
        run.font.size = Pt(13)
        run.font.color.rgb = NAVY
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(6)

        # Foto grande centrada
        try:
            photo_para = doc.add_paragraph()
            photo_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = photo_para.add_run()
            run.add_picture(foto_path, width=Cm(14))
        except Exception:
            pass

        # Salto de página entre fotos (excepto la última)
        if (nombre, foto_path) != items_con_foto[-1]:
            doc.add_page_break()


# ════════════════════════════════════════════════════════════════
# WORD CLIENTE — sin precios por item, luego sección de fotos
# ════════════════════════════════════════════════════════════════
def generate_word_cliente(ppto_data: dict, lugares_raw: list, mob_fotos: dict = None) -> io.BytesIO:
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

    # ─── HEADER + INFO ───
    _header_block(doc, ppto_data, "Presupuesto de Alquiler")
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # ─── TABLA DE ITEMS (sin fotos) ───
    tbl = doc.add_table(rows=1, cols=3)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    for i, label in enumerate(["Item", "Cantidad", "Subtotal"]):
        para = hdr[i].paragraphs[0]
        run = para.add_run(label)
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = WHITE
        _shade_cell(hdr[i], "3A5874")

    for lugar in lugares_raw:
        # Fila nombre del lugar (merger las 3 celdas)
        row = tbl.add_row()
        row.cells[1].merge(row.cells[2])
        cell = row.cells[0]
        para = cell.paragraphs[0]
        run = para.add_run(lugar.get("nombre", "General"))
        run.bold = True
        run.font.size = Pt(11)
        _shade_cell(cell, "F5F0E8")
        _shade_cell(row.cells[1], "F5F0E8")

        for prod in lugar.get("productos", []):
            key = prod.get("catalogo_key", "")
            qty = prod.get("cantidad", 1)
            row = tbl.add_row()
            row.cells[0].paragraphs[0].add_run(key).font.size = Pt(10)
            row.cells[1].paragraphs[0].add_run(str(qty)).font.size = Pt(10)
            row.cells[2].paragraphs[0].add_run("").font.size = Pt(10)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ─── TOTALES ───
    _totales_block(doc, ppto_data, show_mobiliario=False)

    # ─── SECCIÓN DE FOTOS ───
    _fotos_section(doc, lugares_raw, mob_fotos)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ════════════════════════════════════════════════════════════════
# WORD COMPLETO — con precios por item, luego sección de fotos
# ════════════════════════════════════════════════════════════════
def generate_word_completo(ppto_data: dict, lugares_raw: list, mob_prices: dict, mob_fotos: dict = None) -> io.BytesIO:
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

    # ─── HEADER + INFO ───
    _header_block(doc, ppto_data, "Presupuesto de Alquiler — Detalle Completo")
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # ─── TABLA DE ITEMS (sin fotos, con precios) ───
    tbl = doc.add_table(rows=1, cols=4)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    for i, label in enumerate(["Item", "Cantidad", "Precio Unit.", "Subtotal"]):
        para = hdr[i].paragraphs[0]
        run = para.add_run(label)
        run.bold = True
        run.font.color.rgb = WHITE
        _shade_cell(hdr[i], "3A5874")

    for lugar in lugares_raw:
        row = tbl.add_row()
        row.cells[1].merge(row.cells[2]).merge(row.cells[3])
        cell = row.cells[0]
        para = cell.paragraphs[0]
        run = para.add_run(lugar.get("nombre", "General"))
        run.bold = True
        run.font.size = Pt(11)
        _shade_cell(cell, "F5F0E8")

        for prod in lugar.get("productos", []):
            key = prod.get("catalogo_key", "")
            qty = prod.get("cantidad", 1)
            precio_unit = mob_prices.get(key, 0)
            subtotal = qty * precio_unit

            row = tbl.add_row()
            row.cells[0].paragraphs[0].add_run(key).font.size = Pt(10)
            row.cells[1].paragraphs[0].add_run(str(qty)).font.size = Pt(10)
            row.cells[2].paragraphs[0].add_run(_fmt_money(precio_unit)).font.size = Pt(10)
            row.cells[3].paragraphs[0].add_run(_fmt_money(subtotal)).font.size = Pt(10)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ─── TOTALES ───
    _totales_block(doc, ppto_data, show_mobiliario=True)

    # ─── SECCIÓN DE FOTOS ───
    _fotos_section(doc, lugares_raw, mob_fotos)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
