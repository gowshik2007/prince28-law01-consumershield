"""Compare PDF and HTML parsers on available source files."""

import argparse
import time
from html.parser import HTMLParser
from pathlib import Path

import trafilatura

from consumershield.ingest.parse import (
    parse_pdf_pymupdf,
    parse_pdf_pypdf,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NOTES = ROOT / "NOTES.md"
SUPPORTED = {".pdf", ".html", ".htm"}


class PlainHTMLExtractor(HTMLParser):
    """Extract readable text from HTML without a third-party parser."""

    BLOCK_TAGS = {
        "address",
        "article",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "p",
        "section",
        "tr",
    }

    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0
        self.tables = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip_depth += 1
        if tag == "table":
            self.tables += 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)

    def result(self):
        return " ".join(" ".join(self.parts).split())


def measure_document(parser_func, path):
    """Measure a PDF parser's output and execution time."""
    started = time.perf_counter()

    try:
        doc = parser_func(path)
        return {
            "status": "OK",
            "parser": doc.parser,
            "pages": len(doc.pages),
            "chars": sum(len(page.text) for page in doc.pages),
            "tables": sum(page.tables for page in doc.pages),
            "seconds": time.perf_counter() - started,
            "error": "",
        }
    except Exception as exc:
        return {
            "status": "FAILED",
            "parser": parser_func.__name__,
            "pages": 0,
            "chars": 0,
            "tables": 0,
            "seconds": time.perf_counter() - started,
            "error": str(exc).replace("|", "/")[:120],
        }


def measure_html(parser_name, parser_func, source):
    """Measure an HTML parser's extracted text."""
    started = time.perf_counter()

    try:
        text = parser_func(source)
        return {
            "status": "OK",
            "parser": parser_name,
            "pages": 1,
            "chars": len(text),
            "tables": source.lower().count("<table"),
            "seconds": time.perf_counter() - started,
            "error": "",
        }
    except Exception as exc:
        return {
            "status": "FAILED",
            "parser": parser_name,
            "pages": 0,
            "chars": 0,
            "tables": 0,
            "seconds": time.perf_counter() - started,
            "error": str(exc).replace("|", "/")[:120],
        }


def plain_html(source):
    """Extract text by stripping HTML tags."""
    extractor = PlainHTMLExtractor()
    extractor.feed(source)
    return extractor.result()


def trafilatura_html(source):
    """Extract main text using Trafilatura."""
    return trafilatura.extract(source) or ""


def compare(path):
    """Compare the appropriate parser pair for one file."""
    path = path.resolve()

    if path.suffix.lower() == ".pdf":
        first = measure_document(parse_pdf_pymupdf, path)
        second = measure_document(parse_pdf_pypdf, path)
        parser_a = "PyMuPDF"
        parser_b = "pypdf"

    elif path.suffix.lower() in {".html", ".htm"}:
        source = path.read_text(encoding="utf-8", errors="replace")

        first = measure_html(
            "Trafilatura",
            trafilatura_html,
            source,
        )
        second = measure_html(
            "Plain tag-stripping",
            plain_html,
            source,
        )

        parser_a = "Trafilatura"
        parser_b = "Plain tag-stripping"

    else:
        raise ValueError(f"Unsupported comparison format: {path.suffix}")

    if first["status"] != "OK" or second["status"] != "OK":
        result = "One or both parsers failed; inspect errors"
    elif first["chars"] > second["chars"]:
        result = f"{parser_a} extracted more characters; inspect quality"
    elif second["chars"] > first["chars"]:
        result = f"{parser_b} extracted more characters; inspect quality"
    else:
        result = "Similar character count; inspect structure"

    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "format": path.suffix.lower(),
        "a": parser_a,
        "b": parser_b,
        "first": first,
        "second": second,
        "result": result,
    }


