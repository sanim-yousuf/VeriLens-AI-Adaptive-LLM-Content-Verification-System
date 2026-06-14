# API Contract

## Create Analysis

`POST /v1/analyses`

```json
{
  "type": "text",
  "content": "Article, claim, screenshot OCR text, or URL.",
  "analysis_mode": "standard",
  "source_url": "https://example.com/article",
  "locale": "bn-BD",
  "user_context": {
    "region": "BD",
    "audience": "general"
  }
}
```

`type` can be `text`, `url`, `image`, or `screenshot`.

`analysis_mode` can be:

- `quick`
- `standard`
- `deep`
- `offline`

## Response Shape

```json
{
  "analysis_id": "uuid",
  "schema_version": "2026-05-26",
  "input_type": "text",
  "topic": "health",
  "language": "mixed",
  "trust_score": 62,
  "risk_level": "medium",
  "confidence": 0.64,
  "misinformation_probability": 41,
  "manipulation_score": 35,
  "source_score": 55,
  "evidence_quality": 60,
  "score_breakdown": {
    "source_credibility": 55,
    "evidence_consistency": 60,
    "manipulation_intensity": 35,
    "language_patterns": 72,
    "context_risk": 75,
    "visual_authenticity": 100,
    "viral_risk": 30
  },
  "reasoning": [],
  "highlight_spans": [],
  "agent_findings": [],
  "visual_authenticity": {
    "deepfake_risk": 0,
    "tampering_risk": 0,
    "notes": "No visual input provided."
  },
  "risk_factors": [],
  "claim_checks": [],
  "manipulation_patterns": [],
  "ai_generated_likelihood": 18,
  "viral_risk": 30,
  "regional_context": {
    "region": "BD",
    "sensitivity": 75,
    "note": "Bangladesh context applied."
  },
  "community_signal": {
    "report_count": 0,
    "consensus": "not_enough_reports",
    "note": "No community reports yet."
  },
  "trust_timeline": [],
  "expert_notes": [],
  "recommended_action": "verify_before_sharing",
  "summary": "Short user-facing explanation.",
  "uncertainty": "Known limits and missing evidence.",
  "moderation": {
    "flagged": false,
    "categories": []
  },
  "cost": {
    "model_used": "gpt-5.4-mini",
    "input_tokens": 0,
    "output_tokens": 0,
    "cached_tokens": 0,
    "analysis_mode": "standard",
    "cache_hit": false,
    "openai_used": true
  }
}
```

## Ask About A Report

`POST /v1/analyses/{analysis_id}/explain`

```json
{
  "question": "Why is the trust score medium?"
}
```

Response:

```json
{
  "analysis_id": "uuid",
  "answer": "Short explanation grounded in the report.",
  "openai_used": true,
  "model_used": "gpt-5.4-mini"
}
```

## Deep Review

`POST /v1/analyses/{analysis_id}/deep-review`

Pass the original content again. The route forces `analysis_mode=deep`.

## Feedback

`POST /v1/feedback`

```json
{
  "analysis_id": "uuid",
  "user_rating": 4,
  "corrected_risk_level": "medium",
  "notes": "Useful, but source credibility felt too harsh."
}
```

Response:

```json
{
  "accepted": true,
  "message": "Feedback received. It will be used for evaluation and calibration.",
  "analysis_id": "uuid",
  "report_count": 1,
  "consensus": "medium"
}
```

The matching analysis report is also updated so the frontend can render the latest `community_signal`.
