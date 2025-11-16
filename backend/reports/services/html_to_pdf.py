"""
HTML to PDF Converter using xhtml2pdf
Converts the exact HTML from frontend React template to PDF
"""
from io import BytesIO
from xhtml2pdf import pisa
import logging

logger = logging.getLogger(__name__)


def convert_html_to_pdf(html_content: str, css_content: str = None) -> BytesIO:
    """
    Convert HTML string to PDF

    Args:
        html_content: HTML string (complete HTML document)
        css_content: Optional CSS string to include

    Returns:
        BytesIO: PDF file buffer
    """
    try:
        # Create BytesIO buffer for PDF
        pdf_buffer = BytesIO()

        # Base CSS for better PDF rendering
        base_css = """
        <style>
        @page {
            size: A4;
            margin: 1cm;
        }
        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #000;
        }
        h1 { font-size: 24pt; margin-bottom: 12pt; }
        h2 { font-size: 18pt; margin-bottom: 10pt; margin-top: 16pt; }
        h3 { font-size: 14pt; margin-bottom: 8pt; }
        h4 { font-size: 12pt; margin-bottom: 6pt; }
        p { margin-bottom: 8pt; }
        .page-break { page-break-after: always; }
        img { max-width: 100%; height: auto; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 12pt; }
        th, td { padding: 6pt; border: 1px solid #ddd; text-align: left; }
        th { background-color: #f5f5f5; font-weight: bold; }
        </style>
        """

        # Add custom CSS if provided
        if css_content:
            base_css += f"<style>{css_content}</style>"

        # Insert CSS into HTML if it doesn't have a head tag
        if '<head>' in html_content:
            html_content = html_content.replace('<head>', f'<head>{base_css}')
        else:
            html_content = html_content.replace('<html>', f'<html><head>{base_css}</head>')

        # Convert HTML to PDF
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)

        # Check for errors
        if pisa_status.err:
            raise Exception("PDF conversion encountered errors")

        # Reset buffer position
        pdf_buffer.seek(0)

        logger.info("Successfully converted HTML to PDF")
        return pdf_buffer

    except Exception as e:
        logger.error(f"Error converting HTML to PDF: {str(e)}")
        raise Exception(f"PDF conversion failed: {str(e)}")
