"""
Word (.docx) bulk upload support.

The template is written for non-technical marketers, not for our data model:
plain questions, one article per section, tick-boxes instead of dropdowns.

    Create Article #1

    Title
    How to Choose the Right Health Insurance

    Describe your idea
    Explain individual vs family cover. Include tax benefits.

    Target keywords
    health insurance, mediclaim

    Article type  (tick one)
    Articles
    [x] Blog Post
    [ ] How-to Guide
    ...

Ticking a box gives us both the category and the content type, so there is no
"invalid Category/Content Type combination" error to hit. Shared settings live
in a "Your defaults" block at the top and apply to every article, which is
better than the Excel template's row-2-only prefill.

The Excel upload path in views.py is not modified by this module. The BULK_*
lookup maps are passed in by the caller rather than imported, so this module
stays free of a circular import back into views.
"""

import logging
import re
import zipfile
from io import BytesIO

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

logger = logging.getLogger(__name__)

# A .docx is a ZIP archive; refuse to expand an implausible amount of XML.
MAX_UNCOMPRESSED_BYTES = 60 * 1024 * 1024

# Cap on articles accepted from one document.
MAX_BRIEFS_PER_DOCUMENT = 50

# Number of blank article sections shipped in the template by default.
DEFAULT_BRIEF_COUNT = 10

# Word's own checkbox content control lives in the w14 namespace.
W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W14_NS = 'http://schemas.microsoft.com/office/word/2010/wordml'

# Glyphs Word swaps between when a checkbox is clicked.
GLYPH_UNCHECKED = '☐'
GLYPH_CHECKED = '☒'

UNCHECKED = GLYPH_UNCHECKED
CHECKED_MARKERS = ('[x]', '[X]', '☑', '☒', '✓', '✔', '[√]')
UNCHECKED_MARKERS = ('□', '☐', '[ ]', '[  ]', '-', '•')

# "Create Article #1", "Article 2", "Brief 3" all start a new section.
SECTION_DELIMITER = re.compile(
    r'^(?:create\s+)?(?:article|brief)\s*#?\s*\d+\s*:?$', re.IGNORECASE
)

# A line of only underscores/dashes/equals is decoration, not content.
PLACEHOLDER = re.compile(r'^[\s_\-–—.=*]+$')

# Guidance is written inline on the question line, e.g.
# "Target keywords  (separate them with commas)". It is stripped before a line
# is matched against the label table, so it can never be read as an answer.
PARENTHETICAL = re.compile(r'\([^)]*\)')

# Friendly label -> internal key. Older/plainer wordings are accepted too so a
# document written by hand still parses.
ARTICLE_LABELS = {
    'title': 'title',
    'describe your idea': 'idea',
    'your idea': 'idea',
    'content brief': 'idea',
    'brief': 'idea',
    'target keywords': 'keywords',
    'keywords': 'keywords',
    'primary keywords': 'primary_keywords',
    'primary keyword': 'primary_keywords',
    'secondary keywords': 'secondary_keywords',
    'secondary keyword': 'secondary_keywords',
    'anchor text': 'anchor_text',
    'anchor texts': 'anchor_text',
    'article type': 'article_type',
    'content type': 'article_type',
    'type': 'article_type',
    'target country': 'country',
    'country': 'country',
    'tone': 'tone',
    'tone of voice': 'tone',
    'approximate length': 'word_count',
    'length': 'word_count',
    'word count': 'word_count',
    'anything else': 'extra',
    'anything else?': 'extra',
    'additional instructions': 'extra',
    'any links we should read': 'reference_urls',
    'any links we should read?': 'reference_urls',
    'links': 'reference_urls',
    'reference links': 'reference_urls',
    'reference urls': 'reference_urls',
}

# Separators between a link and the note describing it.
REFERENCE_NOTE_SEPARATORS = (' — ', ' – ', ' - ', ' | ')

# Only these may be recognised as a label when written on their own, without a
# colon — they are the exact questions the template prints. The shorter
# aliases above still work, but only in "Alias: value" form.
#
# Without this restriction an answer that happens to be a single common word
# ("Links", "Tone", "Type") would be read as the next question and the user's
# text silently discarded.
ARTICLE_BARE_LABELS = frozenset({
    'title',
    'describe your idea',
    'target keywords',
    'primary keywords',
    'secondary keywords',
    'anchor text',
    'article type',
    'target country',
    'tone',
    'approximate length',
    'any links we should read',
    'anything else',
})