def count_files(suffixes):
    """Count matching files in the project data directory."""
    return sum(1 for path in DATA.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def write_notes(rows, available_pdf, available_html):
    """Write comparison results and observations to NOTES.md."""
    lines = [
        "## Day 7 - Part 5: Parser comparison",
        "",
        (
            "| File | Format | Parser A | Parser B | A pages | B pages | "
            "A chars | B chars | A tables | B tables | A time (s) | "
            "B time (s) | Review / result |"
        ),
        ("|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"),
    ]

    for row in rows:
        first = row["first"]
        second = row["second"]
        result = row["result"].replace("|", "/")

        lines.append(
            f"| {row['path']} | {row['format']} | {row['a']} | "
            f"{row['b']} | {first['pages']} | {second['pages']} | "
            f"{first['chars']} | {second['chars']} | "
            f"{first['tables']} | {second['tables']} | "
            f"{first['seconds']:.3f} | {second['seconds']:.3f} | "
            f"{result} |"
        )

    lines.extend(
        [
            "",
            "### Manual inspection",
            "",
            (
                "- Inspected three stored legal documents in Neon: "
                "The Companies Act, 2013; The Customs Tariff Act, 1975; "
                "and The Income-tax Act, 1961."
            ),
            (
                "- All three documents contained meaningful extracted text. "
                "Page 2 had heading metadata; page 1 had an empty heading array."
            ),
            "- Companies Act: 546 pages, 93 tables and 1,573,723 characters.",
            "- Customs Tariff Act: 712 pages, 601 tables and 1,803,883 characters.",
            "- Income-tax Act: 1,288 pages, 20 tables and 3,692,599 characters.",
            "",
            "### Parser comparison observations",
            "",
        ]
    )

    for row in rows:
        first = row["first"]
        second = row["second"]

        lines.append(
            f"- {row['path']}: {row['a']} extracted {first['chars']} "
            f"characters and {first['tables']} tables in "
            f"{first['seconds']:.3f}s; {row['b']} extracted "
            f"{second['chars']} characters and {second['tables']} tables "
            f"in {second['seconds']:.3f}s. Character counts alone do not "
            "establish extraction quality; inspect the actual content."
        )

    lines.extend(
        [
            "",
            "### Corpus limitation",
            "",
            f"- Available PDF files in data/: {available_pdf}.",
            f"- Available HTML files in data/: {available_html}.",
            f"- Files compared in this run: {len(rows)}.",
            ("- HTML parser comparison has been tested using Fitness Journal.html."),
            (
                "- The ten-file requirement remains incomplete because "
                "fewer than ten suitable PDF/HTML files are currently "
                "available in data/."
            ),
            (
                "- The available test files are not the original separate "
                "364-file corpus mentioned in the exercise."
            ),
            "",
        ]
    )

    existing = NOTES.read_text(encoding="utf-8") if NOTES.exists() else ""
    marker = "## Day 7 - Part 5: Parser comparison"

    if marker in existing:
        existing = existing.split(marker, 1)[0].rstrip() + "\n\n"

    NOTES.write_text(
        existing + "\n".join(lines),
        encoding="utf-8",
    )


def main():
    """Run comparisons and update project notes."""
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()

    if args.paths:
        files = [path if path.is_absolute() else ROOT / path for path in args.paths]
    else:
        files = sorted(
            (
                path
                for path in DATA.rglob("*")
                if path.is_file() and path.suffix.lower() in SUPPORTED
            ),
            key=lambda path: path.stat().st_size,
            reverse=True,
        )[:10]

    files = [path.resolve() for path in files if path.is_file()]

    if not files:
        raise SystemExit("No PDF or HTML files found.")

    unsupported = [path for path in files if path.suffix.lower() not in SUPPORTED]

    if unsupported:
        raise SystemExit(
            "Only PDF and HTML files are supported: " + ", ".join(str(path) for path in unsupported)
        )

    available_pdf = count_files({".pdf"})
    available_html = count_files({".html", ".htm"})

    rows = [compare(path) for path in files]

    write_notes(
        rows,
        available_pdf,
        available_html,
    )

    for row in rows:
        first = row["first"]
        second = row["second"]

        print(f"\nFILE: {row['path']}")
        print(
            f"{row['a']}: {first['status']}, {first['chars']} chars, "
            f"{first['tables']} tables, {first['seconds']:.3f}s"
        )
        print(
            f"{row['b']}: {second['status']}, {second['chars']} chars, "
            f"{second['tables']} tables, {second['seconds']:.3f}s"
        )
        print(f"RESULT: {row['result']}")

    print(
        f"\nCompared {len(rows)} files. Available corpus: "
        f"{available_pdf} PDF, {available_html} HTML."
    )
    print("Comparison table written to NOTES.md")


if __name__ == "__main__":
    main()
