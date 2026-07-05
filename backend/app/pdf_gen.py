"""Generación de PDFs de presupuestos — extraído de presupuestos.py.

Contiene:
- Constantes de brand (colores, nombre)
- Helpers de formato (_fmt_money)
- Builders de flowables (header, footer, estilos)
- 3 generadores: completo (owner), cliente, empleados
"""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable, PageBreak, KeepTogether,
)


# ─── BRAND COLORS / CONSTANTS ───
GOLD = HexColor("#c5a880")
NAVY = HexColor("#3a5874")
LIGHT_GOLD = HexColor("#f5f0e8")
LIGHT_NAVY = HexColor("#e8edf2")
DARK_NAVY = HexColor("#2a4060")
COMPANY = "Azul Livings Luján"


def _fmt_money(val: float) -> str:
    """Format a float as Argentine-style money string: $1.234"""
    return f"${int(round(val)):,}".replace(",", ".")


def _get_base_styles() -> dict:
    """Return a dict of reusable ParagraphStyles for PDF generation."""
    styles = getSampleStyleSheet()
    custom = {
        "title": ParagraphStyle(
            "BrandTitle", parent=styles["Title"],
            fontName="Helvetica-Bold", fontSize=18,
            textColor=NAVY, spaceAfter=2 * mm, alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "BrandSubtitle", parent=styles["Normal"],
            fontName="Helvetica", fontSize=10,
            textColor=GOLD, spaceAfter=6 * mm, alignment=TA_LEFT,
        ),
        "section": ParagraphStyle(
            "BrandSection", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=12,
            textColor=NAVY, spaceBefore=6 * mm, spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "BrandBody", parent=styles["Normal"],
            fontName="Helvetica", fontSize=9, leading=12,
            textColor=black,
        ),
        "body_bold": ParagraphStyle(
            "BrandBodyBold", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=9, leading=12,
            textColor=black,
        ),
        "small": ParagraphStyle(
            "BrandSmall", parent=styles["Normal"],
            fontName="Helvetica", fontSize=8, leading=10,
            textColor=HexColor("#666666"),
        ),
        "footer": ParagraphStyle(
            "BrandFooter", parent=styles["Normal"],
            fontName="Helvetica-Oblique", fontSize=8,
            textColor=HexColor("#999999"), alignment=TA_CENTER,
        ),
        "cell": ParagraphStyle(
            "BrandCell", parent=styles["Normal"],
            fontName="Helvetica", fontSize=9, leading=11,
            textColor=black,
        ),
        "cell_right": ParagraphStyle(
            "BrandCellRight", parent=styles["Normal"],
            fontName="Helvetica", fontSize=9, leading=11,
            textColor=black, alignment=TA_RIGHT,
        ),
        "cell_bold": ParagraphStyle(
            "BrandCellBold", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=9, leading=11,
            textColor=black,
        ),
        "cell_bold_right": ParagraphStyle(
            "BrandCellBoldRight", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=9, leading=11,
            textColor=black, alignment=TA_RIGHT,
        ),
    }
    return custom


