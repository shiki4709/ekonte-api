"""Small provider interface: other models can implement complete()."""

import json
import os
from typing import Protocol


class Provider(Protocol):
    def complete(self, prompt: str, media: list[tuple[str, bytes]], schema: dict) -> dict: ...


class GeminiProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        from google import genai

        key = api_key or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("set GOOGLE_API_KEY or use offline analysis")
        self.model = model or os.getenv("EKONTE_MODEL", "gemini-2.5-flash")
        self.client = genai.Client(api_key=key, http_options={"timeout": 120000})

    def complete(self, prompt, media, schema):
        from google.genai import types

        parts = [types.Part.from_text(text=prompt)]
        parts += [types.Part.from_bytes(data=data, mime_type=mime) for mime, data in media]
        response = self.client.models.generate_content(
            model=self.model,
            contents=parts,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": schema,
                "max_output_tokens": 16000,
                "thinking_config": {"thinking_budget": 0},
            },
        )
        return json.loads(response.text or "{}")
