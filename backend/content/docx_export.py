"""Convert generated-content HTML into a real Word (.docx) document.

The editor stores articles as HTML (``GeneratedContent.content_html``). The
front-end used to "export as Word" by relabelling that HTML as
``application/msword``, which Word opens under protest and Google Docs and
Pages often refuse outright. This module builds genuine OOXML with python-docx
instead, mapping the subset of tags the content generator actually emits.

Anything unrecognised degrades to a plain paragraph rather than being dropped,
so no text is ever lost in translation.
"""

import logging
from io import BytesIO

from bs4 import BeautifulSoup, NavigableString, Tag
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml.ns import qn
from docx.shared import Pt

logger = logging.getLogger(__name__)

# Tags that open a new block. Everything else is treated as inline content.
BLOCK_TAGS = frozenset({
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'div', 'section', 'article', 'header', 'footer', 'main',
    'ul', 'ol', 'table', 'blockquote', 'pre', 'hr', 'figure',
})

HEADING_LEVELS = {f'h{n}': n for n in range(1, 7)}

# Word ships List Bullet/Number styles for three indent levels only; deeper
# nesting reuses level 3 rather than raising KeyError on a missing style.
MAX_LIST_LEVEL = 3

# python-docx exposes no hyperlink API, so links are built from raw OOXML and
# need the hyperlink character style to look like links.
HYPERLINK_COLOR = '0563C1'


def build_docx(html, title=None):
    """Render ``html`` as a .docx and return the file bytes.

    ``title``, when given, is written as a Word Title-styled heading above the
    body so the exported file opens with the article name rather than starting
    mid-content.
    """
    document = Document()
    _apply_base_font(document)

    if title:
        document.add_heading(title, level=0)

    soup = BeautifulSoup(html or '', 'html.parser')
    root = soup.body or soup
    _add_blocks(document, root)

    # A document with no blocks at all still needs a body part to be valid.
    if not document.paragraphs and not document.tables:
        document.add_paragraph('')

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _apply_base_font(document):
    """Set a readable serif-free default; Word's Calibri 11pt is too tight."""
    style = document.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)
    style.paragraph_format.space_after = Pt(8)


def _add_blocks(container, node, list_level=0):
    """Walk ``node``'s children, emitting a block per block-level element.

    Loose text and inline tags between blocks are collected into an implicit
    paragraph so content outside a <p> is not silently discarded.
    """
    pending = []

    def flush():
        if not pending:
            return
        if any(_has_text(n) for n in pending):
            paragraph = container.add_paragraph()
            for item in pending:
                _add_inline(paragraph, item)
        pending.clear()

    for child in node.children:
        if isinstance(child, Tag) and child.name in BLOCK_TAGS:
            flush()
            _add_block(container, child, list_level)
        else:
            pending.append(child)

    flush()


def _add_block(container, tag, list_level):
    name = tag.name

    if name in HEADING_LEVELS:
        paragraph = container.add_paragraph(style=f'Heading {HEADING_LEVELS[name]}')
        _add_inline(paragraph, tag)
        return

    if name in ('ul', 'ol'):
        _add_list(container, tag, list_level)
        return

    if name == 'table':
        _add_table(container, tag)
        return

    if name == 'blockquote':
        paragraph = container.add_paragraph(style='Intense Quote')
        _add_inline(paragraph, tag)
        return

    if name == 'pre':
        paragraph = container.add_paragraph()
        run = paragraph.add_run(tag.get_text())
        run.font.name = 'Consolas'
        run.font.size = Pt(10)
        return

    if name == 'hr':
        container.add_paragraph('_' * 50).alignment = WD_ALIGN_PARAGRAPH.CENTER
        return

    # p, div and the generic wrappers. A wrapper holding further blocks is
    # recursed into so nested structure survives; otherwise it is one paragraph.
    if any(isinstance(c, Tag) and c.name in BLOCK_TAGS for c in tag.children):
        _add_blocks(container, tag, list_level)
        return

    if not _has_text(tag):
        return

    paragraph = container.add_paragraph()
    _add_inline(paragraph, tag)