# The last field in a section: everything after it is taken verbatim, so prose
# containing a stray label word is not mistaken for a new field.
TERMINAL_KEY = 'extra'

# Labels understood inside the "Your defaults" block.
DEFAULT_LABELS = {
    'country': 'country',
    'language': 'language',
    'audience': 'audience',
    'tone': 'tone',
    'writing style': 'style',
    'style': 'style',
    'typical length': 'word_count',
    'length': 'word_count',
    'priority': 'priority',
    'key messages': 'key_messages',
    'topics to avoid': 'topics_to_avoid',
}

DEFAULTS_HEADING = re.compile(r'^your defaults\b', re.IGNORECASE)

_GREY = RGBColor(0x6B, 0x72, 0x80)


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _normalise(text):
    return ' '.join(str(text or '').split()).strip()


def _label_key(text, table, bare_allowed=None):
    """
    Match a line against a label table.

    'Title: Foo' -> ('title', 'Foo'); 'Title' -> ('title', '').

    `bare_allowed` limits which labels may appear without a colon. Pass an
    empty set to require "Label: value" throughout.
    """
    stripped = _normalise(text)
    if not stripped:
        return None, None

    head, separator, rest = stripped.partition(':')
    if separator:
        candidate = _normalise(PARENTHETICAL.sub('', head)).rstrip('?').lower()
        if candidate in table:
            return table[candidate], rest.strip()

    bare = _normalise(PARENTHETICAL.sub('', stripped)).rstrip('?').lower()
    if bare in table and (bare_allowed is None or bare in bare_allowed):
        return table[bare], ''
    return None, None


def _types_by_category(type_map):
    grouped = {}
    for category, content_type in type_map.keys():
        grouped.setdefault(category, []).append(content_type)
    return {cat: sorted(types) for cat, types in sorted(grouped.items())}


def _type_index(type_map):
    """Content-type name (lowered) -> (category, content_type, code)."""
    index = {}
    for (category, content_type), code in type_map.items():
        index[content_type.strip().lower()] = (category, content_type, code)
    return index


# ─────────────────────────────────────────────────────────────────────────────
# Template
# ─────────────────────────────────────────────────────────────────────────────

def _grey(paragraph, text, size=9):
    run = paragraph.add_run(text)
    run.font.size = Pt(size)
    run.font.color.rgb = _GREY
    run.italic = True
    return run


def _question(document, text, hint=''):
    """
    A question line, with its guidance inline in parentheses.

    The hint must stay on this line: a separate paragraph beneath it would be
    read as the user's answer.
    """
    paragraph = document.add_paragraph()
    paragraph.add_run(text).bold = True
    if hint:
        _grey(paragraph, f'   ({hint})')
    return paragraph


def _write_line(document, value=''):
    """The line the user types on."""
    return document.add_paragraph(value if value else '_' * 46)


def _add_checkbox(paragraph, checked=False):
    """
    Append a real Word checkbox (w14 content control) to `paragraph`.

    In Word the user clicks it and the glyph flips ☐ → ☒. Editors that do not
    support the control render the glyph as plain text, which the parser still
    reads — and a user can type an "x" instead.
    """
    from lxml import etree

    sdt = etree.SubElement(paragraph._p, f'{{{W_NS}}}sdt')
    properties = etree.SubElement(sdt, f'{{{W_NS}}}sdtPr')

    checkbox = etree.SubElement(properties, f'{{{W14_NS}}}checkbox')
    state = etree.SubElement(checkbox, f'{{{W14_NS}}}checked')
    state.set(f'{{{W14_NS}}}val', '1' if checked else '0')
    for tag, code in (('checkedState', '2612'), ('uncheckedState', '2610')):
        node = etree.SubElement(checkbox, f'{{{W14_NS}}}{tag}')
        node.set(f'{{{W14_NS}}}val', code)
        node.set(f'{{{W14_NS}}}font', 'MS Gothic')

    content = etree.SubElement(sdt, f'{{{W_NS}}}sdtContent')
    run = etree.SubElement(content, f'{{{W_NS}}}r')
    text = etree.SubElement(run, f'{{{W_NS}}}t')
    text.text = GLYPH_CHECKED if checked else GLYPH_UNCHECKED
    return sdt


