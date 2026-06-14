# Architecture

## Product Frame

VeriLens AI is not a binary fake-news detector. It is an explainable trust-intelligence layer that gives users a score, reasons, uncertainty, and a recommended action.

## Request Pipeline

```text
User input
 -> size and type validation
 -> local preprocessing
 -> language detection
 -> content hash cache
 -> source/domain reputation
 -> moderation gate
 -> offline heuristic baseline
 -> adaptive OpenAI analysis
 -> weighted score reconciliation
 -> claim checks, risk factors, regional context, and trust timeline
 -> structured API response
 -> dashboard rendering
```

## Why This Is Cost Efficient

The backend always computes a local baseline first. That gives the router enough signal to avoid expensive calls for easy or repeated content. Deep analysis is reserved for high-risk topics, uncertain findings, image/screenshot cases, and explicit user escalation.

## Backend Modules

- `main.py`: FastAPI setup and routes.
- `settings.py`: environment configuration.
- `schemas.py`: Pydantic contracts.
- `pipeline.py`: preprocessing, source scoring, offline fallback, model routing, and final score reconciliation.
- `openai_client.py`: OpenAI moderation and Structured Outputs calls.
- `store.py`: in-memory analysis cache.

This is intentionally compact. The product can later split these files again when PostgreSQL, Redis, OCR workers, and a human-review queue become necessary.

## Frontend

The frontend is a working verification surface rather than a landing page. It exposes the core analysis workflow immediately and renders:

- trust score
- risk level
- signal breakdown
- claim checks
- risk factors
- suspicious highlights
- evidence and inference
- source credibility
- runtime/cost metadata
- agent findings
- report assistant
