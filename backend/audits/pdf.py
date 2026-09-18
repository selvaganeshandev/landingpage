"""Audit Engine — the downloadable, designed PDF of a published audit.

Built with ReportLab (pure Python, already a dependency, works on every
platform) rather than WeasyPrint, which needs GTK libraries that are not
installed everywhere the backend runs. The PDF renders the same
`Audit.report` JSON the web page does, so the two never disagree; every read
is defensive (`.get` with defaults) because reports written by older engine
versions may lack newer blocks (funnel, competitors, crawl, plan, narrative,
summary).

Layout (A4, five parts, like an agency deliverable):

    cover                    score, band, headline tiles, prepared-for block
    contents                 numbered parts with page numbers (two-pass build)
    01 Executive summary     key findings, top-3 actions, maturity ladder, visibility depth
    02 AI search visibility  engines chart + cards, funnel heatmap, win/lose,
                             prompt evidence, competitor matrix, share of voice,
                             citation control, brand narrative
    03 Website health        scorecard, crawler checklist, signals, page table
    04 90-day plan           Now / Next / Later, KPI targets, quick wins
    05 Appendices            methodology, scoring model, limitations, glossary

Public API:
    build_audit_pdf(audit) -> bytes
"""
import io
import os
import re
import tempfile
from datetime import datetime

from django.conf import settings
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Circle, Drawing, Rect, String, Wedge
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Flowable, Frame, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ---- palette (matches the web app) -------------------------------------------------
PRIMARY = colors.HexColor('#7c3aed')
PRIMARY_DARK = colors.HexColor('#4c1d95')
PRIMARY_TINT = colors.HexColor('#f5f3ff')
INK = colors.HexColor('#111827')
MUTED = colors.HexColor('#6b7280')
LINE = colors.HexColor('#e5e7eb')
SOFT = colors.HexColor('#f9fafb')
GREEN = colors.HexColor('#059669')
GREEN_BG = colors.HexColor('#ecfdf5')
AMBER = colors.HexColor('#d97706')
AMBER_BG = colors.HexColor('#fffbeb')
RED = colors.HexColor('#dc2626')
RED_BG = colors.HexColor('#fef2f2')
MUTED_BG = colors.HexColor('#f3f4f6')
WHITE = colors.white

GEO_BANDS = [
    # key, label, lo, hi, colour, one-line meaning
    ('absent', 'Absent', 0, 25, RED, 'The engines rarely name you'),
    ('present', 'Present', 26, 50, AMBER, 'Named, but not the answer'),
    ('preferred', 'Preferred', 51, 75, PRIMARY, 'A recommended option'),
    ('default', 'Default', 76, 100, GREEN, 'The answer the engines give'),
]
BAND = {b[0]: b for b in GEO_BANDS}
GAP_LABELS = {'won': ('Won', GREEN), 'position_gap': ('Position gap', AMBER), 'visibility_gap': ('Visibility gap', RED),
              'educational': ('Educational', MUTED), 'no_data': ('No answer', MUTED)}
OUTCOME = {'cited': GREEN, 'mentioned': AMBER, 'absent': RED, 'failed': MUTED}
COUNTRY_NAMES = {'us': 'United States', 'gb': 'United Kingdom', 'ca': 'Canada', 'au': 'Australia', 'de': 'Germany',
                 'fr': 'France', 'es': 'Spain', 'it': 'Italy', 'jp': 'Japan', 'in': 'India', 'br': 'Brazil',
                 'mx': 'Mexico', 'nl': 'Netherlands', 'se': 'Sweden', 'no': 'Norway', 'dk': 'Denmark', 'fi': 'Finland',
                 'pl': 'Poland', 'be': 'Belgium', 'at': 'Austria', 'ch': 'Switzerland', 'ie': 'Ireland',
                 'nz': 'New Zealand', 'sg': 'Singapore', 'ae': 'United Arab Emirates'}

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
W = PAGE_W - 2 * MARGIN
SECONDARY = colors.HexColor('#c084fc')   # brand magenta accent
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
_LOGO_CACHE = {}


def _logo(white=False):
    """Path to the PromptMaxx logo PNG; `white` derives a white-on-transparent copy for dark bands. None if missing."""
    key = 'white' if white else 'dark'
    if key in _LOGO_CACHE:
        return _LOGO_CACHE[key]
    path = os.path.join(ASSETS, 'logo.png')
    out = None
    try:
        if os.path.exists(path):
            if not white:
                out = path
            else:
                out = os.path.join(tempfile.gettempdir(), 'promptmaxx-logo-white.png')
                if not os.path.exists(out):
                    from PIL import Image
                    im = Image.open(path).convert('RGBA')
                    px = im.load()
                    for y in range(im.height):
                        for x in range(im.width):
                            r, g, b, a = px[x, y]
                            ink = min(255, (255 - (r + g + b) // 3) * 3)   # coloured pixels become solid white, edges stay soft
                            px[x, y] = (255, 255, 255, min(a, ink))
                    im.save(out)
    except Exception:  # noqa: BLE001 - a logo problem must never break the PDF
        out = None
    _LOGO_CACHE[key] = out
    return out


def _draw_logo(canvas, x, y, width, white=False):
    path = _logo(white)
    if path:
        canvas.drawImage(path, x, y, width=width, height=width / 5, mask='auto')  # the asset is 5:1

GLOSSARY = [
    ('AI visibility', 'How often a brand appears in the answers AI engines (ChatGPT, Gemini, Claude, Perplexity, ...) give to buyer questions. Measured as mention rate and share of voice over a set of prompts.'),
    ('GEO score', 'A 0-100 score built from placement (35%), frequency (25%), sourcing (25%) and framing (15%) across every answer read. Bands: Absent 0-25, Present 26-50, Preferred 51-75, Default 76-100.'),
    ('Mention rate', 'Share of answers in which the brand is named at all.'),
    ('Citation', "An answer that links to (or names a URL on) the brand's own site. Being cited is stronger than being mentioned: the engine is using you as its source."),
    ('Share of voice', "The brand's mentions as a share of all brand mentions across the answers - you versus every rival the engines named."),
    ('Funnel stage', 'Where a prompt sits in the buyer journey: TOFU (awareness), MOFU (evaluation and comparison), BOFU (decision).'),
    ('Gap type', 'Why a prompt is lost. Visibility gap: never named while rivals are. Position gap: named, but never in the top three. Educational: nobody is named, so it is not a real gap.'),
    ('Findable / Cited / Chosen', 'The three questions behind the measures: can the engines reach and read you; are you the source they use; are you the answer they give.'),
    ('Schema (JSON-LD)', 'Structured data on a page that tells engines what each block is (an FAQ, a product, an author). Engines extract and cite structured answers more readily.'),
    ('llms.txt', 'An optional plain-text file at the site root that tells AI crawlers what the site is about and where the important pages are.'),
    ('Owned citation share', "Of every URL the engines cited on your prompts, the share that points at your own site rather than a rival's or a third party's."),
    ('Website health score', 'A 0-100 site score from eight weighted categories: AI crawlability, structured data, content depth, E-E-A-T signals, internal linking, on-page & technical SEO, content freshness and Core Web Vitals. Unmeasured categories drop out of the weighting.'),
    ('E-E-A-T', 'Experience, Expertise, Authoritativeness, Trust - the signals engines use to decide whether a page is worth citing: author bylines, cited sources, Person schema and credential claims.'),
    ('Authority score', "A 0-100 estimate of how trusted a site is across the web, from the number and quality of sites linking to it (a third-party link index; scale comparable to Ahrefs DR / Moz DA)."),
    ('Core Web Vitals', "Google's real-user speed metrics: LCP (how fast the main content shows), CLS (how much the layout jumps), INP (how fast the page reacts to a tap). Measured for the homepage on mobile."),
    ('Canonical tag', "A page's declaration of its master URL, so tracking parameters and duplicates do not split its authority."),
    ('Orphan page', 'A page no other sampled page links to; crawlers reach it only from the sitemap and it gets no internal authority.'),
]


# =====================================================================================
# styles & small helpers
# =====================================================================================

def _styles():
    ss = getSampleStyleSheet()
    return {
        'eyebrow': ParagraphStyle('eyebrow', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=MUTED, leading=10),
        'eyebrow_light': ParagraphStyle('eyebrow_light', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#ddd6fe'), leading=10),
        'cover_title': ParagraphStyle('cover_title', parent=ss['Title'], fontName='Helvetica-Bold', fontSize=34, leading=38, textColor=WHITE, alignment=TA_LEFT, spaceAfter=6),
        'cover_sub': ParagraphStyle('cover_sub', parent=ss['Normal'], fontSize=10.5, leading=14, textColor=colors.HexColor('#ede9fe')),
        'h1': ParagraphStyle('h1', parent=ss['Heading1'], fontName='Helvetica-Bold', fontSize=22, leading=26, textColor=INK, spaceAfter=4),
        'part_num': ParagraphStyle('part_num', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.HexColor('#ddd6fe')),
        'part_title': ParagraphStyle('part_title', parent=ss['Heading1'], fontName='Helvetica-Bold', fontSize=24, leading=28, textColor=WHITE, spaceAfter=2),
        'part_blurb': ParagraphStyle('part_blurb', parent=ss['Normal'], fontSize=9.2, leading=13, textColor=colors.HexColor('#ede9fe')),
        'part_number': ParagraphStyle('part_number', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=30, leading=34, textColor=PRIMARY_DARK, alignment=TA_CENTER),
        'card_head': ParagraphStyle('card_head', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=10.5, leading=13, textColor=WHITE),
        'card_pct': ParagraphStyle('card_pct', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=18, textColor=WHITE, alignment=TA_CENTER),
        'h2': ParagraphStyle('h2', parent=ss['Heading2'], fontName='Helvetica-Bold', fontSize=15, leading=18, textColor=INK, spaceBefore=6, spaceAfter=2),
        'h3': ParagraphStyle('h3', parent=ss['Heading3'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=INK, spaceBefore=6, spaceAfter=2, keepWithNext=1),
        'sub': ParagraphStyle('sub', parent=ss['Normal'], fontSize=9, leading=12.5, textColor=MUTED, spaceAfter=8),
        'body': ParagraphStyle('body', parent=ss['Normal'], fontSize=10, leading=14.5, textColor=INK),
        'small': ParagraphStyle('small', parent=ss['Normal'], fontSize=8, leading=10.5, textColor=INK),
        'smallmuted': ParagraphStyle('smallmuted', parent=ss['Normal'], fontSize=8, leading=10.5, textColor=MUTED),
        'howto': ParagraphStyle('howto', parent=ss['Normal'], fontSize=8.5, leading=11.5, textColor=MUTED, leftIndent=8, spaceAfter=6),
        'takeaway_label': ParagraphStyle('takeaway_label', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=PRIMARY),
        'takeaway': ParagraphStyle('takeaway', parent=ss['Normal'], fontSize=9.5, leading=13.5, textColor=INK),
        'tile_label': ParagraphStyle('tile_label', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=6.5, textColor=MUTED, leading=8),
        'tile_value': ParagraphStyle('tile_value', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=15, textColor=INK, leading=18),
        'tile_label_light': ParagraphStyle('tile_label_light', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=6.5, textColor=colors.HexColor('#c4b5fd'), leading=8),
        'tile_value_light': ParagraphStyle('tile_value_light', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=13, textColor=WHITE, leading=16),
        'callout': ParagraphStyle('callout', parent=ss['Normal'], fontSize=9.2, leading=12.8, textColor=INK),
        'toc1': ParagraphStyle('toc1', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=20, textColor=INK),
        'toc2': ParagraphStyle('toc2', parent=ss['Normal'], fontSize=9, leading=15, textColor=MUTED, leftIndent=18),
        'center_muted': ParagraphStyle('center_muted', parent=ss['Normal'], fontSize=8, textColor=MUTED, alignment=TA_CENTER),
        'chip': ParagraphStyle('chip', parent=ss['Normal'], fontName='Helvetica-Bold', fontSize=6.8, leading=9, alignment=TA_CENTER),
    }


_GLYPHS = {'\u2010': '-', '\u2011': '-', '\u2012': '-', '\u2013': '-', '\u2014': ' - ', '\u2015': '-', '\u00a0': ' ', '\u202f': ' ',
           '\u2009': ' ', '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u2192': '>', '\u2022': '-',
           '\u2713': 'yes', '\u2717': 'no', '\u2705': '', '\u274c': '', '\u00d7': 'x'}


_KEY_ASIDE = re.compile(r'\s*\(([^()]*\b[a-z]+_[a-z_.]+\b[^()]*)\)')


def _prose(text):
    """LLM prose for print: drop asides that quote digest field names ("(mention_rate_pct: 8)")."""
    return _KEY_ASIDE.sub('', str(text or '')).strip()


def _esc(v):
    s = str(v) if v is not None else ''
    for bad, good in _GLYPHS.items():
        if bad in s:
            s = s.replace(bad, good)
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _p(text, style):
    return Paragraph(_esc(text), style)


def _fmt_date(value):
    if not value:
        return ''
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).strftime('%d %b %Y')
    except ValueError:
        return str(value)[:10]


def _pct(v, digits=0):
    if v is None or v == '':
        return '—'
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"{f:.{digits}f}%"


def _grid(data, col_widths, header=True, zebra=True, extra=None, font_size=8, header_bg=SOFT):
    if header and data:
        # header strings become paragraphs so long labels wrap inside narrow columns instead of overflowing
        th = ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=font_size, leading=font_size + 2, textColor=MUTED)
        data = [[Paragraph(_esc(c), th) if isinstance(c, str) else c for c in data[0]]] + list(data[1:])
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'), ('FONTSIZE', (0, 0), (-1, -1), font_size),
        ('TEXTCOLOR', (0, 0), (-1, -1), INK), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, LINE),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    if header:
        style += [('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('TEXTCOLOR', (0, 0), (-1, 0), MUTED),
                  ('BACKGROUND', (0, 0), (-1, 0), header_bg), ('LINEBELOW', (0, 0), (-1, 0), 0.8, LINE)]
    if zebra:
        for i in range(2 if header else 1, len(data), 2):
            style.append(('BACKGROUND', (0, i), (-1, i), SOFT))
    if extra:
        style += extra
    t.setStyle(TableStyle(style))
    return t


def _box(flowables, width, bg=WHITE, border=LINE, pad=8, left_bar=None):
    """A bordered card with optional coloured left bar."""
    inner = Table([[flowables]], colWidths=[width])
    style = [('BOX', (0, 0), (-1, -1), 0.6, border), ('BACKGROUND', (0, 0), (-1, -1), bg),
             ('LEFTPADDING', (0, 0), (-1, -1), pad), ('RIGHTPADDING', (0, 0), (-1, -1), pad),
             ('TOPPADDING', (0, 0), (-1, -1), pad), ('BOTTOMPADDING', (0, 0), (-1, -1), pad), ('VALIGN', (0, 0), (-1, -1), 'TOP')]
    if left_bar is not None:
        style.append(('LINEBEFORE', (0, 0), (0, -1), 3, left_bar))
    inner.setStyle(TableStyle(style))
    return inner


def _tile(label, value, sub, st, width, dark=False):
    ls, vs = ('tile_label_light', 'tile_value_light') if dark else ('tile_label', 'tile_value')
    if len(str(value)) > 11:  # long values (funnel split, "67% positive") drop to one line
        vs = ParagraphStyle('tv_small', parent=st[vs], fontSize=10, leading=13)
    else:
        vs = st[vs]
    sub_style = ParagraphStyle('ts', parent=st['smallmuted'], textColor=(colors.HexColor('#ddd6fe') if dark else MUTED), fontSize=7, leading=9)
    rows = [[_p(label, st[ls])], [_p(value, vs)], [_p(sub, sub_style)]]
    inner = Table(rows, colWidths=[width - 12])
    inner.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                               ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))
    return _box([inner], width, bg=(PRIMARY_DARK if dark else WHITE), border=(colors.HexColor('#6d28d9') if dark else LINE), pad=6)


