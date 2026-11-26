import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

PROVIDERS = [
    {
        "name": "gemini",
        "key": os.getenv("GEMINI_API_KEY"),
        "model": os.getenv("LLM_PRIMARY_MODEL", "gemini-3.8-flash"),
        "url": os.getenv(
            "LLM_PRIMARY_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai",
        ),
    },
    {
        "name": "groq",
        "key": os.getenv("GROQ_API_KEY"),
        "model": os.getenv("LLM_FALLBACK_MODEL", "openai/gpt-oss-20b"),
        "url": os.getenv(
            "LLM_FALLBACK_BASE_URL",
            "https://api.groq.com/openai/v1",
        ),
    },
]


def ping(provider):
    name = provider["name"]
    key = provider["key"]

    if not key:
        print(f"{name:<7} FAILED   API key missing")
        return

    payload = {
        "model": provider["model"],
        "messages": [{"role": "user", "content": "Reply with one word: pong"}],
        "temperature": 0,
    }

    start = time.perf_counter()

    try:
        response = httpx.post(
            f"{provider['url']}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
            timeout=60.0,
        )

        response.raise_for_status()

        elapsed = (time.perf_counter() - start) * 1000
        data = response.json()

        reply = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        print(
            f"{name:<7} OK       {provider['model']} "
            f"said '{reply}' in {elapsed:.0f} ms, "
            f"tokens in={usage.get('prompt_tokens', '?')} "
            f"out={usage.get('completion_tokens', '?')}"
        )

    except httpx.HTTPStatusError as error:
        print(f"{name:<7} FAILED   {error}")
        print("Details:", error.response.text)

    except Exception as error:
        print(f"{name:<7} FAILED   {error}")


if __name__ == "__main__":
    for provider in PROVIDERS:
        ping(provider)
