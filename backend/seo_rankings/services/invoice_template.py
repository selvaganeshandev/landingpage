"""
Tax invoice HTML — the approved format, parameterised.

The stylesheet lives beside this module in invoice_styles.css and is loaded
verbatim, so the layout can be adjusted without touching the markup. Column
proportions there were measured off the customer's existing Tally invoice so
the grid lands in the same places.

The sample document this was matched against is deliberately NOT in the repo:
it carries a third party's GSTIN and bank account number.

Rendered with WeasyPrint, not xhtml2pdf. The layout depends on real CSS —
rowspan in the HSN header, border-collapse, percentage column widths, @page —
and xhtml2pdf's table engine mangles all of it.
"""
import logging
import os
from html import escape

from .billing import amount_in_words

logger = logging.getLogger(__name__)

_CSS_PATH = os.path.join(os.path.dirname(__file__), "invoice_styles.css")


def _css() -> str:
    try:
        with open(_CSS_PATH, encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:  # pragma: no cover — only if the file is deleted
        logger.error("Invoice stylesheet missing at %s: %s", _CSS_PATH, exc)
        return ""


def _money(n, currency: str = "INR") -> str:
    """1,06,200.00 for INR; 106,200.00 for everything else.

    Indian grouping is only correct for rupees — applying it to a USD export
    invoice would read as a bug to the recipient.
    """
    value = float(n or 0)
    neg = value < 0
    whole, frac = f"{abs(value):.2f}".split(".")
    if currency.upper() != "INR":
        whole = f"{int(whole):,}"
    elif len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return ("-" if neg else "") + f"{whole}.{frac}"


def _symbol(currency: str) -> str:
    # "U$" is how Tally renders USD on Indian export invoices, which is what
    # the reference document uses.
    return {"INR": "&#8377;", "USD": "U$"}.get((currency or "").upper(), escape(currency or ""))


def _conv(amount, fx):
    """Apply the invoice's exchange rate, or pass through when billing in INR."""
    return float(amount or 0) * float(fx["rate"]) if fx else float(amount or 0)


def _addr_divs(text: str, cls: str = "addr") -> str:
    return "".join(
        f'<div class="{cls}">{escape(line)}</div>'
        for line in (text or "").splitlines() if line.strip()
    )


def _party_block(tag: str, party: dict) -> str:
    code = f", Code : {party.get('state_code') or ''}" if party.get("state_code") else ""
    gstin = (f'<div class="kv"><b>GSTIN/UIN</b>: {escape(party["gstin"])}</div>'
             if party.get("gstin") else "")
    state = (f'<div class="kv"><b>State Name</b>: {escape(party["state_name"])}{escape(code)}</div>'
             if party.get("state_name") else "")
    return f"""
        <div class="party">
          <div class="tag">{escape(tag)}</div>
          <div class="name">{escape(party.get('name') or '')}</div>
          {_addr_divs(party.get('address'))}
          {gstin}
          {state}
        </div>"""


def _meta_row(l_label, l_value, r_label, r_value):
    return f"""
          <tr>
            <td><div class="lbl">{escape(l_label)}</div><div class="val">{escape(l_value or '') or '&nbsp;'}</div></td>
            <td><div class="lbl">{escape(r_label)}</div><div class="val">{escape(r_value or '') or '&nbsp;'}</div></td>
          </tr>"""


def _breakdown_page(*, regions, seller, buyer, invoice_no, period, subtotal,
                    currency="INR", fx=None):
    """Page 2 — the per-brand detail behind page 1's single line.

    Kept off the tax invoice so that document stays a clean GST record with one
    consolidated charge, while the customer still gets a full itemisation.
    """
    body, n = [], 0
    for region in regions:
        billed = [p for p in region["projects"] if p["price"] > 0]
        if not billed:
            continue
        if len(regions) > 1:
            body.append(
                f'<tr class="grp"><td colspan="6">{escape(region["label"])}'
                f' &mdash; {len(billed)} project(s)</td></tr>')
        for p in billed:
            n += 1
            body.append(f"""
      <tr>
        <td class="n">{n}</td>
        <td class="pj">{escape(p['name'])}<div class="dom">{escape(p.get('url') or '')}</div></td>
        <td class="rg">{escape(p.get('country') or '')}</td>
        <td class="kw">{p['used_keywords']:,}</td>
        <td class="sb">{p['keyword_limit']:,}</td>
        <td class="am">{_money(_conv(p['price'], fx), currency)}</td>
      </tr>""")

    if not body:
        body.append('<tr><td colspan="6" style="text-align:center">No billable projects</td></tr>')

    return f"""
  <div class="sheet breakpage">
    <div class="bhead">
      <div class="btitle">Itemised Bill</div>
      <div class="bmeta">
        {escape(seller.get('name') or '')} &nbsp;&middot;&nbsp;
        Invoice {escape(invoice_no)} &nbsp;&middot;&nbsp; {escape(period)}
      </div>
      <div class="bmeta">Billed to: {escape(buyer.get('name') or '')}</div>
      {f'<div class="bmeta">Amounts in {escape(currency)}</div>' if currency != "INR" else ''}
    </div>

    <table class="brk">
      <thead>
        <tr>
          <th class="n">#</th><th class="pj">Project</th><th class="rg">Region</th>
          <th class="kw">Keywords</th><th class="sb">Slab</th><th class="am">Amount</th>
        </tr>
      </thead>
      <tbody>{''.join(body)}</tbody>
      <tfoot>
        <tr>
          <td colspan="5" style="text-align:right">Total (excl. tax)</td>
          <td class="am">{_money(_conv(subtotal, fx), currency)}</td>
        </tr>
      </tfoot>
    </table>
  </div>"""


def render_invoice_html(*, cfg, seller, buyer, consignee, invoice_no, invoice_date,
                        items, subtotal, tax_label, tax_rate, tax_amount, total,
                        hsn_sac, logo_src, signature_src, regions=None, period="",
                        title_note="", currency="INR", fx=None):
    item_rows = "".join(
        f"""
    <tr>
      <td class="sl">{i}</td>
      <td class="part">
        <div class="desc">{escape(it['particulars'])}</div>
        {f'<div class="sub">{escape(it["sub"])}</div>' if it.get('sub') else ''}
      </td>
      <td class="rate"></td>
      <td class="per"></td>
      <td class="amt"><b>{_money(_conv(it['amount'], fx), currency)}</b></td>
    </tr>"""
        for i, it in enumerate(items, start=1)
    )

    tax_row = f"""
    <tr>
      <td class="sl"></td>
      <td class="part" style="text-align:right;"><b>{escape(tax_label)}</b></td>
      <td class="rate"><i>{tax_rate:g}</i></td>
      <td class="per">%</td>
      <td class="amt"><b>{_money(_conv(tax_amount, fx), currency)}</b></td>
    </tr>""" if tax_amount else ""

    # Reserved whitespace, as the original leaves. Shrinks as items grow so a
    # busy invoice still fits one page.
    pad_rows = "".join(
        '\n    <tr class="pad"><td class="sl"></td><td></td><td></td><td></td><td></td></tr>'
        for _ in range(max(0, 6 - len(items)))
    )

    # file:// so WeasyPrint reads the upload off disk; a bare path is treated as
    # a relative URL and silently resolves to nothing.
    logo_cell = (f'<td class="logo"><img src="file://{logo_src}" style="width:92px"/></td>'
                 if logo_src else "")
    sig_img = f'<img src="file://{signature_src}"/>' if signature_src else ""

    tax_head = escape((tax_label or "").split("@")[0] or "Tax")

    bank_block = f"""
        <div class="bank">
          <div class="row">Company's Bank Details</div>
          <div class="row"><b>A/c Holder's Name</b>: <span>{escape(cfg.get('bank_account_name') or '')}</span></div>
          <div class="row"><b>Bank Name</b>: <span>{escape(cfg.get('bank_name') or '')}</span></div>
          <div class="row"><b>A/c No.</b>: <span>{escape(cfg.get('bank_account_number') or '')}</span></div>
          <div class="row"><b>Branch &amp; IFS Code</b>: <span>{escape(cfg.get('bank_branch_ifsc') or '')}</span></div>
        </div>"""

    sign_block = f"""
        <div class="sigfor">for {escape(seller.get('name') or '')}</div>
        <div class="sigimg">{sig_img}</div>
        <div class="siglbl">Authorised Signatory</div>"""

    words_line = escape(amount_in_words(_conv(total, fx), currency))

    if tax_amount:
        # Domestic GST invoice: HSN/SAC summary and tax spelled out.
        tail = f"""
  <table class="words">
    <tr>
      <td style="width:72%;">
        <div class="lbl">Amount Chargeable&nbsp;&nbsp;(in words&nbsp;)</div>
        <div class="val">{words_line}</div>
      </td>
      <td style="width:28%;" class="eoe">E. &amp; O.E</td>
    </tr>
  </table>

  <table class="hsn">
    <tr>
      <th class="c1" rowspan="2">HSN/SAC</th>
      <th class="c2" rowspan="2">Taxable<br>Value</th>
      <th colspan="2">{tax_head}</th>
      <th class="c5" rowspan="2">Total<br>Tax Amount</th>
    </tr>
    <tr><th class="c3">Rate</th><th class="c4">Amount</th></tr>
    <tr>
      <td class="l">{escape(hsn_sac or '')}</td>
      <td>{_money(_conv(subtotal, fx), currency)}</td>
      <td>{tax_rate:g}%</td>
      <td>{_money(_conv(tax_amount, fx), currency)}</td>
      <td>{_money(_conv(tax_amount, fx), currency)}</td>
    </tr>
    <tr>
      <td class="totlbl">Total</td>
      <td class="b">{_money(_conv(subtotal, fx), currency)}</td>
      <td></td>
      <td class="b">{_money(_conv(tax_amount, fx), currency)}</td>
      <td class="b">{_money(_conv(tax_amount, fx), currency)}</td>
    </tr>
  </table>

  <div class="taxwords">
    Tax Amount (in words) :&nbsp; <b>{escape(amount_in_words(_conv(tax_amount, fx), currency))}</b>
  </div>

  <table class="foot">
    <tr>
      <td class="spacer" style="height:104px;"></td>
      <td class="bankcell">{bank_block}{sign_block}</td>
    </tr>
  </table>"""
    else:
        # Export invoice: no GST is charged, so the HSN/SAC summary and the tax
        # line have nothing to report and are omitted entirely rather than
        # printed as zeros. The bank block moves up beside the amount in words,
        # as on the reference export invoice.
        tail = f"""
  <table class="words">
    <tr>
      <td style="width:50%;">
        <div class="lbl">Amount Chargeable&nbsp;&nbsp;(in words&nbsp;)</div>
      </td>
      <td style="width:50%;" class="eoe">E. &amp; O.E</td>
    </tr>
    <tr>
      <td style="vertical-align:top;"><div class="val">{words_line}</div></td>
      <td style="vertical-align:top;">{bank_block}</td>
    </tr>
  </table>

  <table class="foot">
    <tr>
      <td class="spacer" style="height:104px;"></td>
      <td class="bankcell">{sign_block}</td>
    </tr>
  </table>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Tax Invoice</title>
<style>
{_css()}
</style></head>
<body>
<div class="sheet">

  <div class="doc-title">TAX INVOICE</div>
  {f'<div class="doc-note">({escape(title_note)})</div>' if title_note else ''}

  <table class="box top">
    <tr>
      <td class="left">
        <table>
          <tr>
            <td class="seller">
              <table>
                <tr>
                  {logo_cell}
                  <td>
                    <div class="cname">{escape(seller.get('name') or '')}</div>
                    {_addr_divs(seller.get('address'), 'caddr')}
                    {f"<div class='caddr'>GSTIN/UIN: {escape(seller['gstin'])}</div>" if seller.get('gstin') else ''}
                    {f"<div class='caddr'>State Name :&nbsp;{escape(seller.get('state_name') or '')}, Code : {escape(seller.get('state_code') or '')}</div>" if seller.get('state_name') else ''}
                    {f"<div class='caddr'>E-Mail : {escape(seller['email'])}</div>" if seller.get('email') else ''}
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
        {_party_block('Consignee (Ship to)', consignee)}
        {_party_block('Buyer (Bill to)', buyer)}
      </td>

      <td class="right">
        <table class="meta">
          {_meta_row('Invoice No.', invoice_no, 'Dated', invoice_date)}
          {_meta_row('Delivery Note', cfg.get('delivery_note'), 'Mode/Terms of Payment', cfg.get('payment_terms'))}
          {_meta_row('Reference No. & Date.', cfg.get('reference_no'), 'Other References', cfg.get('other_references'))}
          {_meta_row("Buyer's Order No.", cfg.get('buyers_order_no'), 'Dated', '')}
          {_meta_row('Dispatch Doc No.', cfg.get('dispatch_doc_no'), 'Delivery Note Date', '')}
          {_meta_row('Dispatched through', cfg.get('dispatched_through'), 'Destination', cfg.get('destination'))}
          <tr>
            <td class="terms" colspan="2" style="border-left:none;">
              <div class="lbl">Terms of Delivery</div>
              {_addr_divs(cfg.get('terms_of_delivery'), 'val')}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>

  <table class="items">
    <tr>
      <th class="sl">Sl<br>No.</th>
      <th class="part">Particulars</th>
      <th class="rate">Rate</th>
      <th class="per">per</th>
      <th class="amt">Amount</th>
    </tr>
    {item_rows}
    {tax_row}
    {pad_rows}
    <tr class="total">
      <td class="sl"></td>
      <td class="part" style="text-align:right;">Total</td>
      <td class="rate"></td>
      <td class="per"></td>
      <td class="amt">{_symbol(currency)}&nbsp;{_money(_conv(total, fx), currency)}</td>
    </tr>
  </table>

  {tail}

  {f'<div class="fxnote">Converted at 1 USD = {fx["inverse"]} INR (as on {fx["as_of"]}) &middot; source: {escape(fx["source"])}</div>' if fx else ''}

  <div class="computer">{escape(cfg.get('footer_note') or '')}</div>

</div>
{_breakdown_page(regions=regions or [], seller=seller, buyer=buyer,
                 invoice_no=invoice_no, period=period, subtotal=subtotal,
                 currency=currency, fx=fx) if regions else ''}
</body></html>"""