def _add_defaults_block(document, defaults, country_map):
    document.add_heading('Your defaults', level=1)
    note = document.add_paragraph()
    _grey(note,
          'These apply to every article below. We have filled them in from '
          'your website settings — change anything you like, or leave them.')

    rows = [
        ('Country', defaults.get('country', '')),
        ('Language', defaults.get('language', '')),
        ('Audience', defaults.get('audience', '')),
        ('Tone', defaults.get('tone', '')),
        ('Writing style', defaults.get('style', '')),
        ('Typical length', defaults.get('word_count', '')),
        ('Priority', defaults.get('priority', '')),
        ('Key messages', defaults.get('key_messages', '')),
        ('Topics to avoid', defaults.get('topics_to_avoid', '')),
    ]
    for label, value in rows:
        paragraph = document.add_paragraph()
        paragraph.add_run(f'{label}: ').bold = True
        paragraph.add_run(str(value) if value else '')


def _add_article(document, number, type_map, defaults=None):
    defaults = defaults or {}
    document.add_paragraph('=' * 50)
    document.add_heading(f'Create Article #{number}', level=1)

    intro = document.add_paragraph()
    _grey(intro, 'Only Title and Primary keywords are required. Everything else is optional.')

    _question(document, 'Title', 'a working title is fine')
    _write_line(document)

    _question(document, 'Describe your idea',
              'optional — what should it cover, and who is it for?')
    _write_line(document)

    _question(document, 'Primary keywords', 'the main 1-2 keywords, separated by commas')
    _write_line(document)

    _question(document, 'Secondary keywords', 'optional supporting keywords, separated by commas')
    _write_line(document)

    _question(document, 'Anchor text',
              'optional; phrases to weave in as link text, one per line')
    _write_line(document)

    _question(document, 'Article type',
              'click one box to tick it; delete any groups you never use')
    for category, types in _types_by_category(type_map).items():
        heading = document.add_paragraph()
        heading.add_run(category).bold = True
        for content_type in types:
            option = document.add_paragraph()
            _add_checkbox(option)
            option.add_run(f'  {content_type}')

    # Target country, tone, approximate length, reference links and extra notes
    # are set once in the "Your defaults" block above and apply to every article,
    # so they are no longer repeated per-article. (The parser still reads these
    # labels from older documents that include them, so nothing breaks.)
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(20)


def _build_defaults(domain, country_map):
    """Shared settings, taken from the domain's content guidelines."""
    defaults = {
        'language': 'US English',
        'audience': 'General',
        'word_count': '1500',
        'priority': 'Medium',
    }
    if domain is None:
        defaults['country'] = 'United States'
        return defaults

    domain_country = str(getattr(domain, 'country', '') or '').strip().lower()
    defaults['country'] = 'United States'
    for display in country_map:
        if display.lower() == domain_country:
            defaults['country'] = display
            break

    for attribute, key in (
        ('tone_of_voice', 'tone'),
        ('content_style', 'style'),
        ('key_messages', 'key_messages'),
        ('topics_to_avoid', 'topics_to_avoid'),
    ):
        value = getattr(domain, attribute, '') or ''
        if value:
            defaults[key] = value

    return defaults


def build_docx_template(*, type_map, country_map, count=DEFAULT_BRIEF_COUNT,
                        domain=None):
    """Build the Word bulk-upload template and return it as bytes."""
    count = max(1, min(int(count), MAX_BRIEFS_PER_DOCUMENT))

    document = Document()
    document.add_heading('Plan Your Articles', level=0)

    intro = document.add_paragraph()
    intro.add_run(
        'Fill in one section per article you want written, then upload this '
        'document. Anything you leave blank uses your defaults.'
    )
    document.add_paragraph(
        'You only need a title, a description and some keywords to get going.',
        style='List Bullet',
    )
    document.add_paragraph(
        f'Need more than {count} articles? Copy a whole "Create Article" '
        f'section and paste it at the end. Up to {MAX_BRIEFS_PER_DOCUMENT}.',
        style='List Bullet',
    )
    document.add_paragraph(
        'Leave a section untouched and it is simply ignored.',
        style='List Bullet',
    )
    document.add_paragraph(
        'Keep the question headings — they are how we read your document.',
        style='List Bullet',
    )
    document.add_paragraph(
        'Click a checkbox to tick it. If your editor will not tick, type an '
        '"x" at the start of that line instead.',
        style='List Bullet',
    )

    template_defaults = _build_defaults(domain, country_map)
    _add_defaults_block(document, template_defaults, country_map)

    document.add_page_break()

    for number in range(1, count + 1):
        _add_article(document, number, type_map, template_defaults)

    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────────────────────