def _chip(text, colour, bg, st):
    t = Table([[Paragraph(f"<font color='{colour.hexval()}'>{_esc(text)}</font>", st['chip'])]], colWidths=[26 * mm])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), bg), ('BOX', (0, 0), (-1, -1), 0.4, colour),
                           ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                           ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3)]))
    return t


PRIORITY_CHIP = {'on_track': ('On track', GREEN, GREEN_BG), 'important': ('Important', AMBER, AMBER_BG),
                 'critical': ('Critical', RED, RED_BG), 'not_measured': ('Not measured', MUTED, MUTED_BG)}
SEVERITY_COLOUR = {'critical': RED, 'warning': AMBER, 'info': MUTED}
CWV_RATING = {'good': ('Good', GREEN), 'needs_improvement': ('Needs improvement', AMBER), 'poor': ('Poor', RED)}


def _priority_chip(priority, st):
    label, colour, bg = PRIORITY_CHIP.get(priority or 'not_measured', PRIORITY_CHIP['not_measured'])
    return _chip(label, colour, bg, st)


def _status_chip(score, target, st):
    if score is None:
        return _chip('Not measured', MUTED, MUTED_BG, st)
    if score >= target:
        return _chip('On track', GREEN, GREEN_BG, st)
    if score >= target * 0.6:
        return _chip('Important', AMBER, AMBER_BG, st)
    return _chip('Critical', RED, RED_BG, st)


# =====================================================================================
# drawings
# =====================================================================================

def _score_ring(score, band_key, size=120, light=False):
    d = Drawing(size, size)
    cx = cy = size / 2
    r = size / 2 - 8
    d.add(Circle(cx, cy, r, strokeColor=(colors.HexColor('#5b21b6') if light else MUTED_BG), strokeWidth=9, fillColor=None))
    colour = BAND.get(band_key, (None, None, 0, 0, MUTED, ''))[4]
    if light and band_key == 'preferred':
        colour = SECONDARY
    if score:
        ang = 360 * min(100, max(0, score)) / 100
        d.add(Wedge(cx, cy, r + 4.5, 90 - ang, 90, radius1=r - 4.5, fillColor=colour, strokeColor=None))
    d.add(String(cx, cy - 8, str(score if score is not None else '—'), fontName='Helvetica-Bold', fontSize=size * 0.28,
                 textAnchor='middle', fillColor=(WHITE if light else INK)))
    d.add(String(cx, cy - 22, BAND.get(band_key, (None, 'Not scored'))[1].upper(), fontName='Helvetica-Bold', fontSize=7.5,
                 textAnchor='middle', fillColor=(WHITE if light else colour)))
    return d


def _maturity_ladder(score, band_key, width):
    """Four bands as a ladder with a "you are here" marker."""
    h = 48
    d = Drawing(width, h)
    seg = width / 4
    for i, (key, label, lo, hi, colour, meaning) in enumerate(GEO_BANDS):
        x = i * seg
        active = key == band_key
        d.add(Rect(x + 1, 14, seg - 2, 14, fillColor=(colour if active else colors.HexColor('#e5e7eb')), strokeColor=None, rx=3, ry=3))
        d.add(String(x + seg / 2, 33, f"{label}  ·  {lo}-{hi}", fontName='Helvetica-Bold' if active else 'Helvetica', fontSize=7.5,
                     textAnchor='middle', fillColor=(colour if active else MUTED)))
        d.add(String(x + seg / 2, 3, meaning, fontName='Helvetica', fontSize=6.3, textAnchor='middle', fillColor=MUTED))
    if score is not None:
        x = width * min(100, max(0, score)) / 100
        d.add(Rect(x - 1, 12, 2, 18, fillColor=INK, strokeColor=None))
        d.add(String(min(width - 14, max(14, x)), 42, f"you · {score}", fontName='Helvetica-Bold', fontSize=7, textAnchor='middle', fillColor=INK))
    return d


def _hbar(labels, values, width, colour=PRIMARY, height=None, suffix='%', vmax=100, highlight=None):
    """`highlight`: index of the bar drawn in the brand colour while the others go muted (share-of-voice "you")."""
    n = max(1, len(labels))
    height = height or (18 * n + 22)
    height += 12
    d = Drawing(width, height)
    bc = HorizontalBarChart()
    bc.x, bc.y, bc.width, bc.height = 78, 18, width - 110, height - 26
    # the chart draws its first category at the bottom; reverse so the list reads top-down
    bc.data = [list(reversed(list(values))) or [0]]
    bc.categoryAxis.categoryNames = list(reversed(list(labels))) or ['']
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.categoryAxis.labels.fontSize = 7.5
    bc.categoryAxis.labels.dx = -4
    bc.categoryAxis.strokeColor = LINE
    bc.valueAxis.valueMin, bc.valueAxis.valueMax = 0, vmax
    bc.valueAxis.valueStep = vmax / 4
    bc.valueAxis.labels.fontSize = 6.5
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.labels.fillColor = MUTED
    bc.valueAxis.strokeColor = LINE
    bc.valueAxis.labelTextFormat = (lambda v: f"{int(v)}{suffix}")
    bc.bars[0].fillColor = colour
    bc.bars[0].strokeColor = None
    if highlight is not None and 0 <= highlight < n:
        # bars are reversed for top-down reading, so the index is mirrored
        for i in range(n):
            bc.bars[(0, i)].fillColor = PRIMARY if (n - 1 - i) == highlight else colors.HexColor('#c4b5fd')
    bc.barWidth = 9
    bc.groupSpacing = 6
    bc.barLabels.fontName = 'Helvetica-Bold'
    bc.barLabels.fontSize = 7
    bc.barLabels.fillColor = INK
    bc.barLabelFormat = (lambda v: f"{int(round(v))}{suffix}")
    bc.barLabels.dx = 12
    d.add(bc)
    return d


def _donut(parts, width, height=92):
    """parts: [(label, value, colour)]"""
    d = Drawing(width, height)
    pie = Pie()
    pie.x, pie.y = 6, 8
    pie.width = pie.height = height - 16
    pie.data = [max(0.0001, float(v or 0)) for _, v, _ in parts]
    pie.labels = None
    pie.slices.strokeColor = WHITE
    pie.slices.strokeWidth = 1
    for i, (_, _, c) in enumerate(parts):
        pie.slices[i].fillColor = c
    d.add(pie)
    d.add(Circle(pie.x + pie.width / 2, pie.y + pie.height / 2, pie.width * 0.28, fillColor=WHITE, strokeColor=None))
    y = height - 18
    for label, v, c in parts:
        d.add(Rect(height + 2, y, 8, 8, fillColor=c, strokeColor=None))
        d.add(String(height + 14, y + 1, f"{label}  {_pct(v)}", fontName='Helvetica', fontSize=7.5, fillColor=INK))
        y -= 14
    return d


# =====================================================================================
# document template with running header/footer + TOC
# =====================================================================================

class _TocMark(Flowable):
    """Zero-height marker that puts one heading into the contents.

    `afterFlowable` only sees flowables added straight to the story, and both
    headings are drawn inside tables now (the purple part band and the accent
    bar beside a section title). Without this marker the contents page would
    have nothing to list, and the running header would lose the part name.
    """

    def __init__(self, level, text):
        super().__init__()
        self.level = level
        self.text = text
        self.width = 0
        self.height = 0

    def wrap(self, *_args):
        return 0, 0

    def draw(self):
        return


