"""
OpenAI GPT-4o Vision integration for food analysis.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a professional dietitian AI.
Analyse the provided food image or text description and return ONLY a valid JSON object — no markdown, no extra text.

Required format:
{"description": "<brief food name>", "calories": <int>, "protein": <int>, "carbs": <int>, "fat": <int>}

Rules:
- All macro values are in grams, calories in kcal.
- If the input is NOT food (e.g. a selfie, a landscape), return:
  {"error": "not_food", "message": "<why>"}
- Be conservative with portions when the size is ambiguous.
- Never refuse to estimate; always give a best-guess number."""


async def analyse_food_image(
    client: AsyncOpenAI,
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> dict:
    """Send a food photo to GPT-4o Vision and parse the JSON response."""
    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{mime_type};base64,{b64}"

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "low"},
                    },
                    {"type": "text", "text": "Analyse this food image."},
                ],
            },
        ],
        max_tokens=256,
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    return _parse_json(raw)


async def analyse_food_text(client: AsyncOpenAI, text: str) -> dict:
    """Send a text description to GPT-4o and parse the JSON response."""
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyse this food description: {text}"},
        ],
        max_tokens=256,
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    return _parse_json(raw)


def _parse_json(raw: str) -> dict:
    """Extract and validate JSON from the model response."""
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse OpenAI response: %s | raw: %s", exc, raw)
        return {"error": "parse_error", "message": "Could not parse AI response."}

    if "error" in data:
        return data

    required = {"description", "calories", "protein", "carbs", "fat"}
    if not required.issubset(data.keys()):
        return {"error": "missing_fields", "message": "Incomplete nutritional data."}

    # Coerce to int just in case the model returns floats
    for field in ("calories", "protein", "carbs", "fat"):
        data[field] = int(round(data[field]))

    return data
