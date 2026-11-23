"""Inspect the downloaded corpus and generate a dataset planning report."""

import argparse
import csv
import json
import math
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".mdx",
    ".rst",
    ".csv",
    ".json",
    ".jsonl",
    ".xml",
    ".yaml",
    ".yml",
    ".html",
    ".htm",
}


class TextExtractor(HTMLParser):
    """Extract visible text from HTML."""

    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if not self.hidden_depth:
            self.parts.append(data)

    def get_text(self):
        return " ".join(self.parts)


def read_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".html", ".htm"}:
        parser = TextExtractor()
        parser.feed(raw)
        return parser.get_text()
    return raw


def estimate_chunks(tokens: int, chunk_size: int, overlap: int) -> int:
    if tokens <= 0:
        return 0
    if tokens <= chunk_size:
        return 1
    return math.ceil((tokens - overlap) / (chunk_size - overlap))


def load_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def load_sources(path: Path) -> list[dict]:
    """Load source register while ignoring comment lines."""
    if not path.exists():
        return []
    lines = [
        line
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines:
        return []
    return list(csv.DictReader(lines))


def main():
    parser = argparse.ArgumentParser(description="Analyse ConsumerShield corpus size and capacity.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--full-pages", type=int, default=5000)
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=100)
    parser.add_argument("--dimensions", type=int, default=1536)
    parser.add_argument(
        "--price-per-million",
        type=float,
        default=0.02,
        help="Embedding price in USD per million input tokens.",
    )
    args = parser.parse_args()

    if args.full_pages < 0:
        parser.error("--full-pages cannot be negative")
    if args.chunk_size < 1:
        parser.error("--chunk-size must be positive")
    if not 0 <= args.overlap < args.chunk_size:
        parser.error("--overlap must be between 0 and chunk-size - 1")
    if args.dimensions < 1 or args.price_per_million < 0:
        parser.error("Dimensions must be positive and price cannot be negative")

    root = args.root.resolve()
    manifest_path = root / "data" / "manifest.jsonl"
    sources_path = root / "data" / "sources.csv"

    sources = load_sources(sources_path)
    manifest = load_manifest(manifest_path)

    data_dirs = [root / "data" / "raw", root / "data" / "processed"]
    files = sorted(
        path
        for directory in data_dirs
        if directory.exists()
        for path in directory.rglob("*")
        if path.is_file()
    )

    total_chars = 0
    pdf_count = 0
    pdf_pages_total = 0
    pdf_pages_read = 0
    text_files = 0
    unsupported_files = []
    errors = []

    for path in files:
        if path.name.endswith(".part"):
            continue
        suffix = path.suffix.lower()

        try:
            if suffix == ".pdf":
                pdf_count += 1
                reader = PdfReader(str(path), strict=False)
                pdf_pages_total += len(reader.pages)
                remaining = max(0, args.full_pages - pdf_pages_read)
                pages_to_read = min(len(reader.pages), remaining)
                for page in reader.pages[:pages_to_read]:
                    total_chars += len(page.extract_text() or "")
                    pdf_pages_read += 1
            elif suffix in TEXT_EXTENSIONS:
                total_chars += len(read_text(path))
                text_files += 1
            else:
                unsupported_files.append(path.relative_to(root).as_posix())
        except Exception as exc:
            errors.append(f"{path.relative_to(root).as_posix()}: {type(exc).__name__}: {exc}")

    estimated_tokens = math.ceil(total_chars / 4)
    chunks = estimate_chunks(estimated_tokens, args.chunk_size, args.overlap)
    embedding_cost = estimated_tokens / 1_000_000 * args.price_per_million
    vector_bytes = chunks * args.dimensions * 4
    vector_mib = vector_bytes / (1024 * 1024)

    latest = {}
    for record in manifest:
        if record.get("url"):
            latest[record["url"]] = record

    statuses = {}
    for record in latest.values():
        status = record.get("status", "unknown")
        statuses[status] = statuses.get(status, 0) + 1

    report = [
        "# ConsumerShield Dataset Report",
        "",
        "Generated by `scripts/dataset_report.py`.",
        "",
        "## Source register",
        "",
        "| Source | Title | Licence |",
        "|---|---|---|",
    ]

    if sources:
        report.extend(
            f"| {row.get('source', '')} | {row.get('title', '')} | {row.get('licence', '')} |"
            for row in sources
        )
    else:
        report.append("| No approved sources registered | — | — |")

    report.extend(["", "## Known gaps", ""])
    if not sources:
        report.append("- No approved sources are currently registered.")
    if not files:
        report.append("- No corpus files have been collected.")
    if not manifest:
        report.append("- No manifest records are available.")
    report.append("- India Code automated access requires written permission.")

    report.extend(
        [
            "",
            "## Corpus inventory",
            "",
            f"- Files found: **{len(files)}**",
            f"- PDF files: **{pdf_count}**",
            f"- PDF pages available: **{pdf_pages_total}**",
            f"- PDF pages inspected: **{pdf_pages_read}**",
            f"- Text files inspected: **{text_files}**",
            f"- Unsupported files: **{len(unsupported_files)}**",
            f"- Extraction errors: **{len(errors)}**",
            "",
            "## Processing estimates",
            "",
            f"- Extracted characters: **{total_chars:,}**",
            f"- Estimated tokens (characters ÷ 4): **{estimated_tokens:,}**",
            f"- Chunk size: **{args.chunk_size:,} tokens**",
            f"- Chunk overlap: **{args.overlap:,} tokens**",
            f"- Estimated chunks: **{chunks:,}**",
            f"- Embedding dimensions: **{args.dimensions:,}**",
            f"- Estimated raw vector storage: **{vector_mib:.2f} MiB**",
            f"- Assumed embedding price: **${args.price_per_million:.4f} / million tokens**",
            f"- Estimated embedding cost: **${embedding_cost:.6f}**",
            "",
            "## Manifest status",
            "",
        ]
    )

    if statuses:
        report.extend(f"- {status}: **{count}**" for status, count in sorted(statuses.items()))
    else:
        report.append("- No manifest records found.")

    report.extend(
        [
            "",
            "## Limitations",
            "",
            "- Token counts are approximate; characters divided by four is not a tokenizer.",
            "- PDF extraction may miss scanned pages, tables, or complex layouts.",
            "- Parquet files are not extracted directly; the processed JSONL corpus is inspected.",
            (
                "- Vector storage estimates float32 vectors only; "
                "database indexes and metadata add overhead."
            ),
            (
                "- Embedding cost is a planning estimate using the supplied price, "
                "not a billing quote."
            ),
            f"- PDF extraction is capped at {args.full_pages:,} pages for this run.",
            "",
        ]
    )

    generated_pdf = root / "data" / "processed" / "capacity_test_corpus.pdf"
    if generated_pdf.exists():
        report.extend(
            [
                "## Generated PDF test artifact",
                "",
                "- Derived from processed JSONL; not an original government-source PDF.",
                "- Its text overlaps with JSONL and is counted twice in combined inventory totals.",
                "",
            ]
        )

    if unsupported_files:
        report.extend(["## Unsupported files", ""])
        report.extend(f"- `{name}`" for name in unsupported_files)
        report.append("")

    if errors:
        report.extend(["## Extraction errors", ""])
        report.extend(f"- {error}" for error in errors)
        report.append("")

    output = root / "DATASET.md"
    output.write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))
    print(f"\nReport saved to: {output}")


if __name__ == "__main__":
    main()