def _document_lines(document):
    """
    Every paragraph's text, including paragraphs nested inside content
    controls (w:sdt), which python-docx's `document.paragraphs` skips.
    """
    lines = []
    for node in document.element.body.iter(qn('w:p')):
        text = _normalise(''.join(t.text or '' for t in node.iter(qn('w:t'))))
        if text:
            lines.append(text)
    return lines


def _checkbox_state(line):
    """
    (is_checked, remaining_text) for a tick-box line, else (None, line).

    Handles Word's clicked checkbox (☒/☐), the plain-text forms people type
    when their editor will not tick ([x], ✓, or a leading "x"), and the
    bracket form used by editors that flatten the control.
    """
    stripped = line.strip()

    for marker in CHECKED_MARKERS:
        if stripped.startswith(marker):
            return True, stripped[len(marker):].strip()

    if stripped.startswith('[') and ']' in stripped:
        inside, _, rest = stripped[1:].partition(']')
        return bool(inside.strip()), rest.strip()

    for marker in UNCHECKED_MARKERS:
        if stripped.startswith(marker):
            return False, stripped[len(marker):].strip()

    # "x Blog Post" — only meaningful when the remainder is a real type, which
    # the caller checks.
    if len(stripped) > 2 and stripped[0] in 'xX' and stripped[1] in ' \t':
        return True, stripped[1:].strip()

    return None, stripped


def _split_references(raw):
    """
    Turn a multi-line answer into the pipe-separated pair the pipeline reads.

        https://a.com — what it covers
        https://b.com

    becomes ('https://a.com|https://b.com', 'what it covers|').

    `_enrich_references_with_content` fetches these URLs and feeds the real
    page text to the model, so they must land in reference_urls rather than
    in the free-text instructions.
    """
    urls, notes = [], []
    for line in str(raw or '').splitlines():
        cleaned = line.strip().lstrip('-•*').strip()
        if not cleaned:
            continue
        url, note = cleaned, ''
        for separator in REFERENCE_NOTE_SEPARATORS:
            if separator in cleaned:
                url, note = cleaned.split(separator, 1)
                break
        url = url.strip()
        if not url:
            continue
        urls.append(url)
        notes.append(note.strip())

    if not urls:
        return '', ''
    return '|'.join(urls), ('|'.join(notes) if any(notes) else '')


def _lookup(value, mapping, default):
    """Case-insensitive display-name -> code lookup, falling back to default."""
    if not value:
        return default
    needle = _normalise(value).lower()
    for display, code in mapping.items():
        if display.lower() == needle:
            return code
    return default


def _suggest(value, options):
    """Closest option name, for a 'did you mean' hint."""
    import difflib
    matches = difflib.get_close_matches(
        _normalise(value).lower(), [o.lower() for o in options], n=1, cutoff=0.6
    )
    if not matches:
        return None
    for option in options:
        if option.lower() == matches[0]:
            return option
    return None


def guard_docx_archive(uploaded_file):
    """
    Validate the upload really is a Word ZIP container and is not a zip bomb.

    Returns an error string, or None when the file is acceptable.
    """
    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(2)
        uploaded_file.seek(0)
        if header != b'PK':
            return 'This does not look like a Word document'

        with zipfile.ZipFile(uploaded_file) as archive:
            names = archive.namelist()
            if 'word/document.xml' not in names:
                return 'This does not look like a Word document'
            if sum(e.file_size for e in archive.infolist()) > MAX_UNCOMPRESSED_BYTES:
                return 'This document is too large'
            if any(n.lower().endswith('vbaproject.bin') for n in names):
                return 'Documents with macros are not supported'
    except zipfile.BadZipFile:
        return 'This does not look like a Word document'
    except Exception as exc:
        logger.warning("docx archive guard failed: %s", exc)
        return 'We could not open this Word document'
    finally:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
    return None


def _parse_defaults(lines):
    """Read the 'Your defaults' block; returns {} when absent."""
    defaults = {}
    active = False
    for line in lines:
        if DEFAULTS_HEADING.match(line):
            active = True
            continue
        if not active:
            continue
        if SECTION_DELIMITER.match(line):
            break
        key, value = _label_key(line, DEFAULT_LABELS, frozenset())
        if key and value:
            defaults[key] = value
    return defaults


