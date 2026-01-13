"""
WeasyPrint PDF Generator
Generates PDFs from HTML templates with exact visual fidelity
"""
from io import BytesIO
from typing import Dict, Any
import logging

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    WEASYPRINT_AVAILABLE = False
    HTML = None
    CSS = None
    logging.warning(f"WeasyPrint not available: {e}. Will use ReportLab fallback.")

from .html_template_renderer import inject_widget_data


logger = logging.getLogger(__name__)


class WeasyPrintPDFGenerator:
    """
    Generate PDFs from HTML templates using WeasyPrint
    Preserves CSS styling, gradients, and layout
    """

    def __init__(self, html_template: str, css_template: str = ""):
        """
        Initialize PDF generator

        Args:
            html_template: HTML template with placeholders
            css_template: CSS styles (Tailwind CSS)
        """
        if not WEASYPRINT_AVAILABLE:
            raise ImportError(
                "WeasyPrint is not installed. Install it with: pip install weasyprint"
            )

        self.html_template = html_template
        self.css_template = css_template

    def generate(self, widget_data: Dict[str, Any], metadata: Dict[str, Any] = None) -> BytesIO:
        """
        Generate PDF from template with real data

        Args:
            widget_data: Dictionary mapping widget IDs to their data
            metadata: Template metadata (domain name, dates, etc.)

        Returns:
            BytesIO buffer containing PDF
        """
        try:
            # Inject widget data into HTML template
            complete_html = inject_widget_data(
                self.html_template,
                self.css_template,
                widget_data,
                metadata
            )

            logger.info(f"Generating PDF with WeasyPrint")
            logger.debug(f"HTML length: {len(complete_html)} characters")

            # Generate PDF
            pdf_bytes = self._html_to_pdf(complete_html)

            # Return as BytesIO buffer
            buffer = BytesIO(pdf_bytes)
            buffer.seek(0)

            logger.info(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")
            return buffer

        except Exception as e:
            logger.error(f"Error generating PDF with WeasyPrint: {str(e)}", exc_info=True)
            raise

    def _html_to_pdf(self, html_content: str) -> bytes:
        """
        Convert HTML to PDF using WeasyPrint

        Args:
            html_content: Complete HTML document

        Returns:
            PDF bytes
        """
        # Create HTML object
        html = HTML(string=html_content)

        # Generate PDF with options
        pdf_bytes = html.write_pdf(
            # Enable background colors and images (critical for gradients!)
            presentational_hints=True,
            # Optimize for screen display
            optimize_images=True,
        )

        return pdf_bytes

    @staticmethod
    def generate_from_template(
        html_template: str,
        css_template: str,
        widget_data: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> BytesIO:
        """
        Convenience method to generate PDF in one call

        Args:
            html_template: HTML with placeholders
            css_template: CSS styles
            widget_data: Widget data
            metadata: Template metadata

        Returns:
            BytesIO buffer containing PDF
        """
        generator = WeasyPrintPDFGenerator(html_template, css_template)
        return generator.generate(widget_data, metadata)


def convert_html_to_pdf_weasyprint(html_content: str) -> BytesIO:
    """
    Direct HTML to PDF conversion using WeasyPrint
    No template processing - just converts the HTML as-is

    Args:
        html_content: Complete HTML document

    Returns:
        BytesIO buffer containing PDF
    """
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("WeasyPrint is not available")

    try:
        logger.info("Converting HTML to PDF with WeasyPrint (direct)")

        # Create HTML object and generate PDF
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf(
            presentational_hints=True,
            optimize_images=True,
        )

        # Return as BytesIO buffer
        buffer = BytesIO(pdf_bytes)
        buffer.seek(0)

        logger.info(f"PDF generated successfully, size: {len(pdf_bytes)} bytes")
        return buffer

    except Exception as e:
        logger.error(f"Error converting HTML to PDF: {str(e)}", exc_info=True)
        raise


def test_weasyprint_installation():
    """Test if WeasyPrint is properly installed and working"""
    if not WEASYPRINT_AVAILABLE:
        return False, "WeasyPrint is not installed"

    try:
        # Test basic HTML to PDF conversion
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .test { color: blue; }
            </style>
        </head>
        <body>
            <h1 class="test">WeasyPrint Test</h1>
            <p>This is a test PDF.</p>
        </body>
        </html>
        """
        html = HTML(string=test_html)
        pdf_bytes = html.write_pdf()

        if len(pdf_bytes) > 0:
            return True, "WeasyPrint is working correctly"
        else:
            return False, "WeasyPrint generated empty PDF"

    except Exception as e:
        return False, f"WeasyPrint test failed: {str(e)}"


# Test on module load (for debugging)
if __name__ == "__main__":
    success, message = test_weasyprint_installation()
    print(f"WeasyPrint Status: {message}")
