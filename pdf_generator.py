"""
PDF Report Generator - Creates hospital-style A4 medical reports.
Uses ReportLab for PDF generation and qrcode for QR codes.
"""
import io
import os
import qrcode
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics import renderPDF


# Color scheme
PRIMARY = HexColor("#0F172A")
ACCENT = HexColor("#3B82F6")
SUCCESS = HexColor("#22C55E")
WARNING = HexColor("#F59E0B")
DANGER = HexColor("#EF4444")
LIGHT_BG = HexColor("#F8FAFC")
BORDER = HexColor("#E2E8F0")
TEXT_SECONDARY = HexColor("#64748B")

FEATURE_LABELS = {
    "gender": "Gender",
    "height": "Height (cm)",
    "weight": "Weight (kg)",
    "ap_hi": "Systolic BP (mmHg)",
    "ap_lo": "Diastolic BP (mmHg)",
    "cholesterol": "Cholesterol Level",
    "gluc": "Glucose Level",
    "smoke": "Smoking",
    "alco": "Alcohol Intake",
    "active": "Physical Activity",
    "age_years": "Age (Years)",
    "bmi": "BMI",
    "MAP": "Mean Arterial Pressure",
}

FEATURE_VALUE_MAP = {
    "gender": {1: "Female", 2: "Male"},
    "cholesterol": {1: "Normal", 2: "Above Normal", 3: "Well Above Normal"},
    "gluc": {1: "Normal", 2: "Above Normal", 3: "Well Above Normal"},
    "smoke": {0: "No", 1: "Yes"},
    "alco": {0: "No", 1: "Yes"},
    "active": {0: "No", 1: "Yes"},
}


def _get_risk_color(risk_level: str):
    if risk_level == "Low":
        return SUCCESS
    elif risk_level == "Medium":
        return WARNING
    return DANGER


