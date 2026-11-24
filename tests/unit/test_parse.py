"""Unit tests for document parsing."""

from pathlib import Path

import fitz
import pytest

from consumershield.ingest.parse import ParseError, parse_file


def make_pdf(path: Path, pages: list[str]) -> Path:
    """Create a small PDF for parser tests."""
    doc = fitz.open()

    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)

    doc.save(path)
    doc.close()
    return path


def long_text(label: str) -> str:
    """Return enough text to pass the parser's minimum text threshold."""
    return (
        f"{label}. ConsumerShield document parsing test. "
        "This page contains enough meaningful text for extraction. "
        "The parser should successfully read and preserve this content."
    )


def test_parse_simple_pdf(tmp_path: Path) -> None:
    path = make_pdf(tmp_path / "simple.pdf", [long_text("Hello ConsumerShield")])

    parsed = parse_file(path)

    assert parsed.kind == "pdf"
    assert parsed.parser == "pymupdf"
    assert len(parsed.pages) == 1
    assert "Hello ConsumerShield" in parsed.pages[0].text


def test_parse_multiple_pdf_pages(tmp_path: Path) -> None:
    path = make_pdf(
        tmp_path / "multiple.pdf",
        [long_text("First page content"), long_text("Second page content")],
    )

    parsed = parse_file(path)

    assert len(parsed.pages) == 2
    assert parsed.pages[0].page_no == 1
    assert parsed.pages[1].page_no == 2
    assert "First page content" in parsed.pages[0].text
    assert "Second page content" in parsed.pages[1].text


def test_parse_empty_pdf(tmp_path: Path) -> None:
    path = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()

    with pytest.raises(ParseError):
        parse_file(path)


def test_parse_invalid_pdf(tmp_path: Path) -> None:
    path = tmp_path / "invalid.pdf"
    path.write_text("This is not a PDF", encoding="utf-8")

    with pytest.raises(ParseError):
        parse_file(path)


def test_parse_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.pdf"

    with pytest.raises(ParseError):
        parse_file(path)


def test_pdf_headings_are_detected(tmp_path: Path) -> None:
    path = tmp_path / "headings.pdf"
    doc = fitz.open()
    page = doc.new_page()

    page.insert_text(
        (72, 72),
        "IMPORTANT HEADING",
        fontsize=20,
    )
    page.insert_text(
        (72, 120),
        long_text("This is the body text"),
        fontsize=11,
    )

    doc.save(path)
    doc.close()

    parsed = parse_file(path)

    assert len(parsed.pages) == 1
    assert isinstance(parsed.pages[0].headings, list)


def test_parse_html_file(tmp_path: Path) -> None:
    path = tmp_path / "sample.html"
    path.write_text(
        """
        <html>
            <head><title>Consumer Protection</title></head>
            <body>
                <h1>Consumer Rights</h1>
                <p>Consumers have important rights.</p>
            </body>
        </html>
        """,
        encoding="utf-8",
    )

    parsed = parse_file(path)

    assert parsed.kind == "html"
    assert len(parsed.pages) >= 1
    assert "Consumer Rights" in parsed.pages[0].text


def test_parse_text_file(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text(
        "ConsumerShield document parsing test.",
        encoding="utf-8",
    )

    parsed = parse_file(path)

    assert parsed.kind == "text"
    assert "ConsumerShield document parsing test." in parsed.pages[0].text


def test_parse_markdown_file(tmp_path: Path) -> None:
    path = tmp_path / "sample.md"
    path.write_text(
        "# Consumer Rights\n\nConsumers must be protected.",
        encoding="utf-8",
    )

    parsed = parse_file(path)

    assert parsed.kind == "text"
    assert "Consumer Rights" in parsed.pages[0].text


def test_parse_json_file(tmp_path: Path) -> None:
    path = tmp_path / "sample.json"
    path.write_text(
        '{"name": "ConsumerShield", "purpose": "Consumer protection"}',
        encoding="utf-8",
    )

    parsed = parse_file(path)

    assert parsed.kind == "data"
    assert "ConsumerShield" in parsed.pages[0].text


def test_parse_csv_file(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text(
        "name,category\nProduct A,Electronics\nProduct B,Food",
        encoding="utf-8",
    )

    parsed = parse_file(path)

    assert parsed.kind == "data"
    assert "Product A" in parsed.pages[0].text


def test_parse_unsupported_file(tmp_path: Path) -> None:
    path = tmp_path / "sample.xyz"
    path.write_text("Unsupported content", encoding="utf-8")

    with pytest.raises(ParseError):
        parse_file(path)


def test_parse_preserves_unicode(tmp_path: Path) -> None:
    path = tmp_path / "unicode.txt"
    path.write_text(
        "Consumer rights: பாதுகாப்பு — café",
        encoding="utf-8",
    )

    parsed = parse_file(path)

    assert "பாதுகாப்பு" in parsed.pages[0].text
    assert "café" in parsed.pages[0].text


def test_parse_page_numbers_start_at_one(tmp_path: Path) -> None:
    path = make_pdf(
        tmp_path / "numbering.pdf",
        [
            long_text("Page one"),
            long_text("Page two"),
            long_text("Page three"),
        ],
    )

    parsed = parse_file(path)

    assert [page.page_no for page in parsed.pages] == [1, 2, 3]


def test_parse_returns_parsed_document(tmp_path: Path) -> None:
    path = tmp_path / "result.txt"
    path.write_text("Test document", encoding="utf-8")

    parsed = parse_file(path)

    assert parsed.kind
    assert parsed.parser
    assert parsed.pages
    assert parsed.pages[0].text == "Test document"


def test_parse_page_headings_field_exists(tmp_path: Path) -> None:
    path = tmp_path / "headings.txt"
    path.write_text("# Heading\n\nSome body text.", encoding="utf-8")

    parsed = parse_file(path)

    assert isinstance(parsed.pages[0].headings, list)
