"""
Generate Bulk Content Upload Template (.xlsx)
With proper data validation dropdowns and cascading Content Type based on Content Category.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter


# ── Dropdown Options ──────────────────────────────────────────────────────────

CONTENT_CATEGORIES = ["Articles", "Web Pages", "Social Media", "Community"]

CONTENT_TYPES = {
    "Articles": ["Blog Post", "How-to Guide", "Comparison Article", "Listicle", "Technical Article"],
    "Web Pages": ["Landing Page", "Services Page", "Product Page", "Features Page", "Resource/Guide Page"],
    "Social Media": ["Twitter/X Post", "LinkedIn Post", "Facebook Post", "Instagram Caption", "Thread/Carousel"],
    "Community": ["Reddit Post", "Quora Answer", "Forum Post", "Product Hunt Launch", "Newsletter Snippet"],
}

TARGET_COUNTRIES = [
    "United States", "United Kingdom", "Canada", "Australia", "Germany",
    "France", "Spain", "Italy", "Netherlands", "Sweden", "Norway", "Denmark",
    "Finland", "Switzerland", "Austria", "Belgium", "Ireland", "Portugal",
    "Poland", "India", "Singapore", "Japan", "South Korea", "China",
    "Brazil", "Mexico", "Argentina", "South Africa", "UAE", "Saudi Arabia", "Global",
]

TARGET_LANGUAGES = [
    "US English", "UK English", "Australian English", "Canadian English",
    "Indian English", "Irish English", "South African English",
    "New Zealand English", "Singapore English",
]

TARGET_AUDIENCES = ["General", "Beginners", "Professionals", "Experts"]

WORD_COUNTS_SOCIAL = ["50", "150", "300", "500"]
WORD_COUNTS_COMMUNITY = ["150", "400", "800", "1500"]
WORD_COUNTS_ARTICLES_PAGES = ["800", "1500", "2000", "2500", "3500"]

PRIORITIES = ["High", "Medium", "Low"]


# ── Column Config ─────────────────────────────────────────────────────────────

HEADERS = [
    "Content Category",       # A - Dropdown
    "Content Type",           # B - Cascading Dropdown
    "Title",                  # C - Free text
    "Keywords",               # D - Free text
    "Target Country",         # E - Dropdown
    "Target Language",        # F - Dropdown
    "Target Audience",        # G - Dropdown
    "Word Count",             # H - Dropdown (varies by category)
    "Tone of Voice",          # I - Free text
    "Content Style",          # J - Free text
    "Key Messages",           # K - Free text
    "Topics to Avoid",        # L - Free text
    "Additional Instructions",# M - Free text
    "Reference URLs",         # N - Free text (pipe separated)
    "Reference Descriptions", # O - Free text (pipe separated)
    "Priority",               # P - Dropdown
]

COLUMN_WIDTHS = {
    "A": 20, "B": 25, "C": 45, "D": 40, "E": 20, "F": 22, "G": 18,
    "H": 14, "I": 20, "J": 20, "K": 35, "L": 35, "M": 40,
    "N": 45, "O": 45, "P": 12,
}


# ── Sample Data ───────────────────────────────────────────────────────────────

SAMPLE_DATA = [
    ["Articles", "Blog Post", "10 Best SEO Strategies for 2026", "seo strategies, seo tips, search engine optimization", "United States", "US English", "Professionals", "2500", "Professional", "Informative", "Focus on actionable SEO tactics", "Black hat SEO techniques", "Include real-world examples", "https://example.com/seo-guide", "SEO comprehensive guide", "High"],
    ["Articles", "How-to Guide", "How to Set Up Google Search Console", "google search console, gsc setup", "United Kingdom", "UK English", "Beginners", "1500", "Friendly", "Informative", "Make setup simple and beginner-friendly", "Advanced technical configurations", "Add screenshots descriptions", "", "", "Medium"],
    ["Web Pages", "Landing Page", "AI-Powered Content Generation Platform", "ai content generator, ai writing tool", "United States", "US English", "General", "1500", "Persuasive", "Conversion-focused", "Highlight AI accuracy and ROI", "Competitor names", "Include clear CTA sections", "", "", "High"],
    ["Social Media", "LinkedIn Post", "Why AI Content is the Future of Marketing", "ai content, content marketing", "United States", "US English", "Professionals", "300", "Professional", "Thought Leadership", "Position AI as productivity tool", "Fear-mongering about AI", "Include data point", "", "", "High"],
    ["Community", "Reddit Post", "What SEO tools are you using in 2026?", "seo tools, seo tech stack", "United States", "US English", "Professionals", "400", "Casual", "Conversational", "Share genuine experience", "Overtly promotional language", "Write in authentic Reddit tone", "", "", "Medium"],
]


# ── Styles ────────────────────────────────────────────────────────────────────

HEADER_FONT = Font(name="Calibri", bold=True, size=11, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True)

DROPDOWN_FILL = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")  # Light blue
FREETEXT_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

DATA_FONT = Font(name="Calibri", size=10)
DATA_ALIGNMENT = Alignment(vertical="center", wrap_text=True)

THIN_BORDER = Border(
    left=Side(style="thin", color="D1D5DB"),
    right=Side(style="thin", color="D1D5DB"),
    top=Side(style="thin", color="D1D5DB"),
    bottom=Side(style="thin", color="D1D5DB"),
)

LOOKUP_HEADER_FONT = Font(name="Calibri", bold=True, size=10, color="FFFFFF")
LOOKUP_HEADER_FILL = PatternFill(start_color="6B7280", end_color="6B7280", fill_type="solid")
LOOKUP_FONT = Font(name="Calibri", size=9, color="374151")

# Dropdown columns (0-indexed): A=0, B=1, E=4, F=5, G=6, H=7, P=15
DROPDOWN_COLUMNS = {0, 1, 4, 5, 6, 7, 15}

MAX_DATA_ROWS = 500  # Template supports up to 500 rows


def create_template():
    wb = openpyxl.Workbook()

    # ── Sheet 1: Upload Template ──────────────────────────────────────────
    ws = wb.active
    ws.title = "Bulk Upload"
    ws.sheet_properties.tabColor = "2563EB"

    # Write headers
    for col_idx, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER

    # Set column widths
    for col_letter, width in COLUMN_WIDTHS.items():
        ws.column_dimensions[col_letter].width = width

    # Header row height
    ws.row_dimensions[1].height = 35

    # Write sample data
    for row_idx, row_data in enumerate(SAMPLE_DATA, start=2):
        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = DATA_FONT
            cell.alignment = DATA_ALIGNMENT
            cell.border = THIN_BORDER
            if (col_idx - 1) in DROPDOWN_COLUMNS:
                cell.fill = DROPDOWN_FILL
            else:
                cell.fill = FREETEXT_FILL

    # Pre-format empty rows for data entry (rows 7 to MAX_DATA_ROWS)
    for row_idx in range(len(SAMPLE_DATA) + 2, MAX_DATA_ROWS + 2):
        for col_idx in range(1, len(HEADERS) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = DATA_FONT
            cell.alignment = DATA_ALIGNMENT
            cell.border = THIN_BORDER
            if (col_idx - 1) in DROPDOWN_COLUMNS:
                cell.fill = DROPDOWN_FILL

    # ── Sheet 2: Lookup Data (hidden) ─────────────────────────────────────
    ws_lookup = wb.create_sheet("_Lookup")
    ws_lookup.sheet_state = "hidden"

    # Column A: Content Categories
    ws_lookup.cell(row=1, column=1, value="Content Category").font = LOOKUP_HEADER_FONT
    ws_lookup.cell(row=1, column=1).fill = LOOKUP_HEADER_FILL
    for i, cat in enumerate(CONTENT_CATEGORIES, start=2):
        ws_lookup.cell(row=i, column=1, value=cat).font = LOOKUP_FONT

    # Column B-E: Content Types per category (used for INDIRECT)
    col_offset = 2
    for cat_idx, (category, types) in enumerate(CONTENT_TYPES.items()):
        col = col_offset + cat_idx
        ws_lookup.cell(row=1, column=col, value=category).font = LOOKUP_HEADER_FONT
        ws_lookup.cell(row=1, column=col).fill = LOOKUP_HEADER_FILL
        for i, ctype in enumerate(types, start=2):
            ws_lookup.cell(row=i, column=col, value=ctype).font = LOOKUP_FONT

    # Column G: Target Countries
    ws_lookup.cell(row=1, column=7, value="Target Country").font = LOOKUP_HEADER_FONT
    ws_lookup.cell(row=1, column=7).fill = LOOKUP_HEADER_FILL
    for i, country in enumerate(TARGET_COUNTRIES, start=2):
        ws_lookup.cell(row=i, column=7, value=country).font = LOOKUP_FONT

    # Column H: Target Languages
    ws_lookup.cell(row=1, column=8, value="Target Language").font = LOOKUP_HEADER_FONT
    ws_lookup.cell(row=1, column=8).fill = LOOKUP_HEADER_FILL
    for i, lang in enumerate(TARGET_LANGUAGES, start=2):
        ws_lookup.cell(row=i, column=8, value=lang).font = LOOKUP_FONT

    # Column I: Target Audience
    ws_lookup.cell(row=1, column=9, value="Target Audience").font = LOOKUP_HEADER_FONT
    ws_lookup.cell(row=1, column=9).fill = LOOKUP_HEADER_FILL
    for i, aud in enumerate(TARGET_AUDIENCES, start=2):
        ws_lookup.cell(row=i, column=9, value=aud).font = LOOKUP_FONT

    # Column J: Word Counts (Social Media)
    ws_lookup.cell(row=1, column=10, value="WC Social Media").font = LOOKUP_HEADER_FONT
    ws_lookup.cell(row=1, column=10).fill = LOOKUP_HEADER_FILL
    for i, wc in enumerate(WORD_COUNTS_SOCIAL, start=2):
        ws_lookup.cell(row=i, column=10, value=wc).font = LOOKUP_FONT

    # Column K: Word Counts (Community)
    ws_lookup.cell(row=1, column=11, value="WC Community").font = LOOKUP_HEADER_FONT
    ws_lookup.cell(row=1, column=11).fill = LOOKUP_HEADER_FILL
    for i, wc in enumerate(WORD_COUNTS_COMMUNITY, start=2):
        ws_lookup.cell(row=i, column=11, value=wc).font = LOOKUP_FONT

    # Column L: Word Counts (Articles / Web Pages)
    ws_lookup.cell(row=1, column=12, value="WC Articles Pages").font = LOOKUP_HEADER_FONT
    ws_lookup.cell(row=1, column=12).fill = LOOKUP_HEADER_FILL
    for i, wc in enumerate(WORD_COUNTS_ARTICLES_PAGES, start=2):
        ws_lookup.cell(row=i, column=12, value=wc).font = LOOKUP_FONT

    # Column M: Priority
    ws_lookup.cell(row=1, column=13, value="Priority").font = LOOKUP_HEADER_FONT
    ws_lookup.cell(row=1, column=13).fill = LOOKUP_HEADER_FILL
    for i, p in enumerate(PRIORITIES, start=2):
        ws_lookup.cell(row=i, column=13, value=p).font = LOOKUP_FONT

    # ── Define Named Ranges ───────────────────────────────────────────────
    from openpyxl.workbook.defined_name import DefinedName

    # Content Categories list
    wb.defined_names.add(DefinedName(
        name="ContentCategories",
        attr_text=f"'_Lookup'!$A$2:$A${1 + len(CONTENT_CATEGORIES)}"
    ))

    # Named ranges for each category's content types (replace spaces with underscores for Excel)
    category_named_ranges = {
        "Articles": "Articles",
        "Web Pages": "Web_Pages",
        "Social Media": "Social_Media",
        "Community": "Community",
    }
    for cat_idx, (category, name) in enumerate(category_named_ranges.items()):
        col_letter = get_column_letter(2 + cat_idx)
        types = CONTENT_TYPES[category]
        wb.defined_names.add(DefinedName(
            name=name,
            attr_text=f"'_Lookup'!${col_letter}$2:${col_letter}${1 + len(types)}"
        ))

    # Other named ranges
    wb.defined_names.add(DefinedName(
        name="TargetCountries",
        attr_text=f"'_Lookup'!$G$2:$G${1 + len(TARGET_COUNTRIES)}"
    ))
    wb.defined_names.add(DefinedName(
        name="TargetLanguages",
        attr_text=f"'_Lookup'!$H$2:$H${1 + len(TARGET_LANGUAGES)}"
    ))
    wb.defined_names.add(DefinedName(
        name="TargetAudiences",
        attr_text=f"'_Lookup'!$I$2:$I${1 + len(TARGET_AUDIENCES)}"
    ))
    wb.defined_names.add(DefinedName(
        name="Priorities",
        attr_text=f"'_Lookup'!$M$2:$M${1 + len(PRIORITIES)}"
    ))

    # ── Data Validations on "Bulk Upload" sheet ───────────────────────────
    data_range = f"2:{MAX_DATA_ROWS + 1}"

    # A: Content Category — strict dropdown
    dv_category = DataValidation(
        type="list",
        formula1="ContentCategories",
        allow_blank=False,
        showErrorMessage=True,
        errorTitle="Invalid Content Category",
        error="Please select from: Articles, Web Pages, Social Media, Community",
        showInputMessage=True,
        promptTitle="Content Category",
        prompt="Select a content category from the dropdown",
    )
    dv_category.add(f"A2:A{MAX_DATA_ROWS + 1}")
    ws.add_data_validation(dv_category)

    # B: Content Type — cascading dropdown using INDIRECT
    # SUBSTITUTE replaces spaces with underscores to match named range names
    dv_type = DataValidation(
        type="list",
        formula1='=INDIRECT(SUBSTITUTE(A2," ","_"))',
        allow_blank=False,
        showErrorMessage=True,
        errorTitle="Invalid Content Type",
        error="Please first select a Content Category, then choose a valid Content Type from the dropdown",
        showInputMessage=True,
        promptTitle="Content Type",
        prompt="First select Content Category (Column A), then pick a Content Type here",
    )
    dv_type.add(f"B2:B{MAX_DATA_ROWS + 1}")
    ws.add_data_validation(dv_type)

    # E: Target Country
    dv_country = DataValidation(
        type="list",
        formula1="TargetCountries",
        allow_blank=False,
        showErrorMessage=True,
        errorTitle="Invalid Country",
        error="Please select a valid target country from the dropdown",
        showInputMessage=True,
        promptTitle="Target Country",
        prompt="Select the target country for this content",
    )
    dv_country.add(f"E2:E{MAX_DATA_ROWS + 1}")
    ws.add_data_validation(dv_country)

    # F: Target Language
    dv_language = DataValidation(
        type="list",
        formula1="TargetLanguages",
        allow_blank=False,
        showErrorMessage=True,
        errorTitle="Invalid Language",
        error="Please select a valid target language from the dropdown",
        showInputMessage=True,
        promptTitle="Target Language",
        prompt="Select the target language variant",
    )
    dv_language.add(f"F2:F{MAX_DATA_ROWS + 1}")
    ws.add_data_validation(dv_language)

    # G: Target Audience
    dv_audience = DataValidation(
        type="list",
        formula1="TargetAudiences",
        allow_blank=False,
        showErrorMessage=True,
        errorTitle="Invalid Audience",
        error="Please select from: General, Beginners, Professionals, Experts",
        showInputMessage=True,
        promptTitle="Target Audience",
        prompt="Select the target audience level",
    )
    dv_audience.add(f"G2:G{MAX_DATA_ROWS + 1}")
    ws.add_data_validation(dv_audience)

    # H: Word Count — combined all valid word counts
    all_word_counts = sorted(set(
        WORD_COUNTS_SOCIAL + WORD_COUNTS_COMMUNITY + WORD_COUNTS_ARTICLES_PAGES
    ), key=int)
    wc_list = ",".join(all_word_counts)
    dv_wordcount = DataValidation(
        type="list",
        formula1=f'"{wc_list}"',
        allow_blank=False,
        showErrorMessage=True,
        errorTitle="Invalid Word Count",
        error=f"Please select a valid word count: {wc_list}",
        showInputMessage=True,
        promptTitle="Word Count",
        prompt="Social Media: 50-500 | Community: 150-1500 | Articles/Pages: 800-3500",
    )
    dv_wordcount.add(f"H2:H{MAX_DATA_ROWS + 1}")
    ws.add_data_validation(dv_wordcount)

    # P: Priority
    dv_priority = DataValidation(
        type="list",
        formula1="Priorities",
        allow_blank=False,
        showErrorMessage=True,
        errorTitle="Invalid Priority",
        error="Please select from: High, Medium, Low",
        showInputMessage=True,
        promptTitle="Priority",
        prompt="Select the content priority level",
    )
    dv_priority.add(f"P2:P{MAX_DATA_ROWS + 1}")
    ws.add_data_validation(dv_priority)

    # ── Sheet 3: Instructions ─────────────────────────────────────────────
    ws_help = wb.create_sheet("Instructions")
    ws_help.sheet_properties.tabColor = "10B981"
    ws_help.column_dimensions["A"].width = 5
    ws_help.column_dimensions["B"].width = 25
    ws_help.column_dimensions["C"].width = 80

    title_font = Font(name="Calibri", bold=True, size=14, color="1E40AF")
    section_font = Font(name="Calibri", bold=True, size=12, color="1E40AF")
    label_font = Font(name="Calibri", bold=True, size=10)
    desc_font = Font(name="Calibri", size=10)
    note_font = Font(name="Calibri", size=10, color="DC2626", bold=True)

    row = 1
    ws_help.cell(row=row, column=2, value="Bulk Content Upload — Instructions").font = title_font
    row += 2

    ws_help.cell(row=row, column=2, value="COLUMN GUIDE").font = section_font
    row += 1

    instructions = [
        ("Content Category *", "Dropdown: Articles | Web Pages | Social Media | Community"),
        ("Content Type *", "Cascading Dropdown: Options change based on Content Category selected"),
        ("Title *", "Free text: Enter the title for your content"),
        ("Keywords *", "Free text: Comma-separated keywords (e.g., seo tips, content marketing)"),
        ("Target Country *", "Dropdown: Select from 31 countries or Global"),
        ("Target Language *", "Dropdown: Select English variant (US, UK, Australian, etc.)"),
        ("Target Audience *", "Dropdown: General | Beginners | Professionals | Experts"),
        ("Word Count *", "Dropdown: Social Media(50-500) | Community(150-1500) | Articles/Pages(800-3500)"),
        ("Tone of Voice", "Free text: e.g., Professional, Friendly, Casual, Persuasive, Enthusiastic"),
        ("Content Style", "Free text: e.g., Informative, Analytical, Technical, Storytelling, Engaging"),
        ("Key Messages", "Free text: Key messages or brand values to incorporate in the content"),
        ("Topics to Avoid", "Free text: Topics or themes the AI should not include"),
        ("Additional Instructions", "Free text: Any special instructions for the AI content generator"),
        ("Reference URLs", "Free text: Use pipe | to separate multiple URLs"),
        ("Reference Descriptions", "Free text: Use pipe | to separate descriptions (match order of URLs)"),
        ("Priority *", "Dropdown: High | Medium | Low"),
    ]

    for label, desc in instructions:
        ws_help.cell(row=row, column=2, value=label).font = label_font
        ws_help.cell(row=row, column=3, value=desc).font = desc_font
        row += 1

    row += 1
    ws_help.cell(row=row, column=2, value="* = Required field").font = note_font
    row += 2

    ws_help.cell(row=row, column=2, value="CONTENT TYPE OPTIONS").font = section_font
    row += 1

    for category, types in CONTENT_TYPES.items():
        ws_help.cell(row=row, column=2, value=category).font = label_font
        ws_help.cell(row=row, column=3, value=" | ".join(types)).font = desc_font
        row += 1

    row += 1
    ws_help.cell(row=row, column=2, value="STATUS FLOW").font = section_font
    row += 1
    ws_help.cell(row=row, column=2, value="After Upload:").font = label_font
    ws_help.cell(row=row, column=3, value="Processed → Generated (auto) → In Review (manual) → Reviewed (manual) → Approved (manual)").font = desc_font
    row += 2

    ws_help.cell(row=row, column=2, value="NOTES").font = section_font
    row += 1
    notes = [
        "1. Select Content Category FIRST, then Content Type dropdown will show relevant options.",
        "2. If Content Type dropdown shows no options, clear the cell and reselect Content Category.",
        "3. Multiple Reference URLs should be separated by pipe character |",
        "4. Keywords should be comma-separated within the Keywords column.",
        "5. This template supports up to 500 content items per upload.",
        "6. Blue-shaded columns are dropdown fields. White columns are free text.",
    ]
    for note in notes:
        ws_help.cell(row=row, column=2, value=note).font = desc_font
        ws_help.merge_cells(start_row=row, start_column=2, end_row=row, end_column=3)
        row += 1

    # ── Freeze panes & filters ────────────────────────────────────────────
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:P{MAX_DATA_ROWS + 1}"

    # ── Save ──────────────────────────────────────────────────────────────
    output_path = "bulk_content_upload_template.xlsx"
    wb.save(output_path)
    print(f"Template saved: {output_path}")
    print(f"  - 'Bulk Upload' sheet: {len(HEADERS)} columns, {len(SAMPLE_DATA)} sample rows, {MAX_DATA_ROWS} max rows")
    print(f"  - '_Lookup' sheet: Hidden (contains dropdown source data)")
    print(f"  - 'Instructions' sheet: Column guide & notes")
    print(f"  - Data validations: Content Category, Content Type (cascading), Country, Language, Audience, Word Count, Priority")


if __name__ == "__main__":
    create_template()
