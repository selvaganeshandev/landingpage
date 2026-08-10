"""
SEO content gaps — .xlsx export.

A Summary sheet, then the gap rows, then the two breakdowns that drive the
page's charts. The summary leads because the gap table alone cannot answer the
question that decides whether the rest is trustworthy: how much of the project
was actually analysed. Most projects carry keywords imported without a stored
results page, and those cannot be judged at all — a spreadsheet that listed 95
gaps without saying they came from 95 of 1,279 keywords would read as a
complete picture of the project.

Styling helpers come from the backlinks export rather than being restated, so
every workbook this product emits uses one palette.
"""
from io import BytesIO

import openpyxl
from openpyxl.styles import Alignment

from .backlinks_export import (
    HEADER_FILL,
    HEADER_FONT,
    _title,
    _write_table,
)

GAP_COLUMNS = [
    ('Keyword', lambda r: r['keyword']),
    ('Platform', lambda r: r['platform']),
    ('Our position', lambda r: r['our_rank'] or 'Not ranked'),
    ('Search volume', lambda r: r['search_volume']),
    ('Est. extra clicks/mo', lambda r: r['estimated_clicks']),
    ('Priority', lambda r: r['bucket'].replace('_', ' ').title()),
    ('Action', lambda r: 'Create new' if r['action'] == 'create' else 'Improve existing'),
    ('Intent', lambda r: r['intent_label']),
    ('Recommended format', lambda r: r['recommended_format']),
    ('Winning format', lambda r: r['content_type_label']),
    ('Results with that format', lambda r: next(
        (m['count'] for m in r['content_type_mix'] if m['type'] == r['content_type']), 0)),
    ('Competitors on page 1', lambda r: r['competitors_on_page_one']),
    ('Leading competitor', lambda r: r['leader']['domain']),
    ('Their position', lambda r: r['leader']['rank']),
    ('Their page', lambda r: r['leader']['url']),
    ('Their page title', lambda r: r['leader']['title']),
    ('All page-1 domains', lambda r: ', '.join(r['competing_domains'])),
    ('Social/video results', lambda r: r['platform_results']),
    ('Paid ads present', lambda r: 'yes' if r['has_ads'] else 'no'),
]

BREAKDOWN_COLUMNS = [
    ('Category', lambda r: r['label']),
    ('Gap keywords', lambda r: r['count']),
]

COMPETITOR_COLUMNS = [
    ('Domain', lambda r: r['domain']),
    ('Gap keywords held', lambda r: r['keywords']),
]


def _write_summary(wb, summary, domain_label, platform_label):
    ws = wb.create_sheet(title='Summary')
    ws.column_dimensions['A'].width = 34
    ws.column_dimensions['B'].width = 22
    ws.column_dimensions['C'].width = 76

    _title(ws, f'SEO content gaps — {domain_label}', 3)

    row = 3

    def section(label):
        nonlocal row
        row += 1
        cell = ws.cell(row=row, column=1, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        ws.cell(row=row, column=2).fill = HEADER_FILL
        ws.cell(row=row, column=3).fill = HEADER_FILL
        row += 1

    def line(label, value, note=''):
        nonlocal row
        ws.cell(row=row, column=1, value=label).font = HEADER_FONT
        ws.cell(row=row, column=2, value=value)
        if note:
            ws.cell(row=row, column=3, value=note).alignment = Alignment(wrap_text=True)
        row += 1

    analysed = summary['keywords_analysed']
    total = summary['total_tracked']
    coverage = round(analysed / total * 100) if total else 0

    section('Coverage')
    line('Project', domain_label)
    line('Platform', platform_label)
    line('Keywords tracked', total)
    line('Keywords analysed', analysed,
         f'{coverage}% of the project. Every figure in this workbook describes these '
         f'keywords only.')
    line('No results page stored', summary['keywords_without_serp'],
         'Gaps are read from the full search results captured on each crawl. Keywords '
         'without one cannot be judged and are excluded rather than reported as having no '
         'competitors. They appear once they have been crawled.')

    section('Gaps found')
    line('Content gaps', summary['gaps'],
         'Tracked keywords where a competitor holds a top-10 position and you are absent '
         'or sit at 11 or worse.')
    line('Need a new page', summary['to_create'], 'You do not rank for these at all.')
    line('Need an existing page improved', summary['to_optimise'],
         'You already rank, off page one.')
    line('Est. extra clicks/mo', summary['estimated_clicks'],
         'Search volume x published average click-through rate for a realistic target '
         'position, minus what the current position earns. Industry-average rates, not '
         'this site\'s measured ones — an estimate for ordering work, not a forecast.')

    section('Priority')
    line('Quick wins', summary['quick_wins'],
         'Already ranking between 11 and 30 — a page to improve, not to write.')
    line('Strategic bets', summary['strategic_bets'],
         'Not ranking at all, 1,000+ monthly searches. Worth building for from nothing.')
    line('Backlog', summary['backlog'], 'Everything else.')

    section('What wins these searches')
    for t in summary['by_content_type']:
        line(t['label'], t['count'])

    section('Search intent')
    for t in summary['by_intent']:
        line(t['label'], t['count'])

    section('Who is taking these')
    for c in summary['top_competitors']:
        line(c['domain'], c['keywords'])

    return ws


def build_content_gap_workbook(rows, summary, domain_label, platform_label='All'):
    """Workbook for one project's gaps. Caller owns the HTTP response."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # drop the default empty sheet

    _write_summary(wb, summary, domain_label, platform_label)

    _write_table(
        wb, 'Content Gaps', GAP_COLUMNS, rows,
        subtitle=(
            f'{len(rows)} gaps across {summary["keywords_analysed"]} analysed keywords, '
            f'best opportunity first. See the Summary sheet for how much of the project '
            f'that covers.'
        ),
    )
    _write_table(
        wb, 'By Format', BREAKDOWN_COLUMNS, summary['by_content_type'],
        subtitle='The kind of page dominating page one, counted across the gap keywords.',
    )
    _write_table(
        wb, 'By Intent', BREAKDOWN_COLUMNS, summary['by_intent'],
        subtitle='Which stage of the buyer journey each gap keyword belongs to.',
    )
    _write_table(
        wb, 'Competitors', COMPETITOR_COLUMNS, summary['top_competitors'],
        subtitle=(
            'Domains holding page one across your gap keywords. Counts every page-one '
            'position, so one domain can appear against a keyword more than once.'
        ),
    )

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream
