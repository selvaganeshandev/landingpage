/**
 * Server-side only: cut the backend's audit PDF down to a preview.
 *
 * The visitor downloads the first PREVIEW_PAGES pages (cover, contents,
 * executive summary, the start of AI search visibility) plus one "locked"
 * page saying the rest arrives by email from the PivotRoots team. Pages past
 * the preview are dropped, not hidden — nothing in the file can be unlocked.
 */
import "server-only";
import { PDFDocument, PDFFont, StandardFonts, rgb } from "pdf-lib";
import { PDF_PREVIEW_PAGES as PREVIEW_PAGES } from "./site";

const INK = rgb(8 / 255, 2 / 255, 2 / 255);
const PEAR = rgb(203 / 255, 219 / 255, 45 / 255);
const WHITE = rgb(1, 1, 1);
const DIM = rgb(0.72, 0.72, 0.7);
const FAINT = rgb(0.24, 0.22, 0.22);

// Padlock, 24x24 units, drawn with drawSvgPath (y grows downwards in SVG space).
const LOCK_BODY = "M5 11 H19 A2 2 0 0 1 21 13 V21 A2 2 0 0 1 19 23 H5 A2 2 0 0 1 3 21 V13 A2 2 0 0 1 5 11 Z";
const LOCK_SHACKLE = "M7 11 V7 A5 5 0 0 1 17 7 V11";

function wrap(text: string, font: PDFFont, size: number, width: number): string[] {
  const lines: string[] = [];
  let line = "";
  for (const word of text.split(/\s+/)) {
    const next = line ? `${line} ${word}` : word;
    if (font.widthOfTextAtSize(next, size) > width && line) { lines.push(line); line = word; }
    else line = next;
  }
  if (line) lines.push(line);
  return lines;
}

export async function previewPdf(full: Uint8Array): Promise<{ bytes: Uint8Array; total: number; kept: number }> {
  const src = await PDFDocument.load(full);
  const total = src.getPageCount();
  if (total <= PREVIEW_PAGES) return { bytes: full, total, kept: total };

  const out = await PDFDocument.create();
  const kept = await out.copyPages(src, Array.from({ length: PREVIEW_PAGES }, (_, i) => i));
  kept.forEach((p) => out.addPage(p));

  const { width: W, height: H } = kept[0].getSize();
  const page = out.addPage([W, H]);
  const bold = await out.embedFont(StandardFonts.HelveticaBold);
  const reg = await out.embedFont(StandardFonts.Helvetica);
  const M = 56;
  const colW = W - M * 2;
  const locked = total - PREVIEW_PAGES;

  page.drawRectangle({ x: 0, y: 0, width: W, height: H, color: INK });
  page.drawRectangle({ x: 0, y: H - 10, width: W, height: 10, color: PEAR });

  // Brand line
  page.drawText("PIVOTROOTS", { x: M, y: H - 70, size: 15, font: bold, color: WHITE });
  page.drawText("A HAVAS COMPANY", { x: M + bold.widthOfTextAtSize("PIVOTROOTS", 15) + 14, y: H - 69, size: 8.5, font: reg, color: DIM });

  // Kicker pill
  let y = H - 170;
  const kicker = `PREVIEW  ·  ${PREVIEW_PAGES} OF ${total} PAGES`;
  const kw = bold.widthOfTextAtSize(kicker, 9) + 24;
  page.drawRectangle({ x: M, y: y - 7, width: kw, height: 22, color: PEAR });
  page.drawText(kicker, { x: M + 12, y, size: 9, font: bold, color: INK });

  // Padlock
  y -= 90;
  page.drawSvgPath(LOCK_SHACKLE, { x: M, y: y + 62, scale: 2.6, borderColor: PEAR, borderWidth: 2.2 });
  page.drawSvgPath(LOCK_BODY, { x: M, y: y + 62, scale: 2.6, color: PEAR });

  // Headline
  y -= 40;
  for (const l of ["THE FULL REPORT", "IS ON ITS WAY."]) {
    page.drawText(l, { x: M, y, size: 38, font: bold, color: WHITE });
    y -= 42;
  }

  // Body
  y -= 14;
  const body =
    `This download is a preview. The PivotRoots team will send the remaining ${locked} page${locked === 1 ? "" : "s"} ` +
    `of your AI visibility audit to the work email you gave us.`;
  for (const l of wrap(body, reg, 13, colW)) { page.drawText(l, { x: M, y, size: 13, font: reg, color: WHITE }); y -= 19; }

  // What's locked
  y -= 26;
  page.drawText("WHAT THE FULL REPORT ADDS", { x: M, y, size: 9, font: bold, color: DIM });
  y -= 8;
  page.drawLine({ start: { x: M, y }, end: { x: W - M, y }, thickness: 0.6, color: FAINT });
  const items = [
    "Engine-by-engine detail: where each AI names you, cites you, or doesn't",
    "Every buyer question, with the rival cited in your place",
    "Website health: the on-site signals the engines rely on",
    "Your 90-day plan: quick wins ranked by lift and effort",
    "Method, scoring and glossary",
  ];
  y -= 26;
  for (const it of items) {
    page.drawRectangle({ x: M, y: y - 1, width: 8, height: 8, color: PEAR });
    const ls = wrap(it, reg, 11.5, colW - 22);
    ls.forEach((l, i) => page.drawText(l, { x: M + 22, y: y - i * 15, size: 11.5, font: reg, color: WHITE }));
    y -= 15 * ls.length + 13;
  }

  // Footer
  page.drawLine({ start: { x: M, y: 92 }, end: { x: W - M, y: 92 }, thickness: 0.6, color: FAINT });
  page.drawText("Didn't get it, or need it sooner?", { x: M, y: 66, size: 10.5, font: bold, color: WHITE });
  page.drawText("hello@pivotroots.com  ·  +91 99202 98092  ·  pivotroots.com", { x: M, y: 50, size: 10, font: reg, color: DIM });

  out.setTitle(`AI Visibility Audit — preview (${PREVIEW_PAGES} of ${total} pages)`);
  out.setAuthor("PivotRoots");
  out.setProducer("PivotRoots");
  out.setCreator("PivotRoots");
  return { bytes: await out.save(), total, kept: PREVIEW_PAGES };
}
