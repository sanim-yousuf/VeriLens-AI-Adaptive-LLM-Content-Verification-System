import json
from typing import Any

from app.schemas import ModerationResult, TrustAnalysis
from app.settings import Settings


class OpenAIClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = bool(settings.openai_api_key)
        self._client = None
        self.unavailable_reason = "OPENAI_API_KEY is not configured."

        if self.enabled:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
            if not hasattr(self._client, "responses"):
                self.enabled = False
                self.unavailable_reason = (
                    "Installed OpenAI SDK does not support the Responses API. "
                    "Run `python -m pip install -r backend/requirements.txt`."
                )
            else:
                self.unavailable_reason = ""

    async def moderate(self, content: str) -> ModerationResult:
        if not self.enabled or self._client is None:
            return ModerationResult(reason=f"Moderation skipped. {self.unavailable_reason}")

        result = (
            await self._client.moderations.create(
                model=self.settings.moderation_model,
                input=content[: self.settings.max_input_chars],
            )
        ).results[0]

        categories = result.categories.model_dump() if hasattr(result.categories, "model_dump") else {}
        return ModerationResult(
            flagged=bool(result.flagged),
            categories=[name for name, enabled in categories.items() if enabled],
            reason="Content matched moderation categories." if result.flagged else None,
        )

    async def analyze(self, model: str, instructions: str, prompt: str) -> tuple[TrustAnalysis, dict[str, int]]:
        if not self.enabled or self._client is None:
            raise RuntimeError(self.unavailable_reason)

        response = await self._client.responses.create(
            model=model,
            instructions=instructions,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "verilens_trust_analysis",
                    "schema": TrustAnalysis.model_json_schema(),
                    "strict": True,
                }
            },
            max_output_tokens=self.settings.max_output_tokens,
            store=False,
        )

        return TrustAnalysis.model_validate_json(self._output_text(response)), self._usage(response)

    async def answer(self, model: str, instructions: str, prompt: str) -> str:
        if not self.enabled or self._client is None:
            raise RuntimeError(self.unavailable_reason)

        response = await self._client.responses.create(
            model=model,
            instructions=instructions,
            input=prompt,
            max_output_tokens=700,
            store=False,
        )
        return self._output_text(response)

    def _output_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text

        payload = response.model_dump() if hasattr(response, "model_dump") else {}
        for output_item in payload.get("output", []):
            for content_item in output_item.get("content", []):
                if content_item.get("text"):
                    return content_item["text"]
        raise RuntimeError("OpenAI response did not contain text output.")

    def _usage(self, response: Any) -> dict[str, int]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}

        payload = usage.model_dump() if hasattr(usage, "model_dump") else json.loads(json.dumps(usage, default=str))
        details = payload.get("input_tokens_details") or {}
        return {
            "input_tokens": int(payload.get("input_tokens") or 0),
            "output_tokens": int(payload.get("output_tokens") or 0),
            "cached_tokens": int(details.get("cached_tokens") or 0),
        }
