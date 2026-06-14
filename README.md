# VeriLens AI

Explainable multilingual trust intelligence for digital content verification.

<img width="1917" height="1077" alt="image" src="https://github.com/user-attachments/assets/1e4cbdab-5d1e-44c8-9d2a-31bf7e9475d7" />


VeriLens AI is a cost-aware trust-analysis platform for Bangla, Banglish, and English content. It combines local preprocessing, moderation, adaptive OpenAI model routing, source reputation heuristics, offline fallback, and a React verification dashboard.

## What Is Implemented

- FastAPI backend with `/v1/analyses`, `/v1/analyses/{id}`, `/v1/analyses/{id}/deep-review`, `/v1/feedback`, and `/health`.
- Adaptive analysis pipeline:
  - local preprocessing and language detection
  - content-hash caching
  - moderation gate
  - local source reputation
  - offline heuristic fallback
  - OpenAI Responses API Structured Outputs when `OPENAI_API_KEY` is configured
  - weighted score reconciliation
  - claim checks, risk factors, regional context, viral-risk, AI-likelihood, trust timeline, and report assistant
- React + Tailwind verification workspace:
  - text, URL, and screenshot modes
  - quick, standard, deep, and offline analysis modes
  - trust gauge, risk banner, signal breakdown, claim checks, highlights, evidence, source, timeline, runtime, and agent panels
- Dockerfiles and Docker Compose.
- Tests for offline scoring and cache behavior.
- API contract tests for frontend report fields, cached report explanation, and feedback/community signal updates.

## Security Note

Do not commit API keys. Put your key in `.env` as `OPENAI_API_KEY=...`. If a key has been pasted into chat, rotate it before production use.

## Run Locally

```powershell
copy .env.example .env
.\start.bat
```

That single command creates the backend virtual environment, installs missing frontend packages, starts FastAPI, and opens the Vite dev server.

Frontend: `http://localhost:5173`  
Backend: `http://localhost:8000`

To stop the system, press `Ctrl+C` in the terminal running `start.bat`.

## Docker Compose

```powershell
copy .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

Frontend: `http://localhost:5173`  
Backend: `http://localhost:8000`

## Environment

Use `.env.example` as the template. The app runs without `OPENAI_API_KEY` in offline heuristic mode. When the key is configured, standard/deep requests use the OpenAI pipeline.

## Simple Codebase Map

```text
backend/app/
  main.py          FastAPI routes and app setup
  settings.py      environment configuration
  schemas.py       request and response models
  pipeline.py      preprocessing, scoring, routing, offline fallback
  openai_client.py OpenAI moderation and structured analysis calls
  store.py         in-memory result cache

frontend/src/
  App.tsx          main screen
  components/      dashboard panels
  services/api.ts  backend API client
  types/           shared response types
```

## Cost-Aware Model Routing

- `offline`: no OpenAI call
- `quick`: triage model
- `standard`: standard model unless content is high-stakes or risky
- `deep`: advanced or premium model based on topic and input type

Model names are environment-controlled so you can pin or replace them without code changes.

## OpenAI API Usage

The backend keeps all OpenAI calls server-side in `backend/app/openai_client.py`.

- Moderation uses the configured moderation model before deeper analysis.
- Trust analysis uses the Responses API with JSON Schema Structured Outputs.
- Report questions use the Responses API when `OPENAI_API_KEY` is configured and fall back to a local explainer otherwise.
