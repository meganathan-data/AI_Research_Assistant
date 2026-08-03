"""
PDF Report Generator Engine for CorpIntel AI.
Builds styled corporate PDF reports matching the Dribbble Neumorphic Web Application theme.
Header: Dark Charcoal (#1f2023)
Subheader: Bright Warm Coral (#f97316) CORPINTEL AI · COMPANY RESEARCH & INTELLIGENCE REPORT
Headings: Warm Coral (#f97316) with Orange Underline
Data Containers: Light Gray (#f8fafc) background with (#e2e8f0) border
"""

import io
from typing import Any

def generate_pdf_report(report: dict[str, Any]) -> bytes:
    """Generates PDF report matching Dribbble website theme styling."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
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

        story = []

        comp_name = report.get("company_name", "Company Report")
        target_city = report.get("target_city", "")
        
        display_title = f"{comp_name} {target_city}".strip() if target_city and target_city.lower() not in comp_name.lower() else comp_name

        header_data = [
            [
                Paragraph('<font color="#f97316" size=8><b>CORPINTEL AI · COMPANY RESEARCH & INTELLIGENCE REPORT</b></font>', getSampleStyleSheet()['Normal']),
            ],
            [
                Paragraph(f'<font color="#ffffff" size=18><b>{display_title}</b></font>', getSampleStyleSheet()['Normal']),
            ]
        ]
        
        header_table = Table(header_data, colWidths=[540])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1f2023')),
            ('PADDING', (0,0), (-1,-1), 14),
            ('BOTTOMPADDING', (0,0), (-1,0), 2),
            ('TOPPADDING', (0,1), (-1,1), 2),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 16))

        title_style = ParagraphStyle(
            'SectionHeader',
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#f97316'),
            spaceAfter=3
        )
        
        body_style = ParagraphStyle(
            'BodyDark',
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1e293b')
        )
        
        bold_label_style = ParagraphStyle(
            'BoldLabel',
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1e293b')
        )

        def add_orange_heading(title_text):
            story.append(Paragraph(f"<b>{title_text}</b>", title_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#f97316'), spaceAfter=8, spaceBefore=2))

        add_orange_heading("COMPANY INFORMATION")

        locs = report.get("locations", {})
        countries = locs.get("countries", [])
        loc_paragraphs = []
        for c in countries:
            c_name = c.get("country_name", "")
            loc_paragraphs.append(f'<font color="#f97316"><b>{c_name}</b></font>')
            for city in c.get("cities", []):
                c_city = city.get("city_name", "")
                addrs = ", ".join(city.get("addresses", []))
                loc_paragraphs.append(f'• <b>{c_city}</b>: {addrs}')

        loc_cell_html = "<br/>".join(loc_paragraphs) if loc_paragraphs else "Global Enterprise Facilities"

        info_data = [
            [Paragraph('<b>Website</b>', bold_label_style), Paragraph(f'<font color="#f97316">{report.get("website", "")}</font>', body_style)],
            [Paragraph('<b>Branch Locations</b>', bold_label_style), Paragraph(loc_cell_html, body_style)]
        ]

        info_table = Table(info_data, colWidths=[110, 430])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 14))

        add_orange_heading("PRODUCTS & SERVICES")
        prods = report.get("products_and_services", [])
        for p in prods:
            story.append(Paragraph(f"• {p}", body_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 10))

        add_orange_heading("SUMMARY & BRANCH OPERATIONS")
        summary_items = report.get("summary") or report.get("pain_points") or []
        for idx, item in enumerate(summary_items, 1):
            story.append(Paragraph(f"<b>{idx}.</b> {item}", body_style))
            story.append(Spacer(1, 6))

        ip = report.get("interview_prep", {})
        if ip:
            story.append(Spacer(1, 10))
            add_orange_heading("INTERVIEW PREPARATION & COMPANY ESSENTIALS")
            kf = ip.get("key_facts", {})
            kf_html = f"<b>Founded:</b> {kf.get('founded', 'N/A')} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Parent:</b> {kf.get('parent_organization', 'N/A')} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Leadership:</b> {kf.get('leadership', 'N/A')}<br/><b>Global Headcount:</b> {kf.get('global_headcount', 'N/A')}"
            
            kf_table = Table([[Paragraph(kf_html, body_style)]], colWidths=[540])
            kf_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(kf_table)
            story.append(Spacer(1, 8))

            culture = ip.get("work_culture_and_values", "")
            if culture:
                story.append(Paragraph("<b>Work Culture & Values:</b>", bold_label_style))
                story.append(Paragraph(culture, body_style))
                story.append(Spacer(1, 6))

            questions = ip.get("top_interview_questions", [])
            if questions:
                story.append(Paragraph("<b>Frequently Asked Interview Questions:</b>", title_style))
                for q_idx, q in enumerate(questions, 1):
                    story.append(Paragraph(f"<b>Q{q_idx}:</b> {q}", body_style))
                    story.append(Spacer(1, 4))

        doc.build(story)
        return buffer.getvalue()

    except Exception as e:
        print(f"[ReportLab Generation Exception]: {e}. Falling back to pure-vector PDF builder.")
        return generate_pure_vector_pdf_fallback(report)


def generate_pure_vector_pdf_fallback(report: dict[str, Any]) -> bytes:
    """Pure Python vector PDF fallback generator using Dribbble Orange website theme."""
    comp_name = report.get("company_name", "Company Report")
    target_city = report.get("target_city", "")
    display_title = f"{comp_name} {target_city}".strip() if target_city and target_city.lower() not in comp_name.lower() else comp_name

    pdf_content = []
    pdf_content.append("%PDF-1.4\n")
    pdf_content.append("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    pdf_content.append("2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    pdf_content.append("3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >> endobj\n")
    pdf_content.append("4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj\n")
    pdf_content.append("5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")

    stream = []
    # Dark Header Banner (#1f2023)
    stream.append("0.12 0.13 0.14 rg\n")
    stream.append("36 696 540 60 re f\n")

    # Header Text
    stream.append("BT /F1 8 Tf 0.97 0.45 0.09 rg 52 736 Td (CORPINTEL AI - COMPANY RESEARCH & INTELLIGENCE REPORT) Tj ET\n")
    stream.append(f"BT /F1 18 Tf 1 1 1 rg 52 710 Td ({clean_pdf_str(display_title)}) Tj ET\n")

    # Section 1: COMPANY INFORMATION
    stream.append("BT /F1 10 Tf 0.97 0.45 0.09 rg 36 670 Td (COMPANY INFORMATION) Tj ET\n")
    stream.append("0.97 0.45 0.09 RG 1 w 36 664 m 576 664 l S\n")

    # Box
    stream.append("0.97 0.98 0.99 rg 36 524 540 130 re f\n")
    stream.append("0.88 0.90 0.94 RG 0.5 w 36 524 540 130 re S\n")
    stream.append("146 524 m 146 654 l S\n")

    # Table Text
    stream.append("BT /F1 9 Tf 0.12 0.16 0.23 rg 46 634 Td (Website) Tj ET\n")
    stream.append(f"BT /F2 9 Tf 0.97 0.45 0.09 rg 156 634 Td ({clean_pdf_str(report.get('website',''))}) Tj ET\n")
    stream.append("BT /F1 9 Tf 0.12 0.16 0.23 rg 46 608 Td (Branch Locations) Tj ET\n")

    y_loc = 608
    locs = report.get("locations", {})
    for c in locs.get("countries", []):
        if y_loc < 535: break
        stream.append(f"BT /F1 9 Tf 0.97 0.45 0.09 rg 156 {y_loc} Td ({clean_pdf_str(c.get('country_name',''))}) Tj ET\n")
        y_loc -= 14
        for city in c.get("cities", []):
            if y_loc < 535: break
            addrs = ", ".join(city.get("addresses", []))
            stream.append(f"BT /F2 8.5 Tf 0.2 0.25 0.3 rg 166 {y_loc} Td (- {clean_pdf_str(city.get('city_name',''))}: {clean_pdf_str(addrs[:50])}) Tj ET\n")
            y_loc -= 12

    # Section 2: PRODUCTS & SERVICES
    stream.append("BT /F1 10 Tf 0.97 0.45 0.09 rg 36 498 Td (PRODUCTS & SERVICES) Tj ET\n")
    stream.append("0.97 0.45 0.09 RG 1 w 36 492 m 576 492 l S\n")

    y_prod = 476
    for p in report.get("products_and_services", [])[:4]:
        stream.append(f"BT /F2 9 Tf 0.1 0.1 0.1 rg 46 {y_prod} Td (- {clean_pdf_str(p)}) Tj ET\n")
        y_prod -= 14

    # Section 3: SUMMARY
    stream.append(f"BT /F1 10 Tf 0.97 0.45 0.09 rg 36 {y_prod - 10} Td (SUMMARY & BRANCH OPERATIONS) Tj ET\n")
    stream.append(f"0.97 0.45 0.09 RG 1 w 36 {y_prod - 16} m 576 {y_prod - 16} l S\n")

    y_sum = y_prod - 30
    for idx, s in enumerate(report.get("summary", [])[:5], 1):
        stream.append(f"BT /F2 8.5 Tf 0.1 0.1 0.1 rg 46 {y_sum} Td ({idx}. {clean_pdf_str(s[:85])}) Tj ET\n")
        y_sum -= 14

    # Section 4: INTERVIEW PREPARATION
    ip = report.get("interview_prep", {})
    if ip:
        stream.append(f"BT /F1 10 Tf 0.97 0.45 0.09 rg 36 {y_sum - 10} Td (INTERVIEW PREPARATION & COMPANY ESSENTIALS) Tj ET\n")
        stream.append(f"0.97 0.45 0.09 RG 1 w 36 {y_sum - 16} m 576 {y_sum - 16} l S\n")
        kf = ip.get("key_facts", {})
        stream.append(f"BT /F2 8.5 Tf 0.1 0.1 0.1 rg 46 {y_sum - 30} Td (Founded: {clean_pdf_str(kf.get('founded','N/A'))} | Parent: {clean_pdf_str(kf.get('parent_organization','N/A'))} | CEO: {clean_pdf_str(kf.get('leadership','N/A'))}) Tj ET\n")

    stream_str = "".join(stream)
    stream_len = len(stream_str)

    pdf_content.append(f"6 0 obj << /Length {stream_len} >> stream\n{stream_str}endstream\nendobj\n")

    pdf_content.append("xref\n0 7\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000262 00000 n \n0000000333 00000 n \n0000000400 00000 n \n")
    pdf_content.append("trailer << /Size 7 /Root 1 0 R >>\nstartxref\n1500\n%%EOF")

    return "".join(pdf_content).encode("latin-1", "ignore")

def clean_pdf_str(val: str) -> str:
    """Escapes parenthesis for raw PDF syntax."""
    return str(val).replace("(", "\\(").replace(")", "\\)")
