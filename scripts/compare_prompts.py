"""Compare every version of the classify prompt against the evaluation set."""

import argparse
import asyncio
import json
from pathlib import Path

from consumershield.config import get_settings
from consumershield.llm.classify import accuracy, classify, find_leaks
from consumershield.llm.gateway import build_gateway
from consumershield.llm.prompts import read_prompt, versions

ROOT = Path(__file__).resolve().parents[1]
TESTSET = ROOT / "eval" / "prompt_testset.jsonl"
CACHE = ROOT / "eval" / "cache"
NOTES = ROOT / "NOTES.md"


def load_rows() -> list[dict]:
    return [
        json.loads(line)
        for line in TESTSET.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


async def compare(force: bool = False) -> None:
    settings = get_settings()
    prompt_dir = settings.prompts_dir
    if not prompt_dir.is_absolute():
        prompt_dir = ROOT / prompt_dir

    names = versions(prompt_dir, "classify")
    if not names:
        raise FileNotFoundError(f"No classify prompts found in {prompt_dir}")

    rows = load_rows()
    CACHE.mkdir(parents=True, exist_ok=True)
    gateway = build_gateway(settings)

    if not gateway.providers:
        raise RuntimeError("No LLM provider is configured. Set GEMINI_API_KEY or GROQ_API_KEY.")

    results = []

    for version in names:
        prompt = read_prompt(prompt_dir, version)
        questions = [row["question"] for row in rows]
        leaks = find_leaks(prompt, questions)
        if leaks:
            print(f"LEAK in {version}: {leaks}")
            raise RuntimeError(f"{version} contains evaluation questions")

        cache_file = CACHE / f"{version}.json"
        cached = {}
        if cache_file.exists() and not force:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))

        answers = []
        for index, row in enumerate(rows):
            question = row["question"]
            key = str(index)
            if key in cached and cached[key].get("question") == question:
                got = cached[key]["got"]
                print(f"{version} [{index + 1}/{len(rows)}] cached: {got}")
            else:
                label, result = await classify(gateway, prompt, version, question)
                got = label
                cached[key] = {"question": question, "label": row["label"], "got": got}
                cache_file.write_text(
                    json.dumps(cached, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                print(f"{version} [{index + 1}/{len(rows)}] {got} (Rs {result.cost_inr:.6f})")
            answers.append({"label": row["label"], "got": got})

        score = accuracy(answers)
        misses = [
            {
                "question": rows[i]["question"],
                "expected": rows[i]["label"],
                "got": answer["got"],
            }
            for i, answer in enumerate(answers)
            if answer["got"] != answer["label"]
        ]
        results.append((version, score, misses))
        print(f"\n{version}: {score:.1%} ({len(answers) - len(misses)}/{len(answers)})")
        for miss in misses:
            print(f"  MISS expected={miss['expected']} got={miss['got']}: {miss['question']}")

    table = [
        "\n## Prompt comparison",
        "",
        "| Prompt | Accuracy | Correct | Misses |",
        "|---|---:|---:|---:|",
    ]
    for version, score, misses in results:
        table.append(
            f"| {version} | {score:.1%} | {len(rows) - len(misses)}/{len(rows)} | {len(misses)} |"
        )

    section = "\n".join(table) + "\n"
    existing = NOTES.read_text(encoding="utf-8") if NOTES.exists() else ""
    marker = "\n## Prompt comparison"
    if marker in existing:
        existing = existing.split(marker)[0].rstrip() + "\n"
    NOTES.write_text(existing.rstrip() + "\n\n" + section, encoding="utf-8")
    print(f"\nComparison written to {NOTES}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="ignore cached answers and run every question again",
    )
    args = parser.parse_args()
    asyncio.run(compare(force=args.force))


if __name__ == "__main__":
    main()
