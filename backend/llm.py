import json
import logging
import re
from typing import Dict, Any, Optional

from backend.config import (
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    GROQ_API_KEY,
    OPENAI_BASE_URL,
    LLM_MODEL
)

logger = logging.getLogger(__name__)

def is_llm_configured() -> bool:
    """Check if an AI provider API key is configured."""
    return bool(GEMINI_API_KEY or OPENAI_API_KEY or GROQ_API_KEY)

def get_active_model() -> str:
    """Return the name of the active LLM model."""
    if LLM_MODEL:
        return LLM_MODEL
    if GROQ_API_KEY:
        return "openai/gpt-oss-120b"
    if OPENAI_API_KEY:
        return "gpt-4o-mini"
    if GEMINI_API_KEY:
        return "gemini-2.5-flash"
    return "Heuristic Mode (No API Key)"

def generate_json_response(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.0
) -> Optional[Dict[str, Any]]:
    """
    Generate structured JSON response using either Groq, OpenAI/OpenRouter, or Gemini
    depending on available API keys and configured LLM_MODEL.
    """
    model_name = get_active_model()

    # 1. Try Groq or OpenAI / OpenRouter / Custom compatible endpoint
    api_key = OPENAI_API_KEY or GROQ_API_KEY
    if api_key:
        try:
            from openai import OpenAI

            base_url = OPENAI_BASE_URL
            if GROQ_API_KEY and not OPENAI_API_KEY and not base_url:
                base_url = "https://api.groq.com/openai/v1"
            elif not base_url and "/" in model_name:
                base_url = "https://openrouter.ai/api/v1"

            client_kwargs: Dict[str, Any] = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url

            client = OpenAI(**client_kwargs)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"}
            )

            raw_content = response.choices[0].message.content or "{}"
            # Extract JSON if enclosed in markdown code fences
            clean_content = raw_content.strip()
            if clean_content.startswith("```"):
                clean_content = re.sub(r"^```(?:json)?\s*", "", clean_content)
                clean_content = re.sub(r"\s*```$", "", clean_content)
            return json.loads(clean_content)

        except Exception as e:
            logger.error(f"Error calling OpenAI-compatible model '{model_name}': {e}")
            if not GEMINI_API_KEY:
                return None

    # 2. Try Google Gemini
    if GEMINI_API_KEY:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=GEMINI_API_KEY)
            gemini_model = model_name if ("gemini" in model_name.lower()) else "gemini-2.5-flash"

            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(
                model=gemini_model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=temperature
                )
            )
            return json.loads(response.text)

        except Exception as e:
            logger.error(f"Error calling Gemini model '{model_name}': {e}")
            return None

    return None

