# Cost Strategy

## Principles

1. Avoid remote calls when local rules are enough.
2. Cache repeated content by normalized hash.
3. Use low-cost models for routing and ordinary analysis.
4. Escalate only when risk, ambiguity, or user intent justifies it.
5. Keep Structured Output schemas concise.
6. Cap input length and output tokens.
7. Store token usage per result.

## Routing

```text
offline -> local heuristics only
quick -> triage model
standard -> standard model or advanced model for high-stakes topics
deep -> advanced or premium model
```

## Runtime Metadata

Every analysis includes:

- `model_used`
- `input_tokens`
- `output_tokens`
- `cached_tokens`
- `analysis_mode`
- `cache_hit`
- `openai_used`

These fields are visible in the dashboard and ready for an admin cost page.

## Production Additions

- Move the in-memory repository to Redis/PostgreSQL.
- Add per-user quotas.
- Add a background queue for screenshot OCR and deep reviews.
- Add Batch API jobs for eval datasets and nightly recalibration.
- Track average cost per analysis by mode, topic, and input type.
