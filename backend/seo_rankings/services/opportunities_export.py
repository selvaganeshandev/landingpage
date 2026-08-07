"""
Opportunities — .xlsx export.

One sheet per classification, plus a Notes sheet recording how the estimated
figures were derived. Anything modelled rather than measured is stated there,
so a spreadsheet that outlives this conversation still explains itself.
"""
from io import BytesIO

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .opportunities_service import (
    CTR_BY_POSITION,
    TARGET_FOR_PAGE_ONE,
    TARGET_FOR_PAGE_TWO,
    TRAJECTORY_DAYS,
    build_opportunities,
)

# Matches the palette used by the existing report export in views.py.
HEADER_FILL = PatternFill(start_color="FFD966", fill_type="solid")
TITLE_FILL = PatternFill(start_color="00B050", fill_type="solid")
HEADER_FONT = Font(bold=True)
TITLE_FONT = Font(bold=True, color="FFFFFF", size=12)

SHEETS = [
    ('striking_distance', 'Striking Distance'),
    ('page_two', 'Page Two'),
    ('slipping', 'Slipping'),
]

COLUMNS = [
    ('Opportunity Score', lambda r: r['opportunity']['score']),
    ('Est. Extra Clicks/mo', lambda r: r['opportunity']['estimated_clicks']),
    ('Winnability', lambda r: r['opportunity']['winnability']),
    ('Position', lambda r: r['rank_now']),
    ('Target Position', lambda r: r['opportunity']['target_position']),
    ('Best Ever', lambda r: r['top_rank'] or ''),
    ('Ranking Page', lambda r: r['target_url']),
    ('Keyword', lambda r: r['keyword']),
    ('Search Volume', lambda r: r['search_volume']),
    ('Trajectory', lambda r: r['trajectory']['state'].replace('_', ' ').title()),
    ('Places Moved (90d)', lambda r: r['trajectory']['delta']),
    ('Volatility', lambda r: r['trajectory']['volatility']),
    ('Days Tracked', lambda r: r['trajectory']['points']),
    ('Ad Competition', lambda r: (r['difficulty']['level'] or '').title()),
    ('Ad Competition Index', lambda r: r['difficulty']['index'] if r['difficulty']['index'] is not None else ''),
    ('CTR Now %', lambda r: r['opportunity']['ctr_now']),
    ('CTR At Target %', lambda r: r['opportunity']['ctr_target']),
    ('Why This Ranks Here', lambda r: '; '.join(r['opportunity']['reasons'])),
    ('30d Change', lambda r: f"{r['month_mark']} {r['month_val']}".strip()),
    ('Tags', lambda r: ', '.join(r['tags'])),
]


def _write_sheet(wb, title, bucket):
    ws = wb.create_sheet(title=title)

    ws.cell(row=1, column=1, value=f"{title} — {bucket['label']}")
    ws.cell(row=1, column=1).font = TITLE_FONT
    ws.cell(row=1, column=1).fill = TITLE_FILL
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(COLUMNS))

    ws.cell(row=2, column=1, value=f"{bucket['total']} keywords")

    for col, (heading, _) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=3, column=col, value=heading)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical='center', wrap_text=True)

    for i, row in enumerate(bucket['rows'], start=4):
        for col, (_, getter) in enumerate(COLUMNS, start=1):
            ws.cell(row=i, column=col, value=getter(row))

    # Width from the widest cell in each column, clamped so the long "why"
    # column cannot push everything else off screen.
    for col, (heading, getter) in enumerate(COLUMNS, start=1):
        longest = len(heading)
        for row in bucket['rows']:
            longest = max(longest, len(str(getter(row))))
        ws.column_dimensions[get_column_letter(col)].width = min(max(longest + 2, 10), 50)

    ws.freeze_panes = 'A4'
    return ws


def _write_notes(wb, data, domain_label):
    ws = wb.create_sheet(title='Notes')
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 95

    def line(row, key, value):
        ws.cell(row=row, column=1, value=key).font = HEADER_FONT
        ws.cell(row=row, column=2, value=value).alignment = Alignment(wrap_text=True)

    ws.cell(row=1, column=1, value='How to read this export').font = TITLE_FONT
    ws.cell(row=1, column=1).fill = TITLE_FILL
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=2)

    rows = [
        ('Domain', domain_label),
        ('Keywords tracked', data['summary']['tracked']),
        ('Currently ranking', data['summary']['ranking']),
        ('In top 3', data['summary']['top_three']),
        ('Not ranked', data['summary']['not_ranked']),
        ('', ''),
        ('Opportunity Score',
         'Estimated extra monthly clicks multiplied by winnability. Use it to order work, '
         'not as a forecast.'),
        ('Est. Extra Clicks/mo',
         'Search volume x (click-through rate at the target position minus the rate at the '
         'current position).'),
        ('IMPORTANT — CTR is modelled',
         'The click-through rates behind every estimate are PUBLISHED INDUSTRY AVERAGES by '
         'position, not measured for this site. No Search Console data is stored per keyword, '
         'so there is nothing to calibrate against. The figures are reliable for comparing '
         'keywords with each other and unreliable as absolute traffic predictions.'),
        ('Target position',
         f'#{TARGET_FOR_PAGE_ONE} for keywords already on page one; '
         f'#{TARGET_FOR_PAGE_TWO} for keywords on page two.'),
        ('Winnability',
         'A multiplier from trajectory, advertiser competition, and whether the page has held '
         'the target position before. Above 1.0 means easier than average, below means harder. '
         'The "Why This Ranks Here" column lists the factors that applied.'),
        ('Trajectory',
         f'Direction over the last {TRAJECTORY_DAYS} days, comparing the average of the first '
         'and last 7 daily positions. A move of 2+ places reads as Climbing or Slipping; a '
         'standard deviation of 5+ reads as Volatile. Under 10 recorded days reads as New.'),
        ('Ad Competition',
         'Google Keyword Planner competition (Low / Medium / High, plus a 0-100 index). This '
         'measures how contested the term is among ADVERTISERS. It is NOT organic ranking '
         'difficulty — a Low term can still be hard to rank for.'),
        ('Slipping sheet ordering',
         'Ordered by size of loss weighted by volume, not by opportunity score, because the '
         'question there is what was lost rather than what could be won.'),
        ('CTR table used',
         ', '.join(f'#{p}={v * 100:.1f}%' for p, v in sorted(CTR_BY_POSITION.items())[:10])),
    ]
    for i, (key, value) in enumerate(rows, start=3):
        line(i, key, value)

    return ws


def build_opportunities_workbook(domain_id, domain_label, platform='desktop'):
    """Return (BytesIO, suggested_filename_stem) for the export."""
    data = build_opportunities(domain_id, platform=platform)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    for key, title in SHEETS:
        _write_sheet(wb, title, data['buckets'][key])
    _write_notes(wb, data, domain_label)

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream, data
