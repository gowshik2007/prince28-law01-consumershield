import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

BASE = "https://ccpa.doca.gov.in"
UA = "ConsumerShieldResearchBot/1.0"


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "tr":
            self.row = []

        elif tag in ("td", "th") and self.row is not None:
            self.cell = {"text": [], "links": []}

        elif tag == "a" and self.cell is not None:
            href = attrs.get("href")
            if href:
                self.cell["links"].append(href)

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.cell["text"] = " ".join(" ".join(self.cell["text"]).split())
            self.row.append(self.cell)
            self.cell = None

        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def fetch_page(url, user_agent):
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def main():
    robots = RobotFileParser()
    robots_url = BASE + "/robots.txt"

    try:
        robots_text = fetch_page(robots_url, UA)
        robots.parse(robots_text.splitlines())
    except HTTPError as exc:
        if exc.code == 404:
            sys.exit(
                "robots.txt is unavailable. Obtain permission or "
                "confirm the site's access policy before proceeding."
            )
        raise

    records = []
    seen = set()

    for page in range(1, 6):
        url = f"{BASE}/ccpa-orders.php?page_no={page}"

        if not robots.can_fetch(UA, url):
            sys.exit(f"Robots policy disallows {url}")

        html = fetch_page(url, UA)
        parser = TableParser()
        parser.feed(html)

        for row in parser.rows:
            if len(row) < 3:
                continue

            title = row[1]["text"]
            date = row[2]["text"]

            if not title:
                continue

            if title.lower() in (
                "title",
                "subject",
                "title of the case",
            ):
                continue

            if title in seen:
                continue

            seen.add(title)

            records.append(
                {
                    "title": title,
                    "date": date,
                    "document_urls": row[-1]["links"],
                    "source": "Central Consumer Protection Authority",
                    "source_page": url,
                    "content_type": "listing_metadata_only",
                    "licence": "Not verified",
                }
            )

            if len(records) >= 100:
                break

        if len(records) >= 100:
            break

    if len(records) < 100:
        sys.exit(f"Only {len(records)} unique order records found. No output written.")

    output_dir = Path("data/raw/ccpa-orders")
    output_dir.mkdir(parents=True, exist_ok=True)

    target = output_dir / "ccpa_orders_metadata.jsonl"

    target.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    print("Unique order records:", len(records))
    print("Missing document links:", sum(not record["document_urls"] for record in records))
    print("Saved:", target)


if __name__ == "__main__":
    main()
