from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime


class ProformaPDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()

        # Title style - bold, centered
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=14,
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=16,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )

        # Table header cell style
        self.header_cell_style = ParagraphStyle(
            'HeaderCell',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            textColor=colors.white,
            alignment=TA_CENTER,
            leading=10,
        )

        # Table data cell style - centered
        self.cell_style = ParagraphStyle(
            'CellCenter',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica',
            alignment=TA_CENTER,
            leading=10,
        )

        # Table data cell style - left aligned (for text)
        self.cell_left_style = ParagraphStyle(
            'CellLeft',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica',
            alignment=TA_LEFT,
            leading=10,
        )

        # Footer style
        self.footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=7,
            alignment=TA_RIGHT,
            textColor=colors.grey,
            spaceBefore=12,
        )

    def _make_header_cell(self, text):
        """Wrap header text in a styled Paragraph for word-wrapping."""
        return Paragraph(text, self.header_cell_style)

    def _make_cell(self, text, left=False):
        """Wrap data text in a styled Paragraph for word-wrapping."""
        style = self.cell_left_style if left else self.cell_style
        return Paragraph(str(text), style)

    def _base_table_style(self):
        """Return a common base table style list."""
        return [
            # Header row background
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            # Header bottom border
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#1a252f')),
            # Vertical alignment
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Padding
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]

    def generate_proforma_1a(self, data, filename="Proforma_1A.pdf"):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )
        elements = []

        # Title
        elements.append(Paragraph("PROFORMA - IA", self.title_style))
        elements.append(Paragraph("List of students having attendance &lt; 65%", self.subtitle_style))
        elements.append(Spacer(1, 0.1 * inch))

        # Table Header (using Paragraphs for wrapping)
        headers = [
            self._make_header_cell("Sl.\nNo."),
            self._make_header_cell("Register\nNo."),
            self._make_header_cell("Student Name"),
            self._make_header_cell("Subject"),
            self._make_header_cell("Hrs.\nAttended"),
            self._make_header_cell("Hrs.\nConducted"),
            self._make_header_cell("Hrs.\nPosted"),
            self._make_header_cell("Attendance\n%"),
            self._make_header_cell("Reason for not\nbeing eligible"),
        ]

        # Table Data
        table_data = [headers]
        for i, row in enumerate(data):
            entry = row.get("proforma_entry") or {}
            table_data.append([
                self._make_cell(str(i + 1)),
                self._make_cell(row.get("student_id", "")),
                self._make_cell(row.get("student_name", "") or "", left=True),
                self._make_cell(
                    f"{row.get('subject_code', '')} - {row.get('subject_name', '')}",
                    left=True
                ),
                self._make_cell(str(row.get("classes_attended", 0))),
                self._make_cell(str(row.get("classes_conducted", 0))),
                self._make_cell(str(row.get("classes_posted", 0))),
                self._make_cell(f"{row.get('attendance_percentage', 0):.2f}%"),
                self._make_cell(entry.get("reason", "") or "", left=True),
            ])

        # Column widths optimized for A4 Landscape (~10.5 inches usable)
        # Sl:0.4  Reg:1.0  Name:1.6  Subject:2.4  Att:0.6  Con:0.7  Pos:0.6  %:0.7  Reason:2.5 = 10.5
        col_widths = [
            0.4 * inch,   # Sl. No.
            1.0 * inch,   # Register No.
            1.6 * inch,   # Name
            2.4 * inch,   # Subject
            0.6 * inch,   # Attended
            0.7 * inch,   # Conducted
            0.6 * inch,   # Posted
            0.7 * inch,   # %
            2.5 * inch,   # Reason
        ]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        style = self._base_table_style()
        table.setStyle(TableStyle(style))

        elements.append(table)

        # Footer with generation timestamp
        now = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        elements.append(Paragraph(f"Generated on: {now}", self.footer_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    def generate_proforma_1b(self, data, filename="Proforma_1B.pdf"):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )
        elements = []

        # Title
        elements.append(Paragraph("PROFORMA - IB", self.title_style))
        elements.append(Paragraph("List of students having attendance 65% - 74%", self.subtitle_style))
        elements.append(Spacer(1, 0.1 * inch))

        # Table Header
        headers = [
            self._make_header_cell("Sl.\nNo."),
            self._make_header_cell("Register\nNo."),
            self._make_header_cell("Student Name"),
            self._make_header_cell("Subject"),
            self._make_header_cell("Hrs.\nAttended"),
            self._make_header_cell("Hrs.\nConducted"),
            self._make_header_cell("Hrs.\nPosted"),
            self._make_header_cell("Attendance\n%"),
            self._make_header_cell("Reason for\nRecommendation"),
            self._make_header_cell("Status"),
        ]

        # Table Data
        table_data = [headers]
        for i, row in enumerate(data):
            entry = row.get("proforma_entry") or {}
            status = entry.get("status", "Pending")
            table_data.append([
                self._make_cell(str(i + 1)),
                self._make_cell(row.get("student_id", "")),
                self._make_cell(row.get("student_name", "") or "", left=True),
                self._make_cell(
                    f"{row.get('subject_code', '')} - {row.get('subject_name', '')}",
                    left=True
                ),
                self._make_cell(str(row.get("classes_attended", 0))),
                self._make_cell(str(row.get("classes_conducted", 0))),
                self._make_cell(str(row.get("classes_posted", 0))),
                self._make_cell(f"{row.get('attendance_percentage', 0):.2f}%"),
                self._make_cell(entry.get("reason", "") or "", left=True),
                self._make_cell(status),
            ])

        # Column widths optimized for A4 Landscape (~10.5 inches usable)
        # Sl:0.35  Reg:0.95  Name:1.4  Subject:2.1  Att:0.55  Con:0.6  Pos:0.55  %:0.7  Reason:2.0  Status:0.8 = 10.0
        col_widths = [
            0.35 * inch,  # Sl. No.
            0.95 * inch,  # Register No.
            1.4 * inch,   # Name
            2.1 * inch,   # Subject
            0.55 * inch,  # Attended
            0.6 * inch,   # Conducted
            0.55 * inch,  # Posted
            0.7 * inch,   # %
            2.0 * inch,   # Reason
            0.8 * inch,   # Status
        ]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        style = self._base_table_style()
        # Color the Status column for Approved entries
        for i, row in enumerate(data):
            entry = row.get("proforma_entry") or {}
            if entry.get("status") == "Approved":
                style.append(('TEXTCOLOR', (9, i + 1), (9, i + 1), colors.HexColor('#28a745')))

        table.setStyle(TableStyle(style))

        elements.append(table)

        # Footer with generation timestamp
        now = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        elements.append(Paragraph(f"Generated on: {now}", self.footer_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer
