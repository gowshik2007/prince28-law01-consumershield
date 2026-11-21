# ConsumerShield

[![CI](https://github.com/gowshik2007/prince28-law01-consumershield/actions/workflows/ci.yml/badge.svg)](https://github.com/gowshik2007/prince28-law01-consumershield/actions/workflows/ci.yml)
[![Live](https://img.shields.io/website?url=https%3A%2F%2Fconsumershield-82yz.onrender.com%2Fhealth&label=live)](https://consumershield-82yz.onrender.com/docs)
[![Uptime (30 days)](https://img.shields.io/uptimerobot/ratio/m804745837-9ac143bf4c955f8db7c4ce39)](https://consumershield-82yz.onrender.com/health)

ConsumerShield is a consumer-rights legal information project focused on helping people understand their rights under Indian consumer-protection law and find relevant legal documents.

**Project status:** Week 1 implementation and deployment milestones completed. Live API: https://consumershield-82yz.onrender.com

## The problem

Consumers often struggle to understand their rights, identify the correct consumer commission, and find relevant legal precedents when dealing with defective products, refunds, and unfair online-selling practices.

ConsumerShield aims to make this information easier to access through searchable legal documents and, as the project develops, evidence-backed answers with citations.

## Who it's for

An example target user is an engineering student in Chennai whose ₹45,000 laptop arrives damaged and whose online seller refuses a refund.

## Product requirements and evaluation

The project requirements and initial evaluation questions are documented here:

- [Functional and non-functional requirements](docs/REQUIREMENTS.md)
- [10 real-user evaluation questions](docs/QUESTIONS.md)

The evaluation set includes questions about consumer rights, e-commerce refunds, dark patterns, defective products, compensation, complaint filing, and similar consumer commission cases.

Question 6 is intentionally unanswerable from the available documents. The intended system behavior is to respond with **"I don't know"** rather than invent an answer.

## Current implementation

The current application provides:

- A FastAPI application with structured configuration and logging.
- Health and database-readiness endpoints.
- Document listing and retrieval endpoints.
- PostgreSQL persistence using SQLAlchemy.
- Alembic database migrations.
- JSONB metadata filtering with a GIN index.
- An idempotent sample-data loader using SHA-256 fingerprints.
- Docker and Docker Compose development environment.
- Unit and database integration tests.
- GitHub Actions CI and automated Render deployment.
- Production health monitoring.

**Important:** Evidence-backed legal question answering, automatic case matching, and the Similar Cases Panel are product goals described in the requirements. They should not be considered implemented features of the current API.

## Data sources and planned experience

The project is designed around Indian consumer-protection material, including:

- Consumer Protection Act, 2019.
- Consumer Protection (E-Commerce) Rules, 2020.
- Consumer Protection (Jurisdiction) Rules, 2021.
- CCPA Dark Patterns Guidelines, 2023.
- National Consumer Helpline information.
- Selected NCDRC and State Consumer Commission orders.

The initial evaluation questions identify the documents and legal provisions needed for each scenario. Exact case references and page details are to be added as the dataset is developed.

The planned signature experience is a Similar Cases Panel showing relevant decided consumer commission cases, their outcomes, and compensation details.

## API endpoints

The currently implemented endpoints are:

| Method | Endpoint | Purpose |
|---|---|---|
| GET, HEAD | `/health` | Application health and deployment metadata |
| GET | `/ready` | Database readiness check |
| GET | `/v1/documents` | List and filter stored documents |
| GET | `/v1/documents/{doc_id}` | Retrieve a document by its external ID |

The document-list endpoint supports pagination and search/filter parameters.

Interactive API documentation is available at `/docs`.

## Architecture

The project uses a Python `src` layout.

```text
src/consumershield/
├── config.py
├── logging_setup.py
├── api/
│   ├── deps.py
│   ├── errors.py
│   ├── main.py
│   ├── middleware.py
│   └── routes/
│       ├── documents.py
│       └── health.py
└── db/
    ├── models.py
    ├── repository.py
    ├── session.py
    └── url.py
```

Supporting project directories include:

- `alembic/` — database migrations.
- `data/` — sample legal-document records.
- `scripts/` — data loading, smoke tests, and database inspection utilities.
- `tests/` — unit and integration tests.
- `docs/` — requirements and evaluation questions.

## Technology stack

- Python 3.12
- FastAPI
- PostgreSQL 17
- SQLAlchemy
- Alembic
- JSONB and GIN indexes
- Redis
- Docker and Docker Compose
- uv for Python dependency management
- Ruff and pre-commit
- GitHub Actions
- Render deployment
- UptimeRobot monitoring

## Run locally in one command

### Prerequisites

- Docker Desktop with Docker Compose.
- Git.

Clone the repository:

```bash
git clone https://github.com/gowshik2007/prince28-law01-consumershield.git
cd prince28-law01-consumershield
```

Start the application:

```bash
docker compose up --build
```

The Compose stack starts PostgreSQL and Redis, runs database migrations and the sample-data loader, and then starts the API after its dependencies are ready.

Open:

- API documentation: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Readiness: http://localhost:8000/ready

### Local Python development

Install dependencies using the lockfile:

```bash
uv sync --locked
```

Run lint checks:

```bash
uv run poe lint
```

The project also provides unit tests, database integration tests, and coverage checks. Integration tests use a separate test database.

## Configuration and secrets

Application configuration is managed through environment variables and Pydantic Settings.

| Variable | Purpose |
|---|---|
| `APP_NAME` | Application name |
| `APP_ENV` | Environment: `local`, `ci`, or `production` |
| `LOG_LEVEL` | Logging level |
| `DATA_FILE` | Sample data file path |
| `DATABASE_URL` | PostgreSQL connection URL |

See `.env.example` for the local configuration template.

Do not commit `.env` files, database credentials, deployment hooks, or other secrets. Production configuration is managed through the hosting and GitHub Actions environment settings.

## Database

PostgreSQL stores documents and their associated pages.

Alembic manages schema migrations. The database includes a GIN index on the JSONB `documents.metadata` column to support metadata containment queries.

The sample-data loader uses SHA-256 fingerprints to detect changes. Repeated loads do not create duplicate records, and modified records are updated.

## Testing and quality

The project includes:

- Unit tests for API behavior, health checks, errors, and configuration.
- Database integration tests.
- Coverage measurement.
- Ruff linting and formatting checks.
- Pre-commit checks and secret scanning.

The recorded Day 4 test results are 16 unit tests passed, 7 integration tests passed, and 92% combined coverage. These are historical results from that verification run.

## CI/CD and deployment

The project uses GitHub Actions for continuous integration and deployment.

- CI validates changes through linting and tests.
- Successful main-branch builds produce the application image.
- The CD workflow deploys the selected image to Render.
- Database migrations run during normal deployments.
- Production smoke tests verify the deployed API.
- The deployment workflow supports rollback to a previous application image.

Production:

https://consumershield-82yz.onrender.com

Health endpoint:

https://consumershield-82yz.onrender.com/health

## Monitoring

UptimeRobot monitors the production `/health` endpoint at a five-minute interval, with email alerts enabled.

The health response includes application status, environment, and Git commit SHA so that the deployed version can be verified.

## Project targets

The following are project targets, not claims of currently achieved performance:

- Document-list API p95 latency below 300 ms.
- Answer p95 latency below 4 seconds.
- First-token latency below 1.5 seconds.
- At least 85% accuracy for commission identification and precedent retrieval across 30 evaluation scenarios.
- Estimated cost below ₹0.50 per answered question.
- 99% monthly uptime.

See [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) for the complete requirements.
