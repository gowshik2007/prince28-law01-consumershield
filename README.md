# ConsumerShield

[![CI](https://github.com/gowshik2007/prince28-law01-consumershield/actions/workflows/ci.yml/badge.svg)](https://github.com/gowshik2007/prince28-law01-consumershield/actions/workflows/ci.yml)
[![Live](https://img.shields.io/website?url=https%3A%2F%2Fconsumershield-82yz.onrender.com%2Fhealth&label=live)](https://consumershield-82yz.onrender.com/docs)
[![Uptime (30 days)](https://img.shields.io/uptimerobot/ratio/m804745837-9ac143bf4c955f8db7c4ce39)](https://consumershield-82yz.onrender.com/health)
Helps consumers understand their rights and options for e-commerce and service complaints, with similar consumer-commission cases cited.

**Status:** Week 1 complete · live at https://consumershield-82yz.onrender.com

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

## Run locally in one command

You need Docker Desktop running. From a fresh clone:

```bash
docker compose up --build
```

This starts Postgres (with pgvector), Redis, runs the migrations and loads the sample data once, then starts the API.

- API docs: http://localhost:8000/docs
- Liveness: http://localhost:8000/health
- Readiness (checks the database): http://localhost:8000/ready

Stop with `Ctrl+C`, then `docker compose down`. Add `-v` to also delete the database volume.

## Develop and test

| Task | Mac / Linux | Windows |
|---|---|---|
| Run the API with reload | `make dev` | `uv run poe dev` |
| Unit tests (no network) | `make test` | `uv run poe test` |
| Integration tests (needs `docker compose up`) | `make test-integration` | `uv run poe test-integration` |
| Coverage report | `make cov` | `uv run poe cov` |
| Lint and format check | `make lint` | `uv run poe lint` |