def _generate_qr_code(data: str) -> Image:
    """Generate a QR code image for report verification."""
    qr = qrcode.QRCode(version=1, box_size=3, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return Image(buffer, width=22*mm, height=22*mm)


def _format_value(key: str, value) -> str:
    """Format medical input values for display."""
    if key in FEATURE_VALUE_MAP and isinstance(value, (int, float)):
        return FEATURE_VALUE_MAP[key].get(int(value), str(value))
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def generate_report_pdf(record) -> bytes:
    """
    Generate a hospital-style A4 PDF report.
    
    Args:
        record: PredictionRecord from database
        
    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18*mm,
        rightMargin=18*mm,
        topMargin=15*mm,
        bottomMargin=20*mm,
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=PRIMARY,
        spaceAfter=2*mm,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )
    
    subtitle_style = ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=TEXT_SECONDARY,
        alignment=TA_CENTER,
        spaceAfter=4*mm,
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=ACCENT,
        spaceBefore=6*mm,
        spaceAfter=3*mm,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderPadding=0,
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=9,
        textColor=TEXT_SECONDARY,
        fontName='Helvetica',
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=10,
        textColor=PRIMARY,
        fontName='Helvetica-Bold',
    )
    
    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=9,
        textColor=PRIMARY,
        fontName='Helvetica',
        leading=13,
    )
    
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=7,
        textColor=TEXT_SECONDARY,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique',
    )
    
    elements = []
    
    # ========================
    # HEADER
    # ========================
    hospital_name = record.hospital_name or "CardioGuard AI Medical Center"
    
    header_data = [
        [
            Paragraph(f'<font size="16" color="#{ACCENT.hexval()[2:]}">\u2764</font>', 
                      ParagraphStyle('icon', alignment=TA_CENTER, fontSize=16)),
            [
                Paragraph(f'<b>{hospital_name}</b>', 
                         ParagraphStyle('HospName', fontSize=14, textColor=PRIMARY, fontName='Helvetica-Bold', alignment=TA_CENTER)),
                Paragraph('AI-Powered Cardiovascular Risk Assessment Report', subtitle_style),
            ],
            Paragraph(f'<font size="8" color="#{TEXT_SECONDARY.hexval()[2:]}">Report ID:<br/><b>{record.id[:8].upper()}</b></font>', 
                      ParagraphStyle('rid', fontSize=8, textColor=TEXT_SECONDARY, alignment=TA_RIGHT)),
        ]
    ]
    
    header_table = Table(header_data, colWidths=[15*mm, 130*mm, 30*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    elements.append(header_table)
    
    # Divider
    elements.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=4*mm))
    
    # ========================
    # PATIENT DETAILS
    # ========================
    elements.append(Paragraph("👤 Patient Information", section_header_style))
    
    gender_display = record.patient_gender or ("Male" if record.medical_inputs.get("gender") == 2 else "Female")
    
    patient_data = [
        [Paragraph('<b>Full Name</b>', label_style), 
         Paragraph(record.patient_name, value_style),
         Paragraph('<b>Age</b>', label_style), 
         Paragraph(str(record.patient_age), value_style)],
        [Paragraph('<b>Gender</b>', label_style), 
         Paragraph(gender_display, value_style),
         Paragraph('<b>Phone</b>', label_style), 
         Paragraph(record.patient_phone or "N/A", value_style)],
        [Paragraph('<b>Email</b>', label_style), 
         Paragraph(record.patient_email or "N/A", value_style),
         Paragraph('<b>Address</b>', label_style), 
         Paragraph(record.patient_address or "N/A", value_style)],
    ]
    
    patient_table = Table(patient_data, colWidths=[30*mm, 55*mm, 30*mm, 55*mm])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
        ('ROUNDEDCORNERS', [2, 2, 2, 2]),
    ]))
    elements.append(patient_table)
    
    # ========================
    # DOCTOR DETAILS
    # ========================
    if record.doctor_name:
        elements.append(Paragraph("🩺 Doctor Information", section_header_style))
        doctor_data = [
            [Paragraph('<b>Doctor Name</b>', label_style), 
             Paragraph(record.doctor_name or "N/A", value_style),
             Paragraph('<b>Hospital/Clinic</b>', label_style), 
             Paragraph(record.hospital_name or "N/A", value_style)],
        ]
        doctor_table = Table(doctor_data, colWidths=[30*mm, 55*mm, 30*mm, 55*mm])
        doctor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
        ]))
        elements.append(doctor_table)
    
    # ========================
    # MEDICAL DATA TABLE
    # ========================
    elements.append(Paragraph("📋 Medical Parameters", section_header_style))
    
    medical_data = [[
        Paragraph('<b>Parameter</b>', ParagraphStyle('th', fontSize=9, textColor=white, fontName='Helvetica-Bold')),
        Paragraph('<b>Value</b>', ParagraphStyle('th', fontSize=9, textColor=white, fontName='Helvetica-Bold')),
        Paragraph('<b>Parameter</b>', ParagraphStyle('th', fontSize=9, textColor=white, fontName='Helvetica-Bold')),
        Paragraph('<b>Value</b>', ParagraphStyle('th', fontSize=9, textColor=white, fontName='Helvetica-Bold')),
    ]]
    
    medical_inputs = record.medical_inputs or {}
    items = list(medical_inputs.items())
    
    for i in range(0, len(items), 2):
        row = []
        k1, v1 = items[i]
        row.append(Paragraph(FEATURE_LABELS.get(k1, k1), normal_style))
        row.append(Paragraph(f'<b>{_format_value(k1, v1)}</b>', normal_style))
        
        if i + 1 < len(items):
            k2, v2 = items[i + 1]
            row.append(Paragraph(FEATURE_LABELS.get(k2, k2), normal_style))
            row.append(Paragraph(f'<b>{_format_value(k2, v2)}</b>', normal_style))
        else:
            row.extend([Paragraph('', normal_style), Paragraph('', normal_style)])
        
        medical_data.append(row)
    
    medical_table = Table(medical_data, colWidths=[40*mm, 40*mm, 40*mm, 40*mm])
    medical_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), ACCENT),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
    ]))
    elements.append(medical_table)
    
    # ========================
    # AI PREDICTION RESULT
    # ========================
    elements.append(Paragraph("🤖 AI Prediction Result", section_header_style))
    
    risk_color = _get_risk_color(record.risk_level)
    prediction_label = "Cardiovascular Disease Detected" if record.prediction == 1 else "No Cardiovascular Disease"
    
    result_data = [
        [
            Paragraph('<b>Prediction</b>', label_style),
            Paragraph(f'<b>{prediction_label}</b>', 
                     ParagraphStyle('pred', fontSize=12, textColor=risk_color, fontName='Helvetica-Bold')),
        ],
        [
            Paragraph('<b>Probability Score</b>', label_style),
            Paragraph(f'<b>{record.probability:.1f}%</b>', value_style),
        ],
        [
            Paragraph('<b>Risk Level</b>', label_style),
            Paragraph(f'<b>{record.risk_level} Risk</b>', 
                     ParagraphStyle('risk', fontSize=12, textColor=risk_color, fontName='Helvetica-Bold')),
        ],
    ]
    
    result_table = Table(result_data, colWidths=[40*mm, 130*mm])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
    ]))
    elements.append(result_table)
    
    # ========================
    # RECOMMENDATIONS
    # ========================
    elements.append(Paragraph("💡 Health Recommendations", section_header_style))
    
    recommendations = record.recommendations or []
    for i, rec in enumerate(recommendations):
        # Clean emoji for PDF compatibility
        clean_rec = rec.replace("⚠️", "[!]").replace("⚕️", "[*]")
        elements.append(Paragraph(
            f'<bullet>&bull;</bullet> {clean_rec}',
            ParagraphStyle('rec', fontSize=9, textColor=PRIMARY, fontName='Helvetica',
                          leftIndent=8*mm, bulletIndent=3*mm, leading=13, spaceBefore=1*mm)
        ))
    
    elements.append(Spacer(1, 8*mm))
    
    # ========================
    # FOOTER
    # ========================
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=3*mm))
    
    # QR code and footer info
    report_time = record.created_at
    if isinstance(report_time, datetime):
        time_str = report_time.strftime("%d %B %Y, %I:%M %p")
    else:
        time_str = str(report_time)
    
    qr_data = f"CardioGuard-Report-{record.id}"
    qr_img = _generate_qr_code(qr_data)
    
    footer_data = [
        [
            qr_img,
            [
                Paragraph(f'<b>Report Generated:</b> {time_str}', 
                         ParagraphStyle('ft', fontSize=8, textColor=TEXT_SECONDARY)),
                Paragraph(f'<b>Report ID:</b> {record.id}', 
                         ParagraphStyle('ft2', fontSize=8, textColor=TEXT_SECONDARY, spaceBefore=1*mm)),
                Paragraph('Scan QR code for report verification', 
                         ParagraphStyle('ft3', fontSize=7, textColor=TEXT_SECONDARY, spaceBefore=1*mm, 
                                       fontName='Helvetica-Oblique')),
            ],
        ]
    ]
    
    footer_table = Table(footer_data, colWidths=[28*mm, 140*mm])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(footer_table)
    
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        "⚕ This report is generated using AI-assisted analysis and is NOT a final medical diagnosis. "
        "Please consult a qualified healthcare professional for medical advice and treatment decisions.",
        disclaimer_style
    ))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(
        f"© {datetime.now().year} CardioGuard AI — Powered by Machine Learning",
        ParagraphStyle('copyright', fontSize=7, textColor=TEXT_SECONDARY, alignment=TA_CENTER)
    ))
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
