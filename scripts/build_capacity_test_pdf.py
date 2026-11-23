import json
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
INPUTS = [
    ROOT / "data/processed/consumer_protection_act_2019.jsonl",
    ROOT / "data/processed/food_safety_act_2006.jsonl",
    ROOT / "data/processed/legal_metrology_act_2009.jsonl",
]
OUTPUT = ROOT / "data/processed/capacity_test_corpus.pdf"

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        leading=26,
        spaceAfter=16,
    )
)
styles.add(
    ParagraphStyle(
        name="ActTitle",
        parent=styles["Heading1"],
        fontSize=16,
        leading=20,
        spaceBefore=12,
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        name="SectionTitle",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        spaceBefore=10,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="LegalBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        spaceAfter=6,
        splitLongWords=True,
    )
)
styles.add(
    ParagraphStyle(
        name="SmallNote", parent=styles["BodyText"], fontSize=8, leading=11, alignment=TA_CENTER
    )
)

story = [
    Spacer(1, 35 * mm),
    Paragraph("ConsumerShield PDF Capacity Test", styles["CoverTitle"]),
    Paragraph("Generated test document — not an original government PDF", styles["Heading2"]),
    Spacer(1, 10 * mm),
    Paragraph(
        "This document was generated from the project's existing processed "
        "legislation JSONL records to measure PDF page extraction and "
        "processing capacity. It is a test artifact, not an independently "
        "downloaded or official source PDF.",
        styles["BodyText"],
    ),
    Spacer(1, 8 * mm),
    Paragraph(
        "Dataset attribution: Open India Law — Central Indian Legislation "
        "Dataset, licensed under CC BY 4.0. Source records identify the "
        "Legislative Department, Ministry of Law and Justice (India Code). "
        "This generated test document retains that attribution.",
        styles["BodyText"],
    ),
    PageBreak(),
]

total_records = 0
total_source_chars = 0

for source in INPUTS:
    if not source.exists():
        raise FileNotFoundError(f"Missing input: {source}")

    records = []
    with source.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    if not records:
        continue

    total_records += len(records)
    title = records[0].get("title") or source.stem
    story.append(Paragraph(escape(title), styles["ActTitle"]))

    for record in records:
        section = record.get("section_number", "")
        section_title = record.get("section_title", "")
        text = record.get("text", "")
        total_source_chars += len(text)

        heading = f"Section {section}: {section_title}".strip(": ")
        if heading:
            story.append(Paragraph(escape(heading), styles["SectionTitle"]))

        # Keep source text readable without interpreting Markdown as XML.
        for paragraph in text.split("\n\n"):
            paragraph = paragraph.strip()
            if paragraph:
                story.append(Paragraph(escape(paragraph), styles["LegalBody"]))

    story.append(Spacer(1, 8 * mm))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(18 * mm, 10 * mm, "ConsumerShield generated capacity-test document")
    canvas.drawRightString(192 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=A4,
    rightMargin=18 * mm,
    leftMargin=18 * mm,
    topMargin=18 * mm,
    bottomMargin=18 * mm,
    title="ConsumerShield PDF Capacity Test",
    author="ConsumerShield project",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)

reader = PdfReader(str(OUTPUT))
page_text = [page.extract_text() or "" for page in reader.pages]
page_chars = [len(text) for text in page_text]
extracted_chars = sum(page_chars)
estimated_tokens = round(extracted_chars / 4)
pages_with_text = sum(bool(text.strip()) for text in page_text)
pdf_bytes = OUTPUT.stat().st_size

print("\n========== PDF CAPACITY TEST ==========")
print(f"Output: {OUTPUT.relative_to(ROOT)}")
print(f"Input legislation records: {total_records:,}")
print(f"Source text characters: {total_source_chars:,}")
print(f"PDF file size: {pdf_bytes:,} bytes")
print(f"Actual PDF pages: {len(reader.pages):,}")
print(f"Pages with extractable text: {pages_with_text:,}")
print(f"Pages without extractable text: {len(reader.pages) - pages_with_text:,}")
print(f"Extracted PDF characters: {extracted_chars:,}")
print(f"Estimated PDF tokens (chars / 4): {estimated_tokens:,}")
print(f"Average extracted characters/page: {extracted_chars / max(len(reader.pages), 1):,.1f}")
print(f"Estimated chunks at 800 tokens, 100 overlap: {max(1, (estimated_tokens + 699) // 700):,}")
print("Document classification: GENERATED TEST PDF, NOT ORIGINAL SOURCE PDF")
print("=======================================\n")
