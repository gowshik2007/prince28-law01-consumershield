# ConsumerShield

Helps consumers understand their rights and options for e-commerce and service complaints, with similar consumer-commission cases cited.

**Status:** Day 1 foundation (FastAPI skeleton, quality gates). Live URL from Day 5.

## Who it's for

Engineering student in Chennai whose Rs 45,000 laptop arrived damaged and the online seller refuses a refund.

## The problem

Many consumers face difficulties when purchasing damaged or defective products online or when sellers refuse refunds. They are often unaware of their rights under the Consumer Protection Act, 2019, and the steps required to file a complaint. Finding the correct consumer commission and understanding similar past case decisions can also be confusing. As a result, consumers may struggle to take appropriate legal action and receive fair compensation. ConsumerShield aims to simplify this process by providing clear guidance and relevant case references.

## Data sources

Consumer Protection Act 2019, Consumer Protection (E-Commerce) Rules 2020, CCPA guidelines (incl. dark patterns 2023), 300+ selected NCDRC and state commission orders, National Consumer Helpline FAQs.

- https://consumeraffairs.nic.in/
- https://ncdrc.nic.in/
- https://consumerhelpline.gov.in/
- Terms: Public law and orders. Cite section or case number and date.

## Hardest problem (my interview story)

Case retrieval by facts: finding orders with similar facts (not just similar words), and working out the right commission by claim value in code.

## Signature feature

Similar cases panel: describe your problem and see 3 decided cases with outcome and compensation, plus where to file.

## Target metric

Correct commission and relevant precedent in top 3 for 85%+ of 30 scenarios.

## Run it locally

```bash
uv sync
cp .env.example .env   # Windows: copy .env.example .env
uv run uvicorn consumershield.api.main:create_app --factory --reload
```

Then open http://localhost:8000/docs

## Checks

```bash
uv run pytest
uv run ruff check .
```