# How far to look ahead when deciding whether a "Title" inside free text is
# really the start of the next article.
_LOOKAHEAD = 6


def _starts_new_article(lines, index):
    """
    True when the Title at `index` heads another article rather than being
    prose that happens to contain the word.

    A real article has another question (Target keywords, Article type …)
    close behind it; prose almost never does.
    """
    for line in lines[index + 1:index + 1 + _LOOKAHEAD]:
        key, _ = _label_key(line, ARTICLE_LABELS, ARTICLE_BARE_LABELS)
        if key and key != 'title':
            return True
    return False


def _iter_article_blocks(lines, type_index):
    """Yield {key: value} for each 'Create Article #N' section."""
    current = None
    field = None
    in_types = False

    for index, line in enumerate(lines):
        if SECTION_DELIMITER.match(line):
            if current is not None:
                yield current
            current, field, in_types = {}, None, False
            continue

        if current is None:
            continue  # preamble and defaults block

        if PLACEHOLDER.match(line):
            continue

        # Tick-box lines: record the ticked one, ignore the rest.
        checked, remainder = _checkbox_state(line)
        if checked is not None and remainder.lower() in type_index:
            if checked:
                current['article_type'] = remainder
            in_types = True
            continue

        key, inline = _label_key(line, ARTICLE_LABELS, ARTICLE_BARE_LABELS)

        # Inside the final free-text answer everything is taken verbatim, so
        # prose like "Tone: friendly is fine" stays prose. The only exception
        # is a Title that clearly heads the next article.
        if field == TERMINAL_KEY:
            if key == 'title' and _starts_new_article(lines, index):
                yield current
                current, field, in_types = {}, None, False
            else:
                current[field] = (current.get(field, '') + '\n' + line).strip()
                continue

        if key:
            if key == 'title' and current.get('title'):
                yield current  # a deleted heading; start the next article
                current, field, in_types = {}, None, False
            if key == 'article_type':
                # Someone may type the type instead of ticking a box. Keep it
                # so validation can confirm it or suggest the closest match;
                # a ticked box later still wins.
                if inline:
                    current['article_type'] = inline
                field, in_types = None, True
                continue
            field, in_types = key, False
            current.setdefault(field, '')
            if inline:
                current[field] = inline
            continue

        if in_types:
            continue  # a category heading such as "Articles"

        if field:
            current[field] = (current.get(field, '') + '\n' + line).strip()

    if current is not None:
        yield current


def _merge_keyword_fields(*fields):
    """Combine several comma-separated keyword strings into one, in the order
    given (so primary keywords come first and are treated as primary by the
    generator), de-duplicated case-insensitively with original order preserved.
    Empty fields are ignored."""
    seen = set()
    out = []
    for field in fields:
        for raw in (field or '').split(','):
            kw = raw.strip()
            if kw and kw.lower() not in seen:
                seen.add(kw.lower())
                out.append(kw)
    return ', '.join(out)


