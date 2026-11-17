# Requirements: ConsumerShield

## Functional (what it does)

1. Users can ask questions in plain English and receive answers based on the project's collected legal documents and sources.
2. Every answer must include citations showing the document name and the relevant page number or section.
3. If the required information is not available in the documents, the product must respond with **"I don't know"** instead of guessing or generating unsupported information.
4. **Signature feature – Similar Cases Panel:** Users can describe their consumer complaint and view three relevant decided consumer commission cases, including their outcomes, compensation awarded, and the appropriate commission for filing.
5. Users can browse and search the underlying legal records through the `GET /v1/documents` API endpoint.

## Non-functional (how well, with numbers)

| # | Quality | Target | How I will measure it |
|---|---|---|---|
| 1 | Speed: record lookups | p95 under 300 ms for `GET /v1/documents` | Load testing (Week 6) |
| 2 | Speed: answers | p95 under 4 seconds for a complete answer; first token under 1.5 seconds | Performance traces (Week 5) |
| 3 | Accuracy | Correct commission and relevant precedent in the top 3 results for at least 85% of 30 test scenarios | Golden question set (Weeks 4 and 5) |
| 4 | Cost | Under ₹0.50 per answered question | Track usage through the `llm_calls` database table (Week 2) |
| 5 | Availability | 99% monthly uptime for the live application URL | Uptime monitoring starting from Day 5 |