class _Doc(BaseDocTemplate):
    def __init__(self, buf, audit, brand_label, **kw):
        super().__init__(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=20 * mm, bottomMargin=18 * mm, **kw)
        self.audit = audit
        self.brand_label = brand_label
        self.part_title = ''
        body = Frame(MARGIN, 18 * mm, W, PAGE_H - 38 * mm, id='body', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        cover = Frame(0, 0, PAGE_W, PAGE_H, id='cover', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([
            PageTemplate(id='cover', frames=[cover], onPage=self._cover_page),
            PageTemplate(id='body', frames=[body], onPageEnd=self._body_page),
        ])

    def _cover_page(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(PRIMARY_DARK)
        canvas.rect(0, PAGE_H - 120 * mm, PAGE_W, 120 * mm, stroke=0, fill=1)
        # soft concentric circles, top-right, for depth
        canvas.setFillColor(WHITE)
        for r, alpha in ((95 * mm, 0.04), (70 * mm, 0.05), (45 * mm, 0.06)):
            canvas.setFillAlpha(alpha)
            canvas.circle(PAGE_W - 30 * mm, PAGE_H - 25 * mm, r, stroke=0, fill=1)
        canvas.setFillAlpha(1)
        # brand accent: primary bar with a magenta cap
        canvas.setFillColor(PRIMARY)
        canvas.rect(0, PAGE_H - 123 * mm, PAGE_W, 3 * mm, stroke=0, fill=1)
        canvas.setFillColor(SECONDARY)
        canvas.rect(0, PAGE_H - 123 * mm, 60 * mm, 3 * mm, stroke=0, fill=1)
        _draw_logo(canvas, MARGIN, PAGE_H - 22 * mm, 42 * mm, white=True)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 10 * mm, f"{self.brand_label} · AI visibility audit · {self.audit.host}")
        canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, 'Confidential')
        canvas.restoreState()

    def beforeDocument(self):
        self.part_title = ''

    def _body_page(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, PAGE_H - 14 * mm, PAGE_W - MARGIN, PAGE_H - 14 * mm)
        canvas.setFont('Helvetica-Bold', 7)
        canvas.setFillColor(INK)
        canvas.drawString(MARGIN, PAGE_H - 11.5 * mm, f"{self.audit.brand_name or self.audit.host}")
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN + canvas.stringWidth(f"{self.audit.brand_name or self.audit.host}", 'Helvetica-Bold', 7) + 4, PAGE_H - 11.5 * mm, '· AI visibility audit')
        canvas.drawCentredString(PAGE_W / 2, PAGE_H - 11.5 * mm, self.part_title)
        if _logo():
            _draw_logo(canvas, PAGE_W - MARGIN - 26 * mm, PAGE_H - 13.4 * mm, 26 * mm)
        else:
            canvas.setFont('Helvetica-Bold', 7)
            canvas.setFillColor(PRIMARY)
            canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 11.5 * mm, self.brand_label.upper())
        canvas.line(MARGIN, 14 * mm, PAGE_W - MARGIN, 14 * mm)
        canvas.drawString(MARGIN, 9.5 * mm, f"{self.brand_label} · {self.audit.host} · {_fmt_date(self.audit.completed_at)}")
        canvas.drawRightString(PAGE_W - MARGIN, 9.5 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        # Contents entries: part titles (level 0) and section headings (level 1).
        # Both arrive as markers because the headings themselves are drawn
        # inside tables, which afterFlowable never sees.
        if isinstance(flowable, _TocMark):
            if flowable.level == 0:
                self.part_title = flowable.text
            self.notify('TOCEntry', (flowable.level, flowable.text, self.page))
        elif isinstance(flowable, Paragraph):
            name = flowable.style.name
            if name == 'part_title':
                self.part_title = flowable.getPlainText()
                self.notify('TOCEntry', (0, flowable.getPlainText(), self.page))
            elif name == 'h2':
                self.notify('TOCEntry', (1, flowable.getPlainText(), self.page))


# =====================================================================================
# data helpers (defensive over report JSON + evidence rows)
# =====================================================================================

def _depth(audit, report):
    """Visibility depth: engine reach, avg position, top-3 rate, #1 rate, sentiment split — from evidence rows when present."""
    rows = []
    try:
        rows = list(audit.prompt_results.filter(status='ok').values('is_mention', 'position', 'sentiment', 'platform'))
    except Exception:  # noqa: BLE001 - trimmed audits or stand-ins without rows
        rows = []
    mentioned = [r for r in rows if r.get('is_mention')]
    positions = [float(r['position']) for r in mentioned if r.get('position') is not None]
    sent = {'positive': 0, 'neutral': 0, 'negative': 0}
    for r in mentioned:
        sent[r.get('sentiment') if r.get('sentiment') in sent else 'neutral'] += 1
    n = len(mentioned) or 1
    engines = (report.get('geo') or {}).get('engines') or []
    reach = [e.get('platform') for e in engines if e.get('mentioned')]
    return {
        'reach': len(reach), 'engines_total': len(engines), 'reach_names': reach,
        'avg_position': round(sum(positions) / len(positions), 1) if positions else None,
        'top3_rate': round(100 * sum(1 for p in positions if p <= 3) / len(positions)) if positions else None,
        'first_rate': round(100 * sum(1 for p in positions if p <= 1) / len(positions)) if positions else None,
        'sentiment': {k: round(100 * v / n) for k, v in sent.items()} if mentioned else None,
    }


def _engine_notes(e, brand):
    """Strengths / gaps for one engine, from its numbers."""
    strengths, gaps = [], []
    rate = round(100 * e.get('mention_rate', 0))
    if e.get('answered'):
        (strengths if rate >= 50 else gaps).append(f"Names {brand} on {rate}% of prompts" if rate >= 50 else f"Names {brand} on only {rate}% of prompts")
        if e.get('cited'):
            strengths.append(f"Cites your site on {e['cited']} answer{'s' if e['cited'] != 1 else ''}")
        else:
            gaps.append('Never cites your site')
        if e.get('avg_position') is not None:
            (strengths if e['avg_position'] <= 2 else gaps).append(f"{'Named early' if e['avg_position'] <= 2 else 'Named late'} - average position {e['avg_position']}")
        if e.get('top_rival') and e.get('top_rival_mentions'):
            gaps.append(f"{e['top_rival']} named {e['top_rival_mentions']}x")
    else:
        gaps.append('No answers returned')
    if not strengths:
        strengths.append('No strengths on this engine yet')
    return strengths[:3], gaps[:3]


def _engine_recommendation(e, brand):
    rate = round(100 * e.get('mention_rate', 0))
    if not e.get('answered'):
        return 'Re-run once the engine is reachable.'
    if rate < 34:
        return f"Publish answer pages for the prompts {e.get('platform')} loses to {e.get('top_rival') or 'rivals'}; this engine barely knows {brand}."
    if not e.get('cited'):
        return 'Add citable pages (comparison tables, pricing, FAQ with schema) so the engine can link to you rather than describe you.'
    return 'Defend: keep cited pages fresh and expand into the funnel stages where you are not yet named.'


def _page_readiness(p):
    if not p.get('fetched', True):
        return None
    links = p.get('external_links') or 0
    return (25 if p.get('schema_types') else 0) + (25 if p.get('author') else 0) + (25 if links >= 3 else 10 if links else 0) + (25 if p.get('last_modified') else 0)


def _page_flags(d):
    """[(label, is_bad)] on-page flags for one page's technical details."""
    flags = []
    if d.get('noindex'):
        flags.append(('noindex', True))
    if (d.get('status_code') or 0) >= 400:
        flags.append((f"HTTP {d['status_code']}", True))
    if d.get('title_length') == 0:
        flags.append(('no title', True))
    if d.get('description_length') == 0:
        flags.append(('no description', False))
    if d.get('h1_count') == 0:
        flags.append(('no H1', False))
    if (d.get('h1_count') or 0) > 1:
        flags.append((f"{d['h1_count']} H1s", False))
    if d.get('canonical_status') == 'missing':
        flags.append(('no canonical', False))
    if d.get('canonical_status') == 'mismatch':
        flags.append(('canonical elsewhere', False))
    if d.get('mixed_content'):
        flags.append(('mixed content', True))
    if d.get('viewport') is False:
        flags.append(('no viewport', False))
    if d.get('redirects'):
        flags.append((f"{d['redirects']} redirect{'s' if d['redirects'] > 1 else ''}", False))
    return flags


def _path_of(url):
    try:
        from urllib.parse import urlparse
        return urlparse(url).path or '/'
    except Exception:  # noqa: BLE001
        return url


# =====================================================================================
# builder
# =====================================================================================

def build_audit_pdf(audit) -> bytes:
    """Render a DONE audit's report to PDF bytes."""
    r = audit.report or {}
    geo = r.get('geo') or {}
    st = _styles()
    brand_label = getattr(settings, 'AUDIT_REPORT_BRAND_NAME', 'PromptMaxx') or 'PromptMaxx'
    brand = audit.brand_name or audit.host
    band_key = audit.geo_stage or ''
    band = BAND.get(band_key, ('', 'Not scored', 0, 0, MUTED, ''))
    country = COUNTRY_NAMES.get(audit.country, (audit.country or '').upper())
    engines = geo.get('engines') or []
    runs = geo.get('runs_per_prompt') or 1
    evidence = geo.get('evidence') or []
    summary = r.get('summary') or {}
    intros = summary.get('sections') or {}
    seo = r.get('seo')
    crawl = r.get('crawl')
    plan = r.get('plan') or {}
    nar = r.get('narrative') or {}
    ctrl = geo.get('citation_control') or {}
    depth = _depth(audit, r)
    prompt_count = (r.get('config') or {}).get('prompt_count') or len(evidence)
    platforms = [e.get('platform') for e in engines]
    mention_rate = round(100 * audit.appearances / audit.total_runs) if audit.total_runs else 0
    sent = depth.get('sentiment') or {}

    buf = io.BytesIO()
    doc = _Doc(buf, audit, brand_label, title=f"{brand} - AI visibility audit", author=brand_label)
    story = []

    def part(num, title, blurb):
        disc = Table([[_p(num, st['part_number'])]], colWidths=[18 * mm], rowHeights=[18 * mm])
        disc.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), WHITE), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                  ('ROUNDEDCORNERS', [9 * mm] * 4), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
        text = [_p(f"PART {num}", st['part_num']), _p(title, st['part_title'])]
        if blurb:
            text.append(_p(blurb, st['part_blurb']))
        band = Table([[disc, text]], colWidths=[26 * mm, W - 26 * mm])
        band.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), PRIMARY_DARK), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                  ('ROUNDEDCORNERS', [8] * 4), ('LINEBELOW', (0, 0), (-1, -1), 3, SECONDARY),
                                  ('LEFTPADDING', (0, 0), (0, 0), 6 * mm), ('RIGHTPADDING', (0, 0), (-1, -1), 6 * mm),
                                  ('TOPPADDING', (0, 0), (-1, -1), 8 * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 8 * mm)]))
        story.append(_TocMark(0, title))
        story.append(band)
        story.append(Spacer(1, 10))

    def sentence(text):
        text = _prose(text)
        if text and text[-1] not in '.!?' and '. ' in text:
            text = text[:text.rfind('. ') + 1]
        return text

    def takeaway(text):
        """'What this means' box - one plain-language sentence written from the numbers, under every major section."""
        text = _prose(text)
        if not text:
            return
        box = Table([[[_p('WHAT THIS MEANS', st['takeaway_label']), _p(text, st['takeaway'])]]], colWidths=[W])
        box.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), PRIMARY_TINT), ('LINEBEFORE', (0, 0), (0, -1), 3, PRIMARY),
                                 ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                                 ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
        story.extend([Spacer(1, 4), box, Spacer(1, 10)])

    def howto(text):
        """'How to read this' note for dense tables."""
        story.append(Paragraph(f"<b>How to read this:</b> {_esc(text)}", st['howto']))

    def gap(h=10):
        story.append(Spacer(1, h))

    def h2(title):
        # a heading needs room for at least a few rows under it; tables then split freely
        story.append(Spacer(1, 8))
        story.append(CondPageBreak(50 * mm))
        story.append(_TocMark(1, title))
        head = Table([[_p(title, st['h2'])]], colWidths=[W])
        head.setStyle(TableStyle([('LINEBEFORE', (0, 0), (0, -1), 2.5, PRIMARY), ('LEFTPADDING', (0, 0), (-1, -1), 8),
                                  ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
        story.append(head)

    def intro(key):
        text = sentence(intros.get(key))
        if text:
            story.append(_box([_p(text, st['callout'])], W, bg=PRIMARY_TINT, border=PRIMARY_TINT, left_bar=PRIMARY))
            story.append(Spacer(1, 4))

    def callout(title, text, tone='info'):
        bg, bar = {'info': (PRIMARY_TINT, PRIMARY), 'warn': (AMBER_BG, AMBER), 'bad': (RED_BG, RED), 'soft': (SOFT, PRIMARY)}[tone]
        story.append(_box([Paragraph(f"<b>{_esc(title)}</b> — {_esc(text)}", st['callout'])], W, bg=bg, border=bg, left_bar=bar))
        story.append(Spacer(1, 4))

    # ---------------------------------------------------------------- cover
    cover_text = [
        Spacer(1, 26 * mm),
        _p("AI VISIBILITY AUDIT · CONFIDENTIAL", st['eyebrow_light']),
        Spacer(1, 4),
        _p('AI Visibility Report', st['cover_title']),
        _p(f"{brand}'s AI search visibility measured across {prompt_count} prompts · {geo.get('runs_total', 0)} AI answers on "
           f"{', '.join(platforms) or 'the configured engines'} - with competitive benchmarking, brand narrative and a 90-day plan.", st['cover_sub']),
        Spacer(1, 12),
    ]
    meta = Table([[
        [_p('CLIENT', st['tile_label_light']), _p(brand, st['tile_value_light'])],
        [_p('DOMAIN', st['tile_label_light']), _p(audit.host, st['tile_value_light'] if len(audit.host) <= 14 else ParagraphStyle('tv_host', parent=st['tile_value_light'], fontSize=10, leading=13))],
        [_p('VERTICAL', st['tile_label_light']), _p(audit.industry or '—', st['tile_value_light'])],
        [_p('DATE', st['tile_label_light']), _p(_fmt_date(audit.completed_at) or '—', st['tile_value_light'])],
    ]], colWidths=[(W - 45 * mm) * f for f in (0.27, 0.27, 0.28, 0.18)])
    meta.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    cover_text.append(meta)
    head = Table([[cover_text, _score_ring(audit.geo_score, band_key, size=110, light=True)]], colWidths=[W - 45 * mm, 45 * mm])
    head.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                              ('TOPPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (1, 0), (1, 0), 26 * mm)]))
    wrap = Table([[head]], colWidths=[PAGE_W], rowHeights=[108 * mm])
    wrap.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), MARGIN), ('RIGHTPADDING', (0, 0), (-1, -1), MARGIN), ('TOPPADDING', (0, 0), (-1, -1), 0),
                              ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story += [wrap, Spacer(1, 22 * mm)]

    default_finding = (f"{brand} is {band[1]} with a GEO score of {audit.geo_score}: named in {audit.appearances} of {audit.total_runs} "
                       f"answers and cited in {audit.cited_runs}.")
    funnel_all = (geo.get('funnel') or {}).get('by_stage') or {}
    funnel = {k: funnel_all[k] for k in ('top', 'middle', 'bottom') if k in funnel_all} or funnel_all
    tiles = [
        ('GEO SCORE', str(audit.geo_score if audit.geo_score is not None else '—'), f"{band[1]} · {band[2]}-{band[3]}" if band[0] else 'not scored'),
        ('AI APPEARANCES', f"{audit.appearances} / {audit.total_runs}", 'answers naming you'),
        ('CITED', f"{audit.cited_runs} / {audit.total_runs}", 'answers linking your site'),
        ('SHARE OF VOICE', _pct(audit.share_of_voice), 'of all brand mentions'),
        ('#1 POSITION RATE', _pct(depth['first_rate']) if depth['first_rate'] is not None else '—', 'of mentions named first'),
        ('ENGINE COVERAGE', f"{depth['reach']} / {depth['engines_total']}", 'engines naming you'),
        ('FUNNEL VISIBILITY', ' · '.join(f"{v.get('label', k)[:4]} {_pct(v.get('rate'))}" for k, v in funnel.items()) or '—', 'mention rate by stage'),
        ('SENTIMENT', f"{_pct(sent.get('positive'))} positive" if sent else '—', f"{_pct(sent.get('neutral'))} neutral · {_pct(sent.get('negative'))} negative" if sent else 'no mentions yet'),
    ]
    tw = W / 4
    tt = Table([[_tile(a, b, c, st, tw - 4) for a, b, c in tiles[:4]], [_tile(a, b, c, st, tw - 4) for a, b, c in tiles[4:]]], colWidths=[tw] * 4)
    tt.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4), ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]))
    tw_wrap = Table([[tt]], colWidths=[PAGE_W])
    tw_wrap.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), MARGIN), ('RIGHTPADDING', (0, 0), (-1, -1), MARGIN)]))
    story += [tw_wrap, Spacer(1, 10 * mm)]
    prep = Table([[[_p(f"PREPARED FOR {brand.upper()} · {country.upper()}", st['eyebrow']), Spacer(1, 3), _p(_prose(summary.get('headline')) or default_finding, st['body'])]]], colWidths=[W])
    prep.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), MARGIN), ('RIGHTPADDING', (0, 0), (-1, -1), MARGIN)]))
    story += [prep, Spacer(1, 8 * mm)]
    inside = [
        ('01', 'Executive summary', 'Key findings, the three moves to make first, where you stand on the maturity ladder.'),
        ('02', 'AI search visibility', 'Engine-by-engine results, the buyer-funnel heatmap, prompts won and lost, rivals, citations, brand narrative.'),
        ('03', 'Website health', 'Can the engines read and trust the site: crawlability, schema, E-E-A-T, technical SEO, page-level scores.'),
        ('04', '90-day plan', 'Every action sequenced Now / Next / Later with the score projected at each step and KPI targets.'),
        ('05', 'Appendices', 'Methodology, scoring model, limitations and glossary.'),
    ]
    rows = []
    for num, title, blurb in inside:
        disc = Table([[Paragraph(f"<font color='{WHITE.hexval()}'><b>{num}</b></font>", ParagraphStyle('d', parent=st['small'], alignment=TA_CENTER, fontSize=8))]], colWidths=[8 * mm], rowHeights=[8 * mm])
        disc.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), PRIMARY), ('ROUNDEDCORNERS', [4 * mm] * 4), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                  ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
        rows.append([disc, [_p(title, st['h3']), _p(blurb, st['smallmuted'])]])
    idx_t = Table(rows, colWidths=[12 * mm, W - 12 * mm])
    idx_t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                               ('TOPPADDING', (0, 0), (-1, -1), 0)]))
    inside_wrap = Table([[[_p('INSIDE THIS REPORT', st['eyebrow']), Spacer(1, 4), idx_t]]], colWidths=[W])
    inside_wrap.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), MARGIN), ('RIGHTPADDING', (0, 0), (-1, -1), MARGIN)]))
    story += [inside_wrap, NextPageTemplate('body'), PageBreak()]

    # ---------------------------------------------------------------- contents
    story.append(_p('Contents', st['h1']))
    toc = TableOfContents()
    toc.levelStyles = [st['toc1'], st['toc2']]
    story += [toc, PageBreak()]

    # ---------------------------------------------------------------- 01 executive summary
    part('01', 'Executive summary',
         f"Scan scope: {prompt_count} prompts asked {'once' if runs == 1 else str(runs) + ' times'} each on {', '.join(platforms) or 'the configured engines'} "
         f"({geo.get('runs_total', 0)} answers). {brand} appeared in {audit.appearances} of those answers and was cited in {audit.cited_runs}.")
    h2('Key findings')
    findings = [_prose(f) for f in (summary.get('key_findings') or []) if _prose(f)] or [default_finding]
    rows = [[Paragraph(f"<font color='{PRIMARY.hexval()}'><b>{i}</b></font>", st['body']), _p(f, st['body'])] for i, f in enumerate(findings, 1)]
    story.extend([_grid(rows, [8 * mm, W - 8 * mm], header=False, zebra=False, extra=[('BOX', (0, 0), (-1, -1), 0.6, LINE), ('BACKGROUND', (0, 0), (-1, -1), SOFT)]), Spacer(1, 6)])

    now_items = next((b.get('items') or [] for b in (plan.get('buckets') or []) if b.get('key') == 'now'), None) or (r.get('quick_wins') or [])
    if now_items:
        h2('Top 3 immediate actions')
        rows = [['Action', 'Business impact', 'Effort']]
        for it in now_items[:3]:
            rows.append([_p(it.get('title', ''), st['small']), _p(it.get('why', ''), st['smallmuted']),
                         _p(f"~{it.get('effort_hours', 0)}h · +{it.get('projected_geo_lift', 0)} pts", st['small'])])
        story.extend([_grid(rows, [W * 0.36, W * 0.46, W * 0.18]), Spacer(1, 6)])

    h2('How to read the GEO score')
    story.append(_p("The GEO score (0-100) measures how strongly AI engines recommend a brand when buyers ask about its category. "
                    "It combines four things: placement 35% (how early you are named among the brands in an answer), frequency 25% "
                    "(how many answers name you), sourcing 25% (how many link to your own site) and framing 15% (how positively you are described). "
                    "Scores fall into four bands: Absent 0-25 (rarely named), Present 26-50 (named but not first), Preferred 51-75 (a recommended option), "
                    "Default 76-100 (the answer the engines give).", st['body']))
    gap(6)

    h2('Where you stand')
    story.append(_p(f"{brand} is in the {band[1]} band ({audit.geo_score}/100). "
                    + (f"The 90-day plan projects {plan['projected']}; doing nothing drifts to {plan.get('status_quo')} as cited pages age." if plan.get('projected') is not None else ''), st['body']))
    story.append(Spacer(1, 4))
    story.append(_maturity_ladder(audit.geo_score, band_key, W))

    h2('Visibility depth - reach, position and sentiment')
    story.append(_p(f"When {brand} appears in an answer: on how many engines, where it ranks, and how it is described.", st['sub']))
    depth_tiles = [
        ('ENGINE REACH', f"{depth['reach']} / {depth['engines_total']}", ', '.join(depth['reach_names']) or 'none'),
        ('AVG POSITION', f"#{depth['avg_position']}" if depth['avg_position'] is not None else '—', 'order among brands named'),
        ('TOP-3 RATE', _pct(depth['top3_rate']) if depth['top3_rate'] is not None else '—', 'of appearances in the top 3'),
        ('#1 RANK RATE', _pct(depth['first_rate']) if depth['first_rate'] is not None else '—', 'of appearances named first'),
        ('SENTIMENT', f"{_pct(sent.get('positive'))} positive" if sent else '—', f"{_pct(sent.get('neutral'))} neutral · {_pct(sent.get('negative'))} negative" if sent else ''),
    ]
    tw = W / 5
    dt = Table([[_tile(a, b, c, st, tw - 4) for a, b, c in depth_tiles]], colWidths=[tw] * 5)
    dt.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story += [dt, Spacer(1, 6)]
    if depth.get('reach') or depth.get('avg_position') is not None:
        takeaway(f"When {brand} does get named, it is named on {depth['reach']} of {depth['engines_total']} engines"
                 + (f", on average in position #{depth['avg_position']} among the brands listed" if depth.get('avg_position') is not None else '')
                 + (f", and first {_pct(depth['first_rate'])} of the time" if depth.get('first_rate') is not None else '')
                 + (f". {_pct(sent.get('positive'))} of those mentions are positive in tone." if sent else '.')
                 + " Being named is only half the job - being named early and positively is what turns a mention into a recommendation.")
    weakest = min((e for e in engines if e.get('answered')), key=lambda e: e.get('mention_rate', 0), default=None)
    if weakest and weakest.get('mention_rate', 1) < 0.5:
        callout('The strategic imperative',
                f"{brand} is weak or invisible on {weakest['platform']} ({round(100 * weakest.get('mention_rate', 0))}% of prompts)"
                + (f", where {weakest['top_rival']} owns the conversation." if weakest.get('top_rival') else '.'), tone='bad')
    story.append(PageBreak())

    # ---------------------------------------------------------------- 02 AI search visibility
    part('02', 'AI search visibility', sentence(intros.get('geo')) or f"{brand} is named on {mention_rate}% of answers across {len(engines)} engine{'s' if len(engines) != 1 else ''}.")
    h2('GEO audit - visibility by engine')
    story.append(_p(f"Share of answers in which {brand} is named, per engine. Higher is better.", st['sub']))
    if engines:
        story.append(_hbar([e.get('platform', '') for e in engines], [round(100 * e.get('mention_rate', 0)) for e in engines], W, height=max(60, 20 * len(engines) + 24)))
        rows = [['Engine', 'Answered', 'Mentioned', 'Cited', 'Avg position', 'Top rival', 'Prefers you']]
        for e in engines:
            rows.append([e.get('platform', ''), e.get('answered', 0), f"{e.get('mentioned', 0)} ({round(100 * e.get('mention_rate', 0))}%)",
                         e.get('cited', 0), e.get('avg_position') if e.get('avg_position') is not None else '—',
                         f"{e['top_rival']} ({e.get('top_rival_mentions', 0)}x)" if e.get('top_rival') else '—', 'yes' if e.get('preferred') else 'no'])
        story.extend([_grid(rows, [W * 0.2, W * 0.11, W * 0.15, W * 0.1, W * 0.13, W * 0.19, W * 0.12]), Spacer(1, 6)])
        answered = [e for e in engines if e.get('answered')]
        if answered:
            best = max(answered, key=lambda e: e.get('mention_rate', 0))
            worst = min(answered, key=lambda e: e.get('mention_rate', 0))
            cited_total = sum(e.get('cited', 0) for e in answered)
            asked_total = sum(e.get('answered', 0) for e in answered)
            takeaway(f"{brand} is named most on {best['platform']} ({round(100 * best.get('mention_rate', 0))}% of answers)"
                     + (f" and least on {worst['platform']} ({round(100 * worst.get('mention_rate', 0))}%)" if worst is not best else '')
                     + f". Across all engines it is cited as a source on {cited_total} of {asked_total} answers"
                     + (f"; {worst.get('top_rival')} is the rival named most where {brand} is weakest." if worst.get('top_rival') else '.'))

        h2('Engine-by-engine breakdown')
        howto('Each card is one AI engine. The header shows the share of buyer questions on which the engine named you (green 50%+, amber 25%+, red below). '
              '"+" lines are what the engine already does for you, "-" lines are the gaps, and "Do next" is the single action that would move that engine most.')
        cards = []
        for e in engines:
            strengths, gaps = _engine_notes(e, brand)
            rate = round(100 * e.get('mention_rate', 0))
            tone = GREEN if rate >= 50 else AMBER if rate >= 25 else RED
            head = Table([[_p(e.get('platform', ''), st['card_head']), _p(f"{rate}%", st['card_pct'])]], colWidths=[W / 2 - 4 - 22 * mm, 22 * mm])
            head.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), tone), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                      ('LEFTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
            body = [_p(f"named on {rate}% of prompts · cited {e.get('cited', 0)}/{e.get('answered', 0)}"
                       + (f" · avg position {e['avg_position']}" if e.get('avg_position') is not None else ''), st['smallmuted']), Spacer(1, 2)]
            body += [Paragraph(f"<font color='{GREEN.hexval()}'><b>+</b></font> {_esc(s_)}", st['small']) for s_ in strengths]
            body += [Paragraph(f"<font color='{RED.hexval()}'><b>-</b></font> {_esc(g)}", st['small']) for g in gaps]
            body += [Spacer(1, 3), Paragraph(f"<font color='{PRIMARY.hexval()}'><b>Do next:</b></font> {_esc(_engine_recommendation(e, brand))}", st['small'])]
            inner = Table([[head], [_box(body, W / 2 - 4, border=WHITE, pad=7)]], colWidths=[W / 2 - 4])
            inner.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.6, LINE), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                       ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
            cards.append(inner)
        for i in range(0, len(cards), 2):
            pair = cards[i:i + 2]
            if len(pair) == 1:
                pair.append('')
            t = Table([pair], colWidths=[W / 2] * 2)
            t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
            story.append(t)

    fun = geo.get('funnel')
    if fun and fun.get('platforms'):
        h2('Funnel stage heatmap')
        story.append(_p('Mention rate by buyer stage x engine (% of answers)', st['sub']))
        howto('Rows are the three stages of a buyer journey - TOFU (awareness: "what is..."), MOFU (evaluation: "which is better..."), BOFU (decision: "best X to buy"). '
              'Each cell is the share of answers at that stage, on that engine, that named you. Green is 67%+, amber 34-66%, red below 34%.')
        plats = fun['platforms']
        rows = [['Stage'] + [p.replace('Google ', '') for p in plats] + ['All engines']]
        extra = []
        for ri, stage in enumerate(fun.get('stages') or [], 1):
            total = (fun.get('by_stage') or {}).get(stage, {})
            row = [f"{(fun.get('labels') or {}).get(stage, stage)}  ({total.get('prompts', 0)} prompts)"]
            cells = [((fun.get('cells') or {}).get(stage) or {}).get(p, {}) for p in plats] + [total]
            for ci, c in enumerate(cells, 1):
                rate = c.get('rate')
                row.append('—' if rate is None else f"{rate}%  ({c.get('mentioned', 0)}/{c.get('asked', 0)})")
                extra.append(('BACKGROUND', (ci, ri), (ci, ri), MUTED_BG if rate is None else GREEN_BG if rate >= 67 else AMBER_BG if rate >= 34 else RED_BG))
            rows.append(row)
        cw = (W - 44 * mm) / (len(plats) + 1)
        story.extend([_grid(rows, [44 * mm] + [cw] * (len(plats) + 1), zebra=False, extra=extra + [('ALIGN', (1, 1), (-1, -1), 'CENTER')]), Spacer(1, 6)])
        story.append(Spacer(1, 4))
        callout('The AI dark funnel', f"when {brand} does not appear in these answers, prospects never discover it, even when they search for the exact problem it solves. "
                "A gap at BOFU is a lost decision; a gap at TOFU is a buyer who never hears the name.")
        stages = [(s, (fun.get('by_stage') or {}).get(s) or {}) for s in (fun.get('stages') or [])]
        stages = [(s, v) for s, v in stages if v.get('rate') is not None]
        if stages:
            weakest_stage = min(stages, key=lambda x: x[1]['rate'])
            strongest_stage = max(stages, key=lambda x: x[1]['rate'])
            lbl = fun.get('labels') or {}
            takeaway(f"{brand} is strongest at the {lbl.get(strongest_stage[0], strongest_stage[0])} stage ({strongest_stage[1]['rate']}% of answers) "
                     f"and weakest at {lbl.get(weakest_stage[0], weakest_stage[0])} ({weakest_stage[1]['rate']}%)"
                     + (" - the decision stage, where a missing name is a lost sale." if weakest_stage[0] == 'bottom' else
                        " - the awareness stage, where buyers first learn which brands exist." if weakest_stage[0] == 'top' else
                        " - the comparison stage, where buyers shortlist options."))

    if evidence:
        won = [ev for ev in evidence if ev.get('gap_type') == 'won']
        lost = [ev for ev in evidence if ev.get('gap_type') in ('visibility_gap', 'position_gap')]
        h2('Prompts you win · prompts you lose')
        colw = [Paragraph(f"<font color='{GREEN.hexval()}'><b>PROMPTS YOU WIN ({len(won)})</b></font>", st['small'])]
        colw += [Paragraph(f"<font color='{GREEN.hexval()}'>+</font> {_esc(ev.get('prompt_text', ''))}", st['small']) for ev in won[:8]] or [_p('None yet', st['smallmuted'])]
        coll = [Paragraph(f"<font color='{RED.hexval()}'><b>PROMPTS YOU LOSE ({len(lost)})</b></font>", st['small'])]
        coll += [Paragraph(f"<font color='{RED.hexval()}'>-</font> {_esc(ev.get('prompt_text', ''))}"
                           + (f" <font color='{MUTED.hexval()}'>· {_esc(ev['top_competitor'])}</font>" if ev.get('top_competitor') else ''), st['small']) for ev in lost[:8]] or [_p('None', st['smallmuted'])]
        t = Table([[_box(colw, W / 2 - 4, bg=GREEN_BG, border=GREEN_BG), _box(coll, W / 2 - 4, bg=RED_BG, border=RED_BG)]], colWidths=[W / 2] * 2)
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]))
        story.append(t)

        h2('Prompt evidence')
        howto('One row per buyer question. The coloured dot under each engine shows what happened: green = the engine named you and linked to your site, '
              'amber = named you without a link, red = did not name you, grey = no answer. "Cited instead of you" lists the sites the engine linked to. '
              'Gap type: Won = you were a top answer; Position gap = named but after the top three; Visibility gap = never named while rivals were; Educational = nobody is named, not a real gap.')
        counts = geo.get('gap_counts') or {}
        legend = ' &nbsp; '.join(f"<font color='{c.hexval()}'>●</font> {n}" for n, c in (('cited', GREEN), ('mentioned', AMBER), ('absent', RED), ('no answer', MUTED)))
        story.append(Paragraph(_esc(' · '.join(f"{n} {GAP_LABELS.get(k, (k, MUTED))[0].lower()}" for k, n in counts.items())) + f" &nbsp;&nbsp; {legend}", st['sub']))
        pl = platforms or sorted({p for ev in evidence for p in (ev.get('engines') or {})})
        # Engine names are abbreviated in narrow columns; the legend line above the table spells them out.
        short = {p: (p.replace('Google ', '')[:4] if len(pl) >= 3 else p.replace('Google ', '')) for p in pl}
        if len(pl) >= 3:
            story.append(_p('Engine columns: ' + ' · '.join(f"{short[p]} = {p}" for p in pl), st['smallmuted']))
        rows = [['What buyers ask', 'Stage'] + [short[p] for p in pl] + ['Top competitor', 'Cited instead of you', 'Gap type']]
        for ev in evidence:
            cells = [_p(ev.get('prompt_text', ''), st['small']), (ev.get('funnel_stage') or '—').capitalize()]
            for p in pl:
                col = OUTCOME.get((ev.get('engines') or {}).get(p, ''), MUTED_BG)
                cells.append(Paragraph(f"<font color='{col.hexval()}' size='10'>●</font>", st['small']))
            glabel, gcol = GAP_LABELS.get(ev.get('gap_type') or '', ('—', MUTED))
            cells += [_p(ev.get('top_competitor') or '—', st['small']), _p(' · '.join(ev.get('cited_instead') or []) or '—', st['smallmuted']),
                      Paragraph(f"<font color='{gcol.hexval()}'>{_esc(glabel)}</font>", st['small'])]
            rows.append(cells)
        # Column plan that keeps the question column readable from 1 to 6 engines:
        # engine columns shrink first, then the competitor / cited columns.
        n = len(pl)
        ew = 15 * mm if n <= 2 else 11 * mm if n <= 4 else 9 * mm
        stage_w, comp_w, cited_w, gap_w = 16 * mm, 24 * mm, 36 * mm, 22 * mm
        first = W - (stage_w + n * ew + comp_w + cited_w + gap_w)
        if first < 50 * mm:
            comp_w, cited_w = 20 * mm, 26 * mm
            first = W - (stage_w + n * ew + comp_w + cited_w + gap_w)
        widths = [first, stage_w] + [ew] * n + [comp_w, cited_w, gap_w]
        story.extend([_grid(rows, widths, extra=[('ALIGN', (2, 1), (1 + n, -1), 'CENTER')]), Spacer(1, 6)])

    comp = geo.get('competitors') or {}
    if len(comp.get('rows') or []) > 1:
        h2('Competitor matrix')
        intro('competitors')
        story.append(_p('Every brand the engines named - prompts it ranks in, and its average order of mention (1 = named first)', st['sub']))
        howto('"Prompts ranked" is how many of the buyer questions the brand was named on, out of all questions asked. "Avg position" is the order it was named in '
              '(1.0 = always first). The three stage columns split that by funnel stage. Your own row is highlighted.')
        rows = [['Brand', 'Prompts ranked', 'Share', 'Avg position', 'TOFU', 'MOFU', 'BOFU']]
        extra = []
        for i, c in enumerate(comp['rows'], 1):
            stg = c.get('stages') or {}
            cell = (lambda s: f"{(stg.get(s) or {}).get('ranked', 0)}/{(stg.get(s) or {}).get('of', 0)}" if (stg.get(s) or {}).get('of') else '—')
            rows.append([f"{c.get('name', '')}{' (you)' if c.get('is_you') else ''}", f"{c.get('prompts_ranked', 0)} / {c.get('prompts_total', 0)}", f"{c.get('share', 0)}%",
                         c.get('avg_position') if c.get('avg_position') is not None else '—', cell('top'), cell('middle'), cell('bottom')])
            if c.get('is_you'):
                extra.append(('BACKGROUND', (0, i), (-1, i), PRIMARY_TINT))
        story.extend([_grid(rows, [W * 0.28, W * 0.15, W * 0.1, W * 0.13, W * 0.11, W * 0.11, W * 0.12], extra=extra + [('ALIGN', (1, 1), (-1, -1), 'CENTER')]), Spacer(1, 6)])
        story.append(Spacer(1, 4))
        for c in (comp.get('callouts') or [])[:3]:
            callout(c.get('title', ''), c.get('text', ''), tone='soft')
        crow = comp['rows']
        you_row = next((c for c in crow if c.get('is_you')), None)
        rivals = [c for c in crow if not c.get('is_you')]
        if you_row and rivals:
            rank = crow.index(you_row) + 1
            lead = rivals[0]
            takeaway(f"{brand} ranks #{rank} of {len(crow)} brands the engines named, appearing on {you_row.get('prompts_ranked', 0)} of {you_row.get('prompts_total', 0)} questions. "
                     f"{lead.get('name')} is the brand to beat: named on {lead.get('prompts_ranked', 0)} questions at an average position of {lead.get('avg_position', '—')}"
                     + (" - ahead of you on both counts." if (lead.get('prompts_ranked', 0) > you_row.get('prompts_ranked', 0)) else " - you are already ahead on questions ranked."))

    sov = geo.get('share_of_voice') or []
    if sov:
        h2('Relative share of voice')
        you = next((x for x in sov if x.get('is_you')), None)
        top = sov[:8]
        if you is not None and you not in top:
            top = sov[:7] + [you]          # the brand's own bar is always on the chart, however low
        loud = max((x.get('mentions', 0) for x in top), default=0) or 1
        if you:
            story.append(_p(f"{brand} sits at {round(100 * you.get('mentions', 0) / loud)}% of {top[0].get('name')}, the loudest tracked brand (set at 100%).", st['sub']))
        you_idx = next((i for i, x in enumerate(top) if x.get('is_you')), None)
        story.append(_hbar([f"{x.get('name')}{' (you)' if x.get('is_you') else ''}" for x in top], [round(100 * x.get('mentions', 0) / loud) for x in top], W,
                           height=18 * len(top) + 24, highlight=you_idx))

    if ctrl.get('total_citations'):
        h2('Citation-source breakdown')
        story.append(_p(f"Who owns the {ctrl['total_citations']} URLs the engines cited on your prompts.", st['sub']))
        donut = _donut([('Owned', ctrl.get('owned', 0), PRIMARY), ('Competitor', ctrl.get('competitor', 0), AMBER), ('Third party', ctrl.get('third_party', 0), MUTED)], W * 0.45)
        tops = [_p('Top sources', st['h3'])] + [_p(f"{s_.get('host')} - {s_.get('count')} citation{'s' if s_.get('count') != 1 else ''}", st['small']) for s_ in (ctrl.get('top_sources') or [])[:6]]
        root = ("Most citations point at other people's pages about you: comparison tables, pricing and FAQ pages on your own site are what engines cite."
                if (ctrl.get('owned') or 0) < 30 else 'Your own pages carry a healthy share of the citations; keep them fresh.')
        tops += [Spacer(1, 4), _box([Paragraph(f"<b>Root cause</b> — {_esc(root)}", st['callout'])], W * 0.5, bg=AMBER_BG, border=AMBER_BG, left_bar=AMBER)]
        t = Table([[donut, tops]], colWidths=[W * 0.47, W * 0.53])
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
        story.append(t)
        top_src = (ctrl.get('top_sources') or [{}])[0]
        takeaway(f"When the engines back up an answer with a link, {_pct(ctrl.get('owned'))} of those links point at your own site, {_pct(ctrl.get('competitor'))} at rivals "
                 f"and {_pct(ctrl.get('third_party'))} at third parties" + (f"; the single most-cited site is {top_src.get('host')} ({top_src.get('count')} citations)" if top_src.get('host') else '')
                 + ". The pages engines cite are the pages that shape what they say - owning more of them is the fastest way to change the story.")

    if nar.get('available'):
        h2('Brand narrative')
        intro('narrative')
        story.append(_p(f"Not whether the engines name {brand} - how they describe it · {nar.get('answers_analysed', 0)} answers analysed", st['sub']))
        head = f"Dominant framing: {nar.get('dominant_framing') or '—'}"
        if nar.get('framing_share') is not None:
            head += f" (in {nar['framing_share']}% of answers)"
        if nar.get('consistency') is not None:
            head += f" · consistency {nar['consistency']}%"
        story += [_p(head, st['body']), Spacer(1, 4)]
        present = nar.get('descriptors_present') or []
        left = [_p('AI DESCRIPTORS (PRESENT)', st['eyebrow'])]
        left += [_hbar([d.get('descriptor', '')[:34] for d in present], [d.get('share', 0) for d in present], W * 0.5 - 8, height=16 * len(present) + 22)] if present else [_p('—', st['smallmuted'])]
        right = [_p('MISSING DESCRIPTORS', st['eyebrow'])]
        right += [Paragraph(f"<font color='{RED.hexval()}'>-</font> {_esc(m)}", st['small']) for m in (nar.get('descriptors_missing') or [])] or [_p('—', st['smallmuted'])]
        right += [Spacer(1, 6), _p('FRAMING BY ENGINE', st['eyebrow'])]
        eng_rows = [['Engine', 'Leads with', 'Tone', 'Matches site']] + [[e.get('platform', ''), e.get('leads_with', ''), (e.get('tone') or '').capitalize(), (e.get('matches_profile') or '').capitalize()] for e in (nar.get('by_engine') or [])]
        right.append(_grid(eng_rows, [W * 0.12, W * 0.18, W * 0.09, W * 0.1], font_size=7))
        t = Table([[left, right]], colWidths=[W * 0.5, W * 0.5])
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
        story += [t, Spacer(1, 4)]
        if nar.get('narrative_gap'):
            callout('Narrative gap', nar['narrative_gap'])
        for o in nar.get('off_brand') or []:
            callout(f"Off-brand ({o.get('platform', '')})", f"“{o.get('claim', '')}” {o.get('why', '')}", tone='warn')

    if seo and seo.get('keywords_total'):
        h2('SEO audit')
        story.append(_p(f"{seo['keywords_total']} keywords discovered · top-10 on {seo.get('top10', 0)} · striking distance {seo.get('striking_distance', 0)} · visibility index {seo.get('visibility', '—')}", st['sub']))
        rows = [['Keyword', 'Volume', 'Position', 'Outranked by', 'GEO']]
        for k in (seo.get('top_keywords') or [])[:12]:
            rows.append([k.get('keyword', ''), f"{k['search_volume']:,}" if k.get('search_volume') else '—', k.get('position') if k.get('position') else '—',
                         ', '.join(k.get('outranked_by') or []) or '—', '—' if k.get('geo_engines_mentioning') is None else f"{k['geo_engines_mentioning']}/{len(engines)}"])
        story.extend([_grid(rows, [W * 0.32, W * 0.12, W * 0.12, W * 0.32, W * 0.12]), Spacer(1, 6)])
    story.append(PageBreak())

    # ---------------------------------------------------------------- 03 website health
    measures = r.get('measures') or []
    pillars = r.get('pillars') or {}
    part('03', 'Website health', sentence(intros.get('website')) or (f"{crawl['pages_sampled']} of {brand}'s pages sampled: what the engines can read, and how citable it is."
                                                           if crawl and crawl.get('pages_sampled') else 'On-site signals were not measured in this audit.'))
    if measures:
        h2('Findable · Cited · Chosen - scorecard')
        story.append(_p('Thirteen measures behind the score, grouped by the three questions that matter: can the engines reach and read you (Findable), '
                        'do they use you as a source (Cited), and are you the answer they give (Chosen).', st['sub']))
        howto('Each measure has a score out of 100 and a target. Green = at or above target, red = below. The priority chip says how urgent it is: '
              'Critical (well below target), Important (close), On track (met), Not measured (the audit could not collect that signal).')
        rows = [['Pillar', 'Measure', 'Value', 'Score / target', 'Priority']]
        extra = []
        for key, title in (('findable', 'Findable'), ('cited', 'Cited'), ('chosen', 'Chosen')):
            ms = [m for m in measures if m.get('pillar') == key]
            if not ms:
                continue
            i0 = len(rows)
            ps = pillars.get(key)
            rows.append([_p(f"{title}  {ps if ps is not None else 'not measured'}", st['small']), '', '', '', ''])
            extra += [('SPAN', (0, i0), (-1, i0)), ('BACKGROUND', (0, i0), (-1, i0), PRIMARY_TINT)]
            for m in ms:
                sc = m.get('score')
                colour = MUTED if sc is None else GREEN if m.get('status') == 'pass' else RED
                score_txt = '—' if sc is None else f"{sc} / {m.get('target', '')}"
                rows.append(['', _p(m.get('label', ''), st['small']), _p(m.get('value') or m.get('evidence') or '—', st['smallmuted']),
                             Paragraph(f"<font color='{colour.hexval()}'>{_esc(score_txt)}</font>", st['small']), _status_chip(sc, m.get('target', 70), st)])
        story.extend([_grid(rows, [22 * mm, W * 0.26, W * 0.32, 20 * mm, 30 * mm], zebra=False, extra=extra), Spacer(1, 6)])
        failing = [m for m in measures if m.get('status') == 'fail']
        if failing:
            worst = min(failing, key=lambda m: (m.get('score') or 0) - (m.get('target') or 0))
            takeaway(f"{len(failing)} of {len([m for m in measures if m.get('score') is not None])} measured signals are below target. "
                     f"The biggest gap is {worst.get('label', '').lower()} ({worst.get('score')} against a target of {worst.get('target')})"
                     + (f" - {worst.get('value')}." if worst.get('value') else '.')
                     + " Findable is what you control on your own site; Cited and Chosen move once the engines start reading and trusting it.")

    health = (crawl or {}).get('health') or {}
    if health.get('categories'):
        h2('Website health scorecard')
        story.append(_p(f"Site score {health.get('score') if health.get('score') is not None else '—'} / 100 - eight weighted categories; "
                        "unmeasured categories drop out of the weighting.", st['sub']))
        rows = [['Category', 'Weight', 'Score', 'Priority', 'Evidence']]
        for cat in health['categories']:
            sc = cat.get('score')
            colour = MUTED if sc is None else GREEN if sc >= 80 else AMBER if sc >= 60 else RED
            rows.append([_p(cat.get('label', ''), st['small']), f"{cat.get('weight', 0)}%",
                         Paragraph(f"<font color='{colour.hexval()}'><b>{sc if sc is not None else '—'}</b></font>", st['small']),
                         _priority_chip(cat.get('priority'), st), _p(cat.get('detail', ''), st['smallmuted'])])
        story.extend([_grid(rows, [W * 0.24, 14 * mm, 14 * mm, 30 * mm, W * 0.76 - 58 * mm], extra=[('ALIGN', (1, 1), (2, -1), 'CENTER')]), Spacer(1, 6)])
        measured_cats = [c for c in health['categories'] if c.get('score') is not None]
        if measured_cats:
            weak = sorted(measured_cats, key=lambda c: c['score'])[:2]
            strong = max(measured_cats, key=lambda c: c['score'])
            takeaway(f"The site scores {health.get('score')}/100. Its strongest area is {strong['label'].lower()} ({strong['score']}); the two areas dragging the score down are "
                     f"{weak[0]['label'].lower()} ({weak[0]['score']})" + (f" and {weak[1]['label'].lower()} ({weak[1]['score']})" if len(weak) > 1 else '')
                     + ". Fixing the lowest category first gives the biggest lift, because each category is weighted.")

    bl = (crawl or {}).get('backlinks') or {}
    if bl.get('source'):
        h2('Backlink analysis')
        story.append(_p(f"The links pointing at {audit.host} shape how much the engines trust and cite it. Verified via a third-party link index"
                        + (f"; links seen since {bl['first_seen'][:4]}." if bl.get('first_seen') else '.'), st['sub']))
        auth = bl.get('authority_score')
        tiles = [_tile('AUTHORITY SCORE', f"{auth}/100" if auth is not None else '—', 'how trusted the site is across the web', st, W / 4 - 4),
                 _tile('SITES LINKING IN', f"{bl.get('referring_domains', 0):,}", 'unique websites that link to you', st, W / 4 - 4),
                 _tile('TOTAL BACKLINKS', f"{bl.get('backlinks', 0):,}", f"{bl['dofollow_share']}% dofollow" if bl.get('dofollow_share') is not None else 'all individual links', st, W / 4 - 4),
                 _tile('BROKEN BACKLINKS', f"{bl.get('broken_backlinks', 0):,}", 'authority to reclaim with redirects', st, W / 4 - 4)]
        bt = Table([tiles], colWidths=[W / 4] * 4)
        bt.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        story.append(bt)

    cwv = (crawl or {}).get('cwv') or {}
    if cwv.get('source'):
        h2('Core Web Vitals')
        story.append(_p(f"{'Real-user data (CrUX, 75th percentile)' if cwv['source'] == 'field' else 'Lab data (Lighthouse)'} for the homepage on mobile. "
                        "Slow pages are crawled less often, so content updates reach AI indexes later.", st['sub']))
        tiles = []
        for key, label, unit in (('lcp_ms', 'LCP - LARGEST CONTENTFUL PAINT', ' ms'), ('cls', 'CLS - LAYOUT SHIFT', ''), ('inp_ms', 'INP - INTERACTION DELAY', ' ms')):
            v = cwv.get(key)
            rating, rcol = CWV_RATING.get(cwv.get(f"{key}_rating") or '', ('no data', MUTED))
            tiles.append(_tile(label, f"{v}{unit}" if v is not None else '—', rating, st, W / 4 - 4))
        tiles.append(_tile('CWV SCORE', str(cwv.get('score')) if cwv.get('score') is not None else '—',
                           f"Lighthouse performance {cwv['performance_score']}" if cwv.get('performance_score') is not None else 'good = 100 · poor = 0', st, W / 4 - 4))
        ct = Table([tiles], colWidths=[W / 4] * 4)
        ct.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        story.append(ct)
        if cwv.get('mobile_friendly') is not None:
            story.append(Spacer(1, 3))
            story.append(Paragraph(f"Mobile-friendly: <font color='{(GREEN if cwv['mobile_friendly'] else RED).hexval()}'>{'yes' if cwv['mobile_friendly'] else 'no - viewport check failed'}</font>", st['small']))
        if len(cwv.get('pages') or []) > 1:
            story.append(Spacer(1, 4))
            rows = [['Page', 'LCP', 'CLS', 'INP', 'Score']]
            for pg in cwv['pages'][:5]:
                def cell(v, rating):
                    col = CWV_RATING.get(rating or '', ('', INK))[1]
                    return Paragraph(f"<font color='{col.hexval()}'>{_esc(v if v is not None else '—')}</font>", st['small'])
                rows.append([_p(_path_of(pg.get('url', '')), st['small']), cell(pg.get('lcp_ms'), pg.get('lcp_ms_rating')), cell(pg.get('cls'), pg.get('cls_rating')),
                             cell(pg.get('inp_ms'), pg.get('inp_ms_rating')), str(pg.get('score') if pg.get('score') is not None else '—')])
            story.extend([_grid(rows, [W * 0.52, W * 0.12, W * 0.12, W * 0.12, W * 0.12], extra=[('ALIGN', (1, 1), (-1, -1), 'CENTER')]), Spacer(1, 6)])
            if cwv.get('site_score') is not None:
                story.append(_p(f"Average across the pages tested: {cwv['site_score']}", st['smallmuted']))

    idx = (crawl or {}).get('indexability')
    if idx:
        h2('Indexability & security')
        story.append(_p('Can search engines index the sampled pages, and is the site served safely.', st['sub']))
        labels = [('indexable', 'INDEXABLE', GREEN), ('not_indexable', 'NOT INDEXABLE', RED), ('canonicalised', 'CANONICALISED ELSEWHERE', AMBER),
                  ('redirected', 'REDIRECTS', AMBER), ('unknown', 'COULD NOT CHECK', MUTED)]
        tiles = [_tile(label, str(idx.get(key, 0)), '', st, W / 5 - 4) for key, label, _ in labels]
        it = Table([tiles], colWidths=[W / 5] * 5)
        it.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        story.append(it)
        site = crawl.get('site') or {}
        sm = crawl.get('sitemap_health') or {}

        def yn(v, yes, no, unknown='not checked'):
            col, text = (GREEN, yes) if v is True else (RED, no) if v is False else (MUTED, unknown)
            return Paragraph(f"<font color='{col.hexval()}'>{_esc(text)}</font>", st['small'])
        rows = [['Check', 'Result', 'Why it matters'],
                ['http:// redirects to https://', yn(site.get('http_redirects_to_https'), 'yes', 'no - both versions reachable'), _p('two reachable copies split authority and expose the insecure one', st['smallmuted'])],
                ['HSTS header', yn(site.get('hsts'), 'present', 'missing', 'unknown'), _p('tells browsers to always use HTTPS', st['smallmuted'])],
                ['SSL certificate', yn(not site.get('ssl_error') if site else None, 'ok', 'error on at least one page'), _p('a failing certificate stops crawlers and warns visitors', st['smallmuted'])]]
        cert = site.get('certificate') or {}
        if cert.get('expires'):
            days = cert.get('days_left')
            rows.append(['Certificate expiry', Paragraph(f"<font color='{(RED if (days is not None and days < 30) else GREEN).hexval()}'>{_esc(cert['expires'])} ({days} days)</font>", st['small']),
                         _p(f"issued by {cert.get('issuer')}" if cert.get('issuer') else 'renew before it lapses', st['smallmuted'])])
        sh = site.get('security_headers') or {}
        if sh:
            present = sum(1 for v in sh.values() if v)
            rows.append(['Security headers', Paragraph(f"<font color='{(GREEN if present == len(sh) else AMBER).hexval()}'>{present} of {len(sh)} present</font>", st['small']),
                         _p('CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy', st['smallmuted'])])
        if crawl.get('soft_404_pages'):
            rows.append(['Soft 404 pages', Paragraph(f"<font color='{RED.hexval()}'>{crawl['soft_404_pages']}</font>", st['small']), _p('say "not found" but return 200', st['smallmuted'])])
        if crawl.get('avg_html_kb') is not None:
            rows.append(['Average HTML weight', _p(f"{crawl['avg_html_kb']} KB · {crawl.get('avg_scripts', 0)} scripts/page", st['small']), _p('heavy HTML slows first paint and crawling', st['smallmuted'])])
        if sm.get('listed'):
            rows.append(['Sitemap health', _p(f"{sm['listed']:,} URLs listed · {sm.get('checked', 0)} checked · {len(sm.get('errors') or [])} with problems · {len(sm.get('not_in_sitemap') or [])} crawled pages not listed", st['small']),
                         _p('a sitemap should list only live, indexable, final URLs', st['smallmuted'])])
        for label, key in (('Redirect chains (2+ hops)', 'redirect_chains'), ('Thin content pages', 'thin_pages')):
            if crawl.get(key):
                rows.append([label, _p(str(crawl[key]), st['small']), ''])
        if crawl.get('duplicate_groups'):
            rows.append(['Near-duplicate page groups', _p(f"{len(crawl['duplicate_groups'])} groups · {sum(len(g) for g in crawl['duplicate_groups'])} pages", st['small']), _p('same body text on several URLs competes with itself', st['smallmuted'])])
        if crawl.get('hreflang_errors'):
            rows.append(['hreflang errors', _p(str(len(crawl['hreflang_errors'])), st['small']), _p('invalid codes or missing return tags void the whole set', st['smallmuted'])])
        story.extend([_grid(rows, [W * 0.3, W * 0.32, W * 0.38]), Spacer(1, 6)])

    if crawl and crawl.get('pages_sampled'):
        h2('AI crawlability')
        bots = [['AI crawler', 'Engine', 'Access', 'Impact']]
        for b in crawl.get('bots') or []:
            ok = b.get('allowed')
            bots.append([b.get('bot', ''), b.get('engine', ''), Paragraph(f"<font color='{(GREEN if ok else RED).hexval()}'>{'Allowed' if ok else 'BLOCKED'}</font>", st['small']),
                         _p(f"{b.get('engine', '')} can index your content" if ok else f"{b.get('engine', '')} cannot read your pages", st['smallmuted'])])
        sitemap_text = 'Not found'
        if crawl.get('sitemap_present'):
            sitemap_text = 'Present' + (f" - index with {crawl['sitemap_children']} child sitemaps" if crawl.get('sitemap_children') else '')
        bots += [['robots.txt', '', _p('present' if crawl.get('robots_present') else 'none (everything allowed)', st['small']), ''],
                 ['sitemap.xml', '', Paragraph(f"<font color='{(GREEN if crawl.get('sitemap_present') else RED).hexval()}'>{_esc(sitemap_text)}</font>", st['small']),
                  _p('lets crawlers discover new pages quickly', st['smallmuted'])],
                 ['llms.txt', '', _p('present' if crawl.get('llms_txt') else 'not detected · optional', st['small']), _p('does not affect the score', st['smallmuted'])]]
        lc = crawl.get('link_check') or {}
        if lc.get('checked'):
            lc_text = f"{lc['broken']} of {lc['checked']} broken" if lc.get('broken') else f"{lc['checked']} checked - none broken"
            bots.append(['Internal links checked', '', Paragraph(f"<font color='{(RED if lc.get('broken') else GREEN).hexval()}'>{_esc(lc_text)}</font>", st['small']),
                         _p(' · '.join(f"{_path_of(e.get('url', ''))} ({e.get('status') or 'unreachable'})" for e in (lc.get('examples') or [])[:3]) or 'links the crawl did not fetch, HEAD-checked', st['smallmuted'])])
        story.extend([_grid(bots, [W * 0.2, W * 0.2, W * 0.2, W * 0.4]), Spacer(1, 6)])

        h2('Content & schema signals')
        sig_raw = [['Signal', 'Value', 'What it means'],
               ['Schema coverage', f"{_pct(crawl.get('schema_coverage'))} of pages", 'pages carrying JSON-LD; the types matter as much as the coverage'],
               ['Key schema types', ', '.join(crawl.get('recommended_types_present') or []) or 'none', 'FAQPage, HowTo, Product, Article, Person are what engines extract'],
               ['Pages with author bio', _pct(crawl.get('author_share')), 'bylines are the trust signal engines look for'],
               ['Outbound citations / page', crawl.get('avg_external_links') if crawl.get('avg_external_links') is not None else '—', 'cited sources make a page look researched'],
               ['Average word count', f"{crawl['avg_word_count']:,}" if crawl.get('avg_word_count') else '—', 'depth, not length, wins citations'],
               ['Question headings / tables', f"{_pct(crawl.get('question_heading_share'))} / {_pct(crawl.get('table_share'))}", 'answer-shaped structure is easiest to cite'],
               ['Stale pages (12 months+)', f"{crawl.get('stale_pages', 0)} of {crawl.get('dated_pages', 0)} dated" if crawl.get('dated_pages') else 'no dates found', 'old pages lose citations fastest'],
               ['Latest update seen', crawl.get('freshest') or '—', '']]
        if crawl.get('avg_internal_links') is not None:
            sig_raw += [['Internal links / page', f"{crawl['avg_internal_links']}" + (f" · {crawl['descriptive_anchor_share']}% descriptive anchors" if crawl.get('descriptive_anchor_share') is not None else ''),
                         'crawlers follow internal links to find and rank pages; anchor text should say what the target is'],
                        ['Person schema / credentials', f"{_pct(crawl.get('person_schema_share'))} / {_pct(crawl.get('credential_share'))} of pages",
                         'author entities and trust claims (awards, registrations, certifications) are E-E-A-T evidence']]
        if crawl.get('schema_gaps'):
            sig_raw.append(['Schema fields missing', ' · '.join(f"{g.get('gap')} ({g.get('pages')})" for g in crawl['schema_gaps'][:3]),
                            'schema that is present but thin is not used by the engines'])
        sig = [sig_raw[0]] + [[a, _p(b, st['small']), _p(c, st['smallmuted'])] for a, b, c in sig_raw[1:]]
        story.extend([_grid(sig, [W * 0.3, W * 0.25, W * 0.45]), Spacer(1, 6)])

        delta = crawl.get('issue_delta')
        if delta:
            h2('Since the previous audit')
            story.append(_p(f"{delta.get('previous_total', 0)} issue types on {_fmt_date(delta.get('previous_completed_at')) or 'the previous audit'} · {delta.get('current_total', 0)} now"
                            + (f" · health was {delta['previous_health']}" if delta.get('previous_health') is not None else ''), st['sub']))
            cols = [[Paragraph(f"<font color='{GREEN.hexval()}'><b>FIXED ({len(delta.get('fixed') or [])})</b></font>", st['small'])]
                    + [_p(f"{f.get('label')} (was {f.get('was')})", st['small']) for f in (delta.get('fixed') or [])[:8]],
                    [Paragraph(f"<font color='{RED.hexval()}'><b>NEW ({len(delta.get('new') or [])})</b></font>", st['small'])]
                    + [_p(f"{f.get('label')} ({f.get('count')})", st['small']) for f in (delta.get('new') or [])[:8]],
                    [Paragraph(f"<font color='{AMBER.hexval()}'><b>CHANGED ({len(delta.get('changed') or [])})</b></font>", st['small'])]
                    + [_p(f"{f.get('label')} {f.get('from')} > {f.get('to')}", st['small']) for f in (delta.get('changed') or [])[:8]]]
            dt_ = Table([[_box(c, W / 3 - 4, pad=6) for c in cols]], colWidths=[W / 3] * 3)
            dt_.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
            story.append(dt_)

        issues = crawl.get('technical_issues')
        if issues is not None:
            h2('Technical SEO issues')
            counts = {s_: sum(1 for i in issues if i.get('severity') == s_) for s_ in ('critical', 'warning', 'info')}
            story.append(_p(f"{counts['critical']} critical · {counts['warning']} warnings · {counts['info']} info - counted over the {crawl.get('pages_sampled')} sampled pages", st['sub']))
            howto('Critical issues stop pages from ranking or being cited and should be fixed first; warnings cost visibility or speed; info items are polish. '
                  '"Pages" is how many sampled pages have the issue. Under each fix is the exact tag, header or setting to add.')
            if not issues:
                story.append(Paragraph(f"<font color='{GREEN.hexval()}'>No on-page or technical issues found on the sampled pages.</font>", st['body']))
            else:
                crit = [i for i in issues if i.get('severity') == 'critical']
                takeaway(f"{len(issues)} issue types were found across {crawl.get('pages_sampled')} sampled pages"
                         + (f"; {len(crit)} are critical - start with \"{crit[0].get('action', crit[0].get('label', ''))}\"" if crit else ', none of them critical')
                         + ". The Issues CSV next to the report lists every affected URL for your developer.")
                rows = [['Severity', 'Issue', 'Pages', 'Examples', 'Fix']]
                for i in issues[:14]:
                    col = SEVERITY_COLOUR.get(i.get('severity'), MUTED)
                    fix_cell = [Paragraph(f"<b>{_esc(i.get('action', ''))}.</b> <font color='{MUTED.hexval()}'>{_esc(i.get('fix', ''))}</font>", st['small'])]
                    if i.get('snippet'):
                        fix_cell.append(Paragraph(f"<font face='Courier' size='6' color='{PRIMARY_DARK.hexval()}'>{_esc(i['snippet'][:160])}</font>", st['small']))
                    rows.append([Paragraph(f"<font color='{col.hexval()}'><b>{_esc((i.get('severity') or '').capitalize())}</b></font>", st['small']),
                                 _p(i.get('label', ''), st['small']), f"{i.get('count', 0)} / {i.get('of', 0)}",
                                 _p(' · '.join((i.get('examples') or [])[:3]), st['smallmuted']), fix_cell])
                story.extend([_grid(rows, [16 * mm, W * 0.22, 14 * mm, W * 0.22, W * 0.56 - 30 * mm], extra=[('ALIGN', (2, 1), (2, -1), 'CENTER')]), Spacer(1, 6)])
                story.append(_p('The full list of affected URLs is in the CSV export (Issues CSV) next to the report.', st['smallmuted']))
        ops = crawl.get('link_opportunities') or []
        if ops:
            h2('Internal link opportunities')
            story.append(_p("Pages that talk about another page's topic but never link to it - add a contextual link.", st['sub']))
            rows = [['Link from', 'To', 'Shared topic']] + [[_p(_path_of(o.get('from', '')), st['small']), _p(_path_of(o.get('to', '')), st['small']), _p(o.get('topic', ''), st['smallmuted'])] for o in ops[:12]]
            story.extend([_grid(rows, [W * 0.4, W * 0.4, W * 0.2]), Spacer(1, 6)])

        patterns = crawl.get('content_patterns') or []
        if patterns:
            h2('Winning content patterns')
            story.append(_p('The three page shapes AI engines cite most often, and whether your sampled pages use them.', st['sub']))
            tone = {'present': ('present', GREEN), 'partial': ('partly there', AMBER), 'missing': ('missing', RED)}
            cards = []
            for pat in patterns[:3]:
                label, col = tone.get(pat.get('status'), ('—', MUTED))
                cards.append(_box([_p(pat.get('title', ''), st['h3']),
                                   Paragraph(f"<font color='{col.hexval()}'><b>{label}</b></font> <font color='{MUTED.hexval()}'>· {_esc(pat.get('evidence', ''))}</font>", st['small']),
                                   Spacer(1, 3), _p(pat.get('advice', ''), st['smallmuted'])], W / 3 - 4, pad=7))
            while len(cards) < 3:
                cards.append('')
            pt = Table([cards], colWidths=[W / 3] * 3)
            pt.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
            story.append(pt)

        pages = crawl.get('pages') or []
        if pages:
            h2('Page-level scores')
            story.append(_p('Readiness of each sampled page: does it carry schema, a byline, citations and a date (25 points each).', st['sub']))
            howto('"Ready" is the page\'s citation-readiness score out of 100: 25 points each for structured data, an author byline, at least three outbound citations, and a visible update date. '
                  '"Links" is how many internal links the page carries. "On-page" flags the technical problems found on that page; "clean" means none.')
            has_details = any((p_.get('details') or {}) for p_ in pages)
            rows = [['Page', 'Words', 'Schema', 'Author', 'Citations', 'Updated', 'Ready', 'Links', 'On-page'] if has_details else ['Page', 'Words', 'Schema', 'Author', 'Citations', 'Updated', 'Readiness']]
            for p_ in pages[:20]:
                fetched = p_.get('fetched', True)
                score = _page_readiness(p_)
                colour = GREEN if (score or 0) >= 75 else AMBER if (score or 0) >= 50 else RED
                row = [_p(_path_of(p_.get('url', '')) if fetched else f"{_path_of(p_.get('url', ''))} (could not be read)", st['small']),
                       f"{p_.get('word_count', 0):,}" if fetched else '—',
                       _p(', '.join(p_.get('schema_types') or []) or ('none' if fetched else '—'), st['smallmuted']), _p(p_.get('author') or '—', st['small']),
                       p_.get('external_links', 0) if fetched else '—', p_.get('last_modified') or '—',
                       Paragraph(f"<font color='{colour.hexval()}'><b>{score if score is not None else '—'}</b></font>", st['small'])]
                if has_details:
                    d = p_.get('details') or {}
                    flags = _page_flags(d)
                    row += [str(d.get('internal_links')) if d.get('internal_links') is not None else '—',
                            Paragraph(', '.join(f"<font color='{(RED if bad else AMBER).hexval()}'>{_esc(f_)}</font>" for f_, bad in flags) if flags
                                      else (f"<font color='{GREEN.hexval()}'>clean</font>" if d else '—'), st['small'])]
                rows.append(row)
            widths = ([W * 0.22, W * 0.07, W * 0.15, W * 0.09, W * 0.08, W * 0.08, W * 0.08, W * 0.09, W * 0.14] if has_details
                      else [W * 0.3, W * 0.09, W * 0.2, W * 0.13, W * 0.09, W * 0.1, W * 0.09])
            story.extend([_grid(rows, widths), Spacer(1, 6)])
    story.append(PageBreak())

    # ---------------------------------------------------------------- 04 plan
    part('04', '90-day plan', sentence(intros.get('plan')) or (f"{brand} moves from {plan.get('today')} to {plan.get('projected')} by executing the actions below in order; doing nothing drifts to {plan.get('status_quo')}."
                                                     if plan.get('projected') is not None else ''))
    buckets = [b for b in (plan.get('buckets') or []) if b.get('items')]
    if buckets:
        h2('Visibility plan - Now / Next / Later')
        story.append(_p("Every gap's action, sequenced, with the score projected at each step. Lifts are nominal; the projection applies headroom and confidence.", st['sub']))
        howto('Now = the first month, small tasks that stop the bleeding. Next = months two and three, the biggest answers to win. Later = widening the lead. '
              '"Lift" is the GEO points an action is worth once done; "Effort" is a rough number of working hours; "Owner" is who usually does it.')
        if plan.get('projected') is not None:
            takeaway(f"Doing everything in this plan takes {brand} from {plan.get('today')} to about {plan.get('projected')} within 90 days"
                     + (f"; doing nothing drifts to {plan.get('status_quo')} as the pages the engines cite go stale." if plan.get('status_quo') is not None else '.'))
        rows = [['When', 'Action', 'Why', 'Owner', 'Lift', 'Effort']]
        extra = []
        for b in buckets:
            i0 = len(rows)
            rows.append([_p(f"{b.get('label', '')}  {b.get('from', '')} > {b.get('to', '')}", st['small']), _p(b.get('subtitle', ''), st['smallmuted']), '', '', '', ''])
            extra += [('SPAN', (1, i0), (-1, i0)), ('BACKGROUND', (0, i0), (-1, i0), PRIMARY_TINT)]
            for it in b['items']:
                rows.append(['', _p(it.get('title', ''), st['small']), _p(it.get('why', ''), st['smallmuted']), (it.get('owner') or '').capitalize(),
                             f"+{it.get('projected_geo_lift', 0)}", f"~{it.get('effort_hours', 0)}h"])
        story.extend([_grid(rows, [22 * mm, W * 0.28, W * 0.39, 15 * mm, 10 * mm, 12 * mm], zebra=False, extra=extra), Spacer(1, 6)])

        h2('KPI scorecard - 30-day and 90-day targets')
        b30 = next((b for b in buckets if b.get('key') == 'now'), buckets[0])
        owned = ctrl.get('owned') or 0
        kpi = [['Metric', 'Baseline', '30-day target', '90-day target', 'Tracked via'],
               ['GEO score', f"{plan.get('today', audit.geo_score)}/100", f"{b30.get('to', '')}/100", f"{plan.get('projected', '')}/100", 'audit re-run, same prompts'],
               ['Mention rate', _pct(mention_rate), _pct(min(100, mention_rate + 10)), _pct(min(100, mention_rate + 25)), 'prompt sampling on every engine'],
               ['Owned citation share', _pct(owned), _pct(min(100, owned + 10)), _pct(min(100, owned + 25)), 'citation control on the same prompts'],
               ['Engines preferring you', f"{audit.engines_preferred}/{audit.engines_total}", f"{min(audit.engines_total, audit.engines_preferred + 1)}/{audit.engines_total}",
                f"{audit.engines_total}/{audit.engines_total}", 'engine-level mention rate > 50%']]
        story.extend([_grid(kpi, [W * 0.24, W * 0.14, W * 0.16, W * 0.16, W * 0.30]), Spacer(1, 6)])

    wins = r.get('quick_wins') or []
    if wins:
        h2('Quick wins - ranked by impact')
        rows = [['#', 'Action', 'Expected impact', 'Lift', 'Effort']]
        for i, w_ in enumerate(wins, 1):
            rows.append([str(i), _p(w_.get('title', ''), st['small']), _p(w_.get('why', ''), st['smallmuted']), f"+{w_.get('projected_geo_lift', 0)} pts", f"~{w_.get('effort_hours', 0)}h"])
        story.extend([_grid(rows, [8 * mm, W * 0.32, W * 0.44, 18 * mm, 16 * mm]), Spacer(1, 6)])
    story.append(PageBreak())

    # ---------------------------------------------------------------- 05 appendices
    part('05', 'Appendices', 'How this audit was run, how the score is built, what it cannot tell you, and the terms used throughout.')
    h2('Methodology')
    story.append(_p(
        f"{prompt_count} prompts were generated from {audit.host} and asked {'once' if runs == 1 else str(runs) + ' times'} each on {', '.join(platforms) or 'the configured engines'}"
        f"{(' on ' + _fmt_date(audit.completed_at)) if audit.completed_at else ''}. Prompts span the buyer funnel - TOFU (awareness), MOFU (evaluation), BOFU (decision) - "
        "and were written from the site's own pages so they reflect what its buyers actually ask. "
        + ("One run per engine means low statistical confidence by design - AI answers vary run to run; the product re-asks each prompt several times and reports rates, not single results. "
           if runs == 1 else f"With {runs} runs per engine, an engine counts as cited or mentioned on a prompt when at least half its runs were. ")
        + ("SEO data comes from PromptMaxx's own SERP pipeline; keyword volume from DataForSEO. " if seo else "Google rankings were not measured in this audit. ")
        + (f"On-site signals come from a plain-HTTP sample of {crawl['pages_sampled']} pages (schema, bylines, outbound citations, dates); no rendering, no user data. " if crawl and crawl.get('pages_sampled') else '')
        + "Google AI Overviews are not yet tracked.", st['body']))
    h2('Scoring model')
    story.append(_p("The GEO score runs from 0 to 100 and is a weighted sum of four components measured across every answer read: placement (35%) - the order in which "
                    "the brand is named among the brands in an answer; frequency (25%) - the share of answers that name it; sourcing (25%) - the share that cite its own site; "
                    "framing (15%) - how favourably it is described where it is named. Bands: Absent 0-25, Present 26-50, Preferred 51-75, Default 76-100. "
                    "The Findable / Cited / Chosen measures each have a target; targets are the model's ceilings, not industry averages. "
                    "The same formula scores tracked projects, so an audit score and a project score mean the same thing.", st['body']))
    h2('Limitations')
    story.append(_p(f"This audit is a point-in-time capture on {_fmt_date(audit.completed_at) or 'the audit date'}. {prompt_count} prompts is a directional sample, "
                    "below the 30-100 prompts used for statistically stable rates. AI engines are stochastic: the same prompt re-run tomorrow can surface a different set of brands. "
                    "Brand and rival names are extracted automatically from the answers and may occasionally be mislabelled. Parts of this report are written by a language model "
                    "from the audit's numbers; every claim is traceable to a table in the report, but treat the prose as a starting point for discussion, not the final word.", st['body']))
    h2('Glossary')
    rows = [['Term', 'Definition']] + [[_p(term, st['small']), _p(definition, st['smallmuted'])] for term, definition in GLOSSARY]
    story.extend([_grid(rows, [W * 0.24, W * 0.76]), Spacer(1, 6)])
    story.append(Spacer(1, 8))
    story.append(_p(f"Generated by {brand_label} · {_fmt_date(audit.completed_at)} · report version {r.get('version', 1)}", st['center_muted']))

    # two passes so the contents page gets real page numbers
    doc.multiBuild(story)
    return buf.getvalue()