def _add_list(container, tag, list_level):
    """Emit <li> items, recursing so nested lists get an indented Word style."""
    ordered = tag.name == 'ol'
    level = min(list_level + 1, MAX_LIST_LEVEL)
    base = 'List Number' if ordered else 'List Bullet'
    style = base if level == 1 else f'{base} {level}'

    for item in tag.find_all('li', recursive=False):
        nested = [c for c in item.children if isinstance(c, Tag) and c.name in ('ul', 'ol')]

        if _has_text(item):
            paragraph = container.add_paragraph(style=style)
            for child in item.children:
                if isinstance(child, Tag) and child.name in ('ul', 'ol'):
                    continue  # emitted below at the deeper level
                _add_inline(paragraph, child)

        for sublist in nested:
            _add_list(container, sublist, level)


def _add_table(container, tag):
    """Build a Word table from the HTML grid, padding ragged rows."""
    rows = tag.find_all('tr')
    if not rows:
        return

    widths = [len(r.find_all(['td', 'th'])) for r in rows]
    columns = max(widths)
    if not columns:
        return

    table = container.add_table(rows=0, cols=columns)
    table.style = 'Table Grid'

    for html_row in rows:
        cells = html_row.find_all(['td', 'th'])
        row = table.add_row()
        for index, html_cell in enumerate(cells[:columns]):
            cell = row.cells[index]
            # add_row seeds each cell with one empty paragraph — reuse it so the
            # cell does not open with a blank line.
            paragraph = cell.paragraphs[0]
            _add_inline(paragraph, html_cell)
            if html_cell.name == 'th':
                for run in paragraph.runs:
                    run.bold = True


def _add_inline(paragraph, node, bold=False, italic=False, underline=False):
    """Append ``node``'s text to ``paragraph``, carrying formatting down."""
    if isinstance(node, NavigableString):
        text = str(node)
        if not text.strip():
            return
        # Collapse HTML whitespace the way a browser would.
        run = paragraph.add_run(' '.join(text.split()) + ' ')
        run.bold = bold
        run.italic = italic
        run.underline = underline
        return

    if not isinstance(node, Tag):
        return

    name = node.name

    if name == 'br':
        paragraph.add_run().add_break()
        return

    # Images cannot be embedded without fetching remote bytes, which would turn
    # an export into an outbound request fan-out. Leave a visible placeholder.
    if name == 'img':
        alt = node.get('alt') or node.get('src') or 'image'
        run = paragraph.add_run(f'[image: {alt}] ')
        run.italic = True
        return

    if name == 'a' and node.get('href'):
        _add_hyperlink(paragraph, node.get('href'), node.get_text(strip=True))
        return

    bold = bold or name in ('strong', 'b', 'th')
    italic = italic or name in ('em', 'i')
    underline = underline or name == 'u'

    if name in ('code', 'kbd', 'samp'):
        run = paragraph.add_run(node.get_text() + ' ')
        run.font.name = 'Consolas'
        run.bold = bold
        run.italic = italic
        return

    for child in node.children:
        _add_inline(paragraph, child, bold, italic, underline)


def _add_hyperlink(paragraph, url, text):
    """Insert a real clickable hyperlink.

    python-docx has no API for this, so the w:hyperlink element is assembled by
    hand against a new relationship on the containing part.
    """
    if not text:
        text = url

    try:
        rel_id = paragraph.part.relate_to(
            url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True
        )
    except Exception:
        # A malformed href should cost the link, not the whole export.
        logger.warning('Skipping unusable hyperlink target in docx export')
        paragraph.add_run(text + ' ')
        return

    link = paragraph._p.makeelement(qn('w:hyperlink'), {})
    link.set(qn('r:id'), rel_id)

    run = paragraph._p.makeelement(qn('w:r'), {})
    properties = paragraph._p.makeelement(qn('w:rPr'), {})

    color = paragraph._p.makeelement(qn('w:color'), {})
    color.set(qn('w:val'), HYPERLINK_COLOR)
    properties.append(color)

    underline = paragraph._p.makeelement(qn('w:u'), {})
    underline.set(qn('w:val'), 'single')
    properties.append(underline)

    run.append(properties)

    text_element = paragraph._p.makeelement(qn('w:t'), {})
    text_element.text = text + ' '
    run.append(text_element)

    link.append(run)
    paragraph._p.append(link)


def _has_text(node):
    """True when the node contributes visible text or a line break."""
    if isinstance(node, NavigableString):
        return bool(str(node).strip())
    if isinstance(node, Tag):
        if node.name in ('br', 'img'):
            return True
        return bool(node.get_text(strip=True))
    return False