def _build_pdf_buffer(story) -> io.BytesIO:
    """Build a PDF from a list of flowables and return the BytesIO buffer."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    doc.build(story)
    buf.seek(0)
    return buf


def _header_block(st, ppto_data: dict) -> list:
    """Return flowables for the company header + presupuesto info."""
    elements = []
    elements.append(Paragraph(COMPANY.upper(), st["title"]))
    elements.append(Paragraph("Presupuesto de Alquiler", st["subtitle"]))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=4 * mm))

    info_data = [
        [Paragraph("<b>Cliente:</b>", st["body"]),
         Paragraph(ppto_data.get("cliente_nombre") or "—", st["body"]),
         Paragraph("<b>Fecha evento:</b>", st["body"]),
         Paragraph(ppto_data.get("fecha_evento") or "—", st["body"])],
        [Paragraph("<b>Tipo:</b>", st["body"]),
         Paragraph(ppto_data.get("tipo_evento") or "—", st["body"]),
         Paragraph("<b>Invitados:</b>", st["body"]),
         Paragraph(str(ppto_data.get("cantidad_invitados") or "—"), st["body"])],
        [Paragraph("<b>Localidad:</b>", st["body"]),
         Paragraph(ppto_data.get("localidad") or "—", st["body"]),
         Paragraph("<b>Logística:</b>", st["body"]),
         Paragraph(ppto_data.get("logistica_tipo") or "—", st["body"])],
    ]
    info_table = Table(info_data, colWidths=[3 * cm, 5 * cm, 3 * cm, 5 * cm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4 * mm))
    return elements


def _footer_block(st) -> list:
    """Return footer flowables."""
    return [
        Spacer(1, 6 * mm),
        HRFlowable(width="100%", thickness=0.5, color=HexColor("#cccccc"), spaceAfter=3 * mm),
        Paragraph("Seña del 50% para confirmar la reserva", st["footer"]),
        Paragraph(COMPANY + " — presupuesto válido por 7 días", st["footer"]),
    ]


# ════════════════════════════════════════════════════════════════
# PDF COMPLETO (OWNER) — all details + prices
# ════════════════════════════════════════════════════════════════
def generate_pdf_completo(ppto_data: dict, lugares_raw: list, mob_prices: dict) -> io.BytesIO:
    st = _get_base_styles()
    story = []
    story.extend(_header_block(st, ppto_data))

    all_table_data = []
    for lugar in lugares_raw:
        all_table_data.append([
            Paragraph(f"<b>{lugar.get('nombre', 'General')}</b>", st["cell_bold"]),
            "", "", "", "",
        ])
        productos = lugar.get("productos", [])
        for prod in productos:
            key = prod.get("catalogo_key", "")
            qty = prod.get("cantidad", 1)
            precio_manual = prod.get("precio_manual")
            precio_unit = precio_manual if precio_manual is not None else mob_prices.get(key, 0)
            subtotal_item = precio_unit * qty
            notas = prod.get("notas", "")
            all_table_data.append([
                Paragraph(key, st["cell"]),
                Paragraph(str(qty), st["cell_right"]),
                Paragraph(_fmt_money(precio_unit), st["cell_right"]),
                Paragraph(_fmt_money(subtotal_item), st["cell_right"]),
                Paragraph(notas, st["small"]),
            ])
        subtotal_lugar = sum(
            (prod.get("precio_manual") if prod.get("precio_manual") is not None
             else mob_prices.get(prod.get("catalogo_key", ""), 0))
            * prod.get("cantidad", 1)
            for prod in productos
        )
        all_table_data.append([
            Paragraph(f"<b>Subtotal {lugar.get('nombre', 'General')}</b>", st["cell_bold"]),
            "", "",
            Paragraph(f"<b>{_fmt_money(subtotal_lugar)}</b>", st["cell_bold_right"]),
            "",
        ])

    if not all_table_data:
        all_table_data.append([Paragraph("Sin items", st["cell"]), "", "", "", ""])

    # Header row
    hdr_style = ParagraphStyle("hdr", parent=st["cell_bold"], textColor=white)
    hdr_r = ParagraphStyle("hdr_r", parent=st["cell_bold"], textColor=white, alignment=TA_RIGHT)
    all_table_data.insert(0, [
        Paragraph("<b>Item</b>", hdr_style),
        Paragraph("<b>Cant.</b>", hdr_r),
        Paragraph("<b>P.Unit.</b>", hdr_r),
        Paragraph("<b>Subtotal</b>", hdr_r),
        Paragraph("<b>Notas</b>", hdr_style),
    ])

    col_w = [5.5 * cm, 1.8 * cm, 2.5 * cm, 2.5 * cm, 4 * cm]
    items_table = Table(all_table_data, colWidths=col_w, repeatRows=1)

    style_cmds = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#cccccc")),
    ]

    current_row = 1
    for lugar in lugares_raw:
        style_cmds.append(("BACKGROUND", (0, current_row), (-1, current_row), LIGHT_GOLD))
        style_cmds.append(("SPAN", (0, current_row), (1, current_row)))
        current_row += 1
        n_products = len(lugar.get("productos", []))
        for i in range(n_products):
            if i % 2 == 1:
                style_cmds.append(("BACKGROUND", (0, current_row + i), (-1, current_row + i), HexColor("#f9f9f9")))
        current_row += n_products
        style_cmds.append(("BACKGROUND", (0, current_row), (-1, current_row), LIGHT_NAVY))
        style_cmds.append(("SPAN", (0, current_row), (2, current_row)))
        current_row += 1

    if len(lugares_raw) == 0:
        style_cmds.append(("SPAN", (0, 1), (2, 1)))

    items_table.setStyle(TableStyle(style_cmds))
    story.append(items_table)

    # Totals
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="60%", thickness=0.5, color=GOLD, spaceAfter=2 * mm))

    totals_data = [
        [Paragraph("<b>Subtotal Mobiliario</b>", st["cell_bold"]),
         Paragraph(_fmt_money(ppto_data["subtotal_mobiliario"]), st["cell_bold_right"])],
        [Paragraph("Logística" + (f" ({ppto_data['logistica_tipo']})" if ppto_data.get("logistica_tipo") else ""),
                   st["cell"]),
         Paragraph(_fmt_money(ppto_data["costo_logistica"]), st["cell_right"])],
    ]
    if ppto_data.get("acarreo_adicional"):
        totals_data.append([Paragraph("<i>Incluye acarreo adicional</i>", st["small"]), ""])
    if ppto_data.get("solo_ambientacion"):
        totals_data.append([Paragraph("<i>Solo ambientación (sin armado/desarme)</i>", st["small"]), ""])

    totals_data.append([
        Paragraph("<b>TOTAL</b>", ParagraphStyle("tot_bold", parent=st["cell_bold"], fontSize=11, textColor=NAVY)),
        Paragraph(f"<b>{_fmt_money(ppto_data['total'])}</b>",
                  ParagraphStyle("tot_val", parent=st["cell_bold_right"], fontSize=11, textColor=NAVY)),
    ])

    totals_table = Table(totals_data, colWidths=[10 * cm, 6 * cm])
    totals_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, NAVY),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, NAVY),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GOLD),
    ]))
    story.append(totals_table)
    story.extend(_footer_block(st))
    return _build_pdf_buffer(story)


# ════════════════════════════════════════════════════════════════
# PDF CLIENTE — clean, elegant, no per-item prices
# ════════════════════════════════════════════════════════════════
def generate_pdf_cliente(ppto_data: dict, lugares_raw: list) -> io.BytesIO:
    st = _get_base_styles()
    story = []
    story.extend(_header_block(st, ppto_data))

    table_data = []
    hdr_style = ParagraphStyle("cl_hdr", parent=st["cell_bold"], textColor=white, fontSize=9)
    hdr_r = ParagraphStyle("cl_hdr_r", parent=st["cell_bold"], textColor=white, fontSize=9, alignment=TA_RIGHT)
    table_data.append([Paragraph("<b>Item</b>", hdr_style), Paragraph("<b>Cantidad</b>", hdr_r)])

    for lugar in lugares_raw:
        table_data.append([Paragraph(f"<b>{lugar.get('nombre', 'General')}</b>", st["cell_bold"]), ""])
        for prod in lugar.get("productos", []):
            key = prod.get("catalogo_key", "")
            qty = prod.get("cantidad", 1)
            table_data.append([Paragraph(key, st["cell"]), Paragraph(str(qty), st["cell_right"])])

    if len(table_data) == 1:
        table_data.append([Paragraph("Sin items", st["cell"]), ""])

    col_w = [12 * cm, 4 * cm]
    items_table = Table(table_data, colWidths=col_w, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#dddddd")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#f7f5f0")]),
    ]

    current_row = 1
    for lugar in lugares_raw:
        style_cmds.append(("BACKGROUND", (0, current_row), (-1, current_row), LIGHT_GOLD))
        style_cmds.append(("SPAN", (0, current_row), (1, current_row)))
        current_row += 1 + len(lugar.get("productos", []))

    items_table.setStyle(TableStyle(style_cmds))
    story.append(items_table)

    # Totals
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="50%", thickness=0.8, color=GOLD, spaceAfter=3 * mm))

    tot_data = []
    if ppto_data.get("costo_logistica") and ppto_data["costo_logistica"] > 0:
        log_label = "Flete / Traslado"
        if ppto_data.get("logistica_tipo"):
            log_label += f" ({ppto_data['logistica_tipo']})"
        tot_data.append([Paragraph(log_label, st["cell"]),
                         Paragraph(_fmt_money(ppto_data["costo_logistica"]), st["cell_right"])])

    tot_data.append([
        Paragraph("<b>TOTAL</b>", ParagraphStyle("cl_tot", parent=st["cell_bold"], fontSize=12, textColor=NAVY)),
        Paragraph(f"<b>{_fmt_money(ppto_data['total'])}</b>",
                  ParagraphStyle("cl_tot_v", parent=st["cell_bold_right"], fontSize=12, textColor=NAVY)),
    ])

    tot_table = Table(tot_data, colWidths=[10 * cm, 6 * cm])
    tot_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, NAVY),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, NAVY),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GOLD),
    ]))
    story.append(tot_table)
    story.extend(_footer_block(st))
    return _build_pdf_buffer(story)


# ════════════════════════════════════════════════════════════════
# PDF EMPLEADOS — checklist, no prices, checkbox col
# ════════════════════════════════════════════════════════════════
def generate_pdf_empleados(ppto_data: dict, lugares_raw: list) -> io.BytesIO:
    st = _get_base_styles()
    story = []

    # Simplified header for warehouse
    story.append(Paragraph(COMPANY.upper(), st["title"]))
    story.append(Paragraph("Lista de Carga — Depósito", st["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=4 * mm))

    info_data = [
        [Paragraph("<b>Cliente:</b>", st["body"]),
         Paragraph(ppto_data.get("cliente_nombre") or "—", st["body"]),
         Paragraph("<b>Fecha:</b>", st["body"]),
         Paragraph(ppto_data.get("fecha_evento") or "—", st["body"])],
        [Paragraph("<b>Tipo:</b>", st["body"]),
         Paragraph(ppto_data.get("tipo_evento") or "—", st["body"]),
         Paragraph("<b>Localidad:</b>", st["body"]),
         Paragraph(ppto_data.get("localidad") or "—", st["body"])],
    ]
    info_tbl = Table(info_data, colWidths=[3 * cm, 5 * cm, 3 * cm, 5 * cm])
    info_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 4 * mm))

    # Checklist table
    table_data = []
    hdr_w = ParagraphStyle("emp_hdr", parent=st["cell_bold"], textColor=white, fontSize=9)
    hdr_r = ParagraphStyle("emp_hdr_r", parent=st["cell_bold"], textColor=white, fontSize=9, alignment=TA_CENTER)
    table_data.append([Paragraph("<b>☐</b>", hdr_r), Paragraph("<b>Item</b>", hdr_w), Paragraph("<b>Cantidad</b>", hdr_r)])

    total_items = 0
    for lugar in lugares_raw:
        table_data.append(["", Paragraph(f"<b>{lugar.get('nombre', 'General')}</b>", st["cell_bold"]), ""])
        for prod in lugar.get("productos", []):
            key = prod.get("catalogo_key", "")
            qty = prod.get("cantidad", 1)
            total_items += qty
            table_data.append([
                Paragraph("☐", ParagraphStyle("chk", parent=st["cell"], alignment=TA_CENTER, fontSize=12)),
                Paragraph(key, st["cell"]),
                Paragraph(str(qty), st["cell_right"]),
            ])

    if len(table_data) == 1:
        table_data.append(["", Paragraph("Sin items", st["cell"]), ""])

    col_w = [1.5 * cm, 11 * cm, 3.5 * cm]
    items_table = Table(table_data, colWidths=col_w, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.3, HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#f5f5f5")]),
    ]

    current_row = 1
    for lugar in lugares_raw:
        style_cmds.append(("BACKGROUND", (0, current_row), (-1, current_row), LIGHT_NAVY))
        style_cmds.append(("SPAN", (0, current_row), (1, current_row)))
        current_row += 1 + len(lugar.get("productos", []))

    items_table.setStyle(TableStyle(style_cmds))
    story.append(items_table)

    # Summary
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="40%", thickness=0.5, color=NAVY, spaceAfter=3 * mm))
    story.append(Paragraph(f"<b>Total de piezas:</b> {total_items}", st["cell_bold"]))

    # Signature
    story.append(Spacer(1, 15 * mm))
    story.append(HRFlowable(width="45%", thickness=0.5, color=HexColor("#999999"), spaceAfter=1 * mm, hAlign="CENTER"))
    story.append(Paragraph("Firma de entrega", ParagraphStyle("sig", parent=st["small"], alignment=TA_CENTER)))

    story.extend(_footer_block(st))
    return _build_pdf_buffer(story)
