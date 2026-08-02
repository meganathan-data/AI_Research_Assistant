"""
PDF Generator Module
Converts company research Python dictionaries into high-quality, professional, premium PDF reports.
Uses a minimalistic dark navy and sky blue color palette (#0f172a / #0284c7).
"""

import io
import textwrap
from typing import Any

def generate_pdf_report(report: dict[str, Any]) -> bytes:
    """
    Generates a premium PDF report binary from a research report Python dictionary.
    Supports ReportLab with custom ParagraphStyles and automatic text wrapping.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        
        NAVY_BG = colors.HexColor("#0f172a")
        SKY_BLUE = colors.HexColor("#0284c7")
        
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#ffffff')
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#38bdf8')
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=SKY_BLUE,
            spaceAfter=4
        )
        
        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor('#1e293b')
        )
        
        bullet_style = ParagraphStyle(
            'ReportBullet',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor('#334155'),
            leftIndent=12,
            spaceAfter=4
        )
        
        story = []
        
        # 1. Dark Navy Header Banner
        header_data = [
            [Paragraph("RELU CONSULTANCY · COMPANY RESEARCH REPORT", subtitle_style)],
            [Paragraph(report.get('company_name', 'Company Intelligence Report'), title_style)]
        ]
        header_table = Table(header_data, colWidths=[540])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), NAVY_BG),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 16))
        
        # 2. Company Information Section
        story.append(Paragraph("COMPANY INFORMATION", section_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=SKY_BLUE, spaceBefore=2, spaceAfter=8))
        
        info_rows = [
            [Paragraph("<b>Official Website</b>", body_style), Paragraph(f"<font color='#0284c7'><u>{report.get('website', '')}</u></font>", body_style)]
        ]
        
        phone_val = report.get('phone', '').strip()
        if phone_val and 'not' not in phone_val.lower():
            info_rows.append([Paragraph("<b>Phone</b>", body_style), Paragraph(phone_val, body_style)])

        locs = report.get('locations', [])
        if isinstance(locs, list) and locs:
            loc_paragraphs = []
            for country in locs:
                cname = country.get('country_name', '')
                loc_paragraphs.append(f"<b>🌍 {cname}</b>")
                for city in country.get('cities', []):
                    ctname = city.get('city_name', '')
                    addrs = ", ".join(city.get('addresses', []))
                    loc_paragraphs.append(f"&nbsp;&nbsp;&nbsp;&nbsp;• <b>{ctname}:</b> {addrs}")
            
            loc_text = "<br/>".join(loc_paragraphs)
            info_rows.append([Paragraph("<b>Locations & Offices</b>", body_style), Paragraph(loc_text, body_style)])

        info_table = Table(info_rows, colWidths=[140, 400])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 14))
        
        # 3. Products & Services Section
        story.append(Paragraph("PRODUCTS & SERVICES", section_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=SKY_BLUE, spaceBefore=2, spaceAfter=8))
        
        for prod in report.get("products_and_services", []):
            story.append(Paragraph(f"• &nbsp; <b>{prod}</b>", bullet_style))
            
        story.append(Spacer(1, 14))
        
        # 4. SUMMARY Section
        story.append(Paragraph("SUMMARY", section_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=SKY_BLUE, spaceBefore=2, spaceAfter=8))
        
        summary_pts = report.get("summary") or report.get("pain_points", [])
        for idx, pt in enumerate(summary_pts, 1):
            pt_para = Paragraph(f"<b>{idx}.</b> &nbsp; {pt}", bullet_style)
            story.append(pt_para)
            story.append(Spacer(1, 4))
            
        story.append(Spacer(1, 14))
        
        # 5. Competitors Section
        story.append(Paragraph("COMPETITORS", section_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=SKY_BLUE, spaceBefore=2, spaceAfter=8))
        
        comp_data = []
        for comp in report.get("competitors", []):
            comp_data.append([
                Paragraph(f"<b>{comp.get('name', '')}</b>", body_style),
                Paragraph(f"<font color='#0284c7'><u>{comp.get('website', '')}</u></font>", body_style)
            ])
            
        if comp_data:
            comp_table = Table(comp_data, colWidths=[200, 340])
            comp_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(comp_table)
            
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
        
    except Exception as e:
        print(f"[ReportLab Warning]: {e}. Using pure-Python vector PDF engine.")
        return generate_styled_vector_pdf_fallback(report)

def generate_styled_vector_pdf_fallback(report: dict[str, Any]) -> bytes:
    """
    Pure Python Vector PDF engine using dark navy and sky blue color palette.
    """
    company_name = report.get("company_name", "Company")
    website = report.get("website", "")
    phone = report.get("phone", "")
    locs = report.get("locations", [])
    products = report.get("products_and_services", [])
    summary_pts = report.get("summary") or report.get("pain_points", [])
    competitors = report.get("competitors", [])
    
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    
    content_lines = []
    
    # 1. Dark Navy Header Banner Box
    content_lines.append("0.06 0.09 0.16 rg") # Dark navy #0f172a
    content_lines.append("36 700 540 65 re f")
    
    # Subtitle Sky Blue Text
    content_lines.append("BT\n0.22 0.74 0.97 rg\n/F1 8.5 Tf\n12 TL\n52 748 Td\n(RELU CONSULTANCY - COMPANY RESEARCH REPORT) Tj\nET")
    # Title White Text
    safe_company = company_name.replace("(", "\\(").replace(")", "\\)")
    content_lines.append(f"BT\n1 1 1 rg\n/F1 18 Tf\n22 TL\n52 718 Td\n({safe_company}) Tj\nET".encode("latin-1", "ignore").decode("latin-1"))
    
    y = 675
    
    def draw_section_title(title: str, current_y: int) -> int:
        cmds = []
        cmds.append(f"BT\n0.01 0.52 0.78 rg\n/F1 11 Tf\n14 TL\n36 {current_y} Td\n({title}) Tj\nET")
        cmds.append(f"0.01 0.52 0.78 RG 1.5 w 36 {current_y - 4} m 576 {current_y - 4} l S")
        return current_y - 20
        
    y = draw_section_title("COMPANY INFORMATION", y)
    
    content_lines.append(f"BT\n0.12 0.16 0.23 rg\n/F1 9.5 Tf\n13 TL\n36 {y} Td\n(Website: {website}) Tj\nET".encode("latin-1", "ignore").decode("latin-1"))
    y -= 16
    
    if phone and 'not' not in phone.lower():
        content_lines.append(f"BT\n0.12 0.16 0.23 rg\n/F1 9.5 Tf\n13 TL\n36 {y} Td\n(Phone: {phone}) Tj\nET".encode("latin-1", "ignore").decode("latin-1"))
        y -= 16
        
    if isinstance(locs, list):
        content_lines.append(f"BT\n0.12 0.16 0.23 rg\n/F1 9.5 Tf\n13 TL\n36 {y} Td\n(Locations & Branch Hierarchy:) Tj\nET")
        y -= 16
        for c in locs[:4]:
            cname = c.get('country_name', '')
            content_lines.append(f"BT\n0.12 0.16 0.23 rg\n/F1 9.5 Tf\n13 TL\n48 {y} Td\n(* Country: {cname}) Tj\nET".encode("latin-1", "ignore").decode("latin-1"))
            y -= 14
            for city in c.get('cities', [])[:3]:
                ctname = city.get('city_name', '')
                addrs = ", ".join(city.get('addresses', []))
                wrapped_addrs = textwrap.wrap(f"{ctname}: {addrs}", width=70)
                for w_line in wrapped_addrs[:2]:
                    content_lines.append(f"BT\n0.2 0.25 0.35 rg\n/F1 8.5 Tf\n12 TL\n64 {y} Td\n(- {w_line}) Tj\nET".encode("latin-1", "ignore").decode("latin-1"))
                    y -= 12
                    
    y -= 10
    y = draw_section_title("PRODUCTS & SERVICES", y)
    for p in products[:8]:
        wrapped_p = textwrap.wrap(p, width=80)
        for w_p in wrapped_p:
            content_lines.append(f"BT\n0.12 0.16 0.23 rg\n/F1 9 Tf\n13 TL\n44 {y} Td\n(* {w_p}) Tj\nET".encode("latin-1", "ignore").decode("latin-1"))
            y -= 14
            
    y -= 10
    y = draw_section_title("SUMMARY", y)
    for idx, pt in enumerate(summary_pts[:4], 1):
        wrapped_pt = textwrap.wrap(f"{idx}. {pt}", width=82)
        for w_line in wrapped_pt[:3]:
            content_lines.append(f"BT\n0.12 0.16 0.23 rg\n/F1 8.5 Tf\n12 TL\n44 {y} Td\n({w_line}) Tj\nET".encode("latin-1", "ignore").decode("latin-1"))
            y -= 13
        y -= 4
        
    y -= 6
    y = draw_section_title("COMPETITORS", y)
    for comp in competitors[:4]:
        c_str = f"{comp.get('name')}: {comp.get('website')}"
        content_lines.append(f"BT\n0.12 0.16 0.23 rg\n/F1 9 Tf\n13 TL\n44 {y} Td\n(- {c_str}) Tj\nET".encode("latin-1", "ignore").decode("latin-1"))
        y -= 14

    stream_content = "\n".join(content_lines)
    c_bytes = stream_content.encode("latin-1", "ignore")
    
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        f"5 0 obj\n<< /Length {len(c_bytes)} >>\nstream\n".encode("latin-1") + c_bytes + b"\nendstream\nendobj\n"
    ]
    
    offsets = []
    for obj in objects:
        offsets.append(out.tell())
        out.write(obj)
        
    xref_offset = out.tell()
    out.write(b"xref\n0 6\n0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode("latin-1"))
        
    out.write(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1"))
    return out.getvalue()