def parse_docx_briefs(uploaded_file, *, type_map, country_map,
                      language_map=None, audience_map=None):
    """
    Parse a .docx into item dicts shaped exactly like the Excel path's output.

    Returns (items_data, errors). `errors` entries are
    {'row': <article number>, 'errors': [...]}; as on the Excel path a
    non-empty errors list means nothing should be imported.
    """
    archive_error = guard_docx_archive(uploaded_file)
    if archive_error:
        return [], [{'row': 0, 'errors': [archive_error]}]

    try:
        document = Document(uploaded_file)
    except Exception as exc:
        logger.warning("docx parse failed: %s", exc)
        return [], [{'row': 0, 'errors': ['We could not read this Word document']}]

    lines = _document_lines(document)
    defaults = _parse_defaults(lines)
    type_index = _type_index(type_map)

    items_data = []
    errors = []
    filled = 0

    def default_for(key, fallback):
        value = defaults.get(key, '')
        return value.strip() if value else fallback

    # Country / Tone / Approximate length are PRE-FILLED from the user's
    # defaults in every template block, so they are no longer a signal that a
    # block was used. Decide "did the user actually fill this article?" from the
    # content fields only, so untouched blocks (defaults only) are still skipped.
    _CONTENT_KEYS = ('title', 'idea', 'keywords', 'primary_keywords',
                     'secondary_keywords', 'article_type', 'extra', 'reference_urls')
    for number, values in enumerate(_iter_article_blocks(lines, type_index), start=1):
        if not any((values.get(k) or '').strip() for k in _CONTENT_KEYS):
            continue

        filled += 1
        if filled > MAX_BRIEFS_PER_DOCUMENT:
            errors.append({
                'row': number,
                'errors': [
                    f'This document has more than {MAX_BRIEFS_PER_DOCUMENT} '
                    f'articles. Please split it into smaller files.'
                ],
            })
            break

        title = values.get('title', '').strip()
        chosen_type = values.get('article_type', '').strip()
        idea = values.get('idea', '').strip()
        extra = values.get('extra', '').strip()

        # Keywords: merge Primary + Secondary (primary first, so the generator
        # treats it as the primary keyword) and fall back to the legacy
        # "Target keywords" field so documents made from the old template still
        # parse. All three are folded together, de-duplicated.
        primary_kw = values.get('primary_keywords', '').strip()
        secondary_kw = values.get('secondary_keywords', '').strip()
        legacy_kw = values.get('keywords', '').strip()
        keywords = _merge_keyword_fields(primary_kw, secondary_kw, legacy_kw)

        # Anchor text: optional phrases to weave in (usable later as link text).
        # Folded into the article's instructions so no new model field/migration
        # is needed and the existing generation pipeline uses it as-is.
        anchor_text = values.get('anchor_text', '').strip()

        article_errors = []

        if not title:
            article_errors.append('Please add a Title')
        if not keywords:
            article_errors.append('Please add at least one primary keyword')

        if not chosen_type:
            article_errors.append(
                'Please tick one Article type box'
            )
            category = content_type = article_code = ''
        else:
            found = type_index.get(chosen_type.lower())
            if found:
                category, content_type, article_code = found
            else:
                hint = _suggest(chosen_type, [t for t in type_index])
                article_errors.append(
                    f'We did not recognise the article type "{chosen_type}"'
                    + (f' — did you mean "{hint.title()}"?' if hint else '')
                )
                category = content_type = article_code = ''

        raw_length = values.get('word_count', '').strip() or default_for('word_count', '1500')
        try:
            word_count = int(re.sub(r'[^\d]', '', raw_length) or 1500)
        except (ValueError, TypeError):
            word_count = 1500
            article_errors.append(
                f'We could not read the length "{raw_length}" — use a number like 1500'
            )

        if article_errors:
            errors.append({'row': number, 'errors': article_errors})
            continue

        country = values.get('country', '').strip() or default_for('country', '')
        tone = values.get('tone', '').strip() or default_for('tone', 'professional')

        anchor_note = ''
        if anchor_text:
            # Present the anchor phrases (one per line) as a clear instruction so
            # the writer weaves them in naturally as link/emphasis text.
            phrases = ', '.join(
                p.strip() for p in re.split(r'[\r\n]+', anchor_text) if p.strip()
            )
            if phrases:
                anchor_note = (
                    'Weave these anchor-text phrases into the content naturally, '
                    'used as link text where a link fits: ' + phrases
                )
        instructions = '\n\n'.join(
            part for part in (idea, extra, anchor_note) if part
        )
        reference_urls, reference_notes = _split_references(
            values.get('reference_urls', ''))

        items_data.append({
            'row_number': number,
            'content_category': category,
            'content_type': content_type,
            'title': title,
            'keywords': keywords,
            'article_type': article_code,
            'target_country': _lookup(country, country_map, 'united_states'),
            'target_language': _lookup(default_for('language', ''),
                                       language_map or {}, 'us_english'),
            'target_audience': _lookup(default_for('audience', ''),
                                       audience_map or {}, 'general'),
            'word_count': word_count,
            'tone': tone,
            'style': default_for('style', 'informative'),
            'key_messages': default_for('key_messages', ''),
            'topics_to_avoid': default_for('topics_to_avoid', ''),
            'additional_instructions': instructions,
            'reference_urls': reference_urls,
            'reference_descriptions': reference_notes,
            'priority': _lookup(default_for('priority', 'Medium'),
                                {'High': 'high', 'Medium': 'medium', 'Low': 'low'},
                                'medium'),
        })

    return items_data, errors
