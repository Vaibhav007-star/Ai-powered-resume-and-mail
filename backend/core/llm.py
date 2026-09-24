import json
import logging
import re
from typing import Dict, Any, Optional

from backend.core.config import (
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

_openai_client = None
_openai_client_key = None
_gemini_client = None
_gemini_client_key = None

JSON_CLEAN_PREFIX = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
JSON_CLEAN_SUFFIX = re.compile(r"\s*```$", re.IGNORECASE)

def _get_openai_client(api_key: str, base_url: Optional[str] = None):
    global _openai_client, _openai_client_key
    cache_key = (api_key, base_url)
    if _openai_client is None or _openai_client_key != cache_key:
        from openai import OpenAI
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        _openai_client = OpenAI(**client_kwargs)
        _openai_client_key = cache_key
    return _openai_client

def _get_gemini_client(api_key: str):
    global _gemini_client, _gemini_client_key
    if _gemini_client is None or _gemini_client_key != api_key:
        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
        _gemini_client_key = api_key
    return _gemini_client

def generate_json_response(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.0
) -> Optional[Dict[str, Any]]:
    """Generate structured JSON response using Groq, OpenAI/OpenRouter, or Gemini."""
    model_name = get_active_model()

    api_key = OPENAI_API_KEY or GROQ_API_KEY
    if api_key:
        try:
            base_url = OPENAI_BASE_URL
            if GROQ_API_KEY and not OPENAI_API_KEY and not base_url:
                base_url = "https://api.groq.com/openai/v1"
            elif not base_url and "/" in model_name:
                base_url = "https://openrouter.ai/api/v1"

            client = _get_openai_client(api_key, base_url)

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
            clean_content = raw_content.strip()
            if clean_content.startswith("```"):
                clean_content = JSON_CLEAN_PREFIX.sub("", clean_content)
                clean_content = JSON_CLEAN_SUFFIX.sub("", clean_content)
            return json.loads(clean_content)

        except Exception as e:
            logger.error(f"Error calling OpenAI-compatible model '{model_name}': {e}")
            if not GEMINI_API_KEY:
                return None

    if GEMINI_API_KEY:
        try:
            from google.genai import types

            client = _get_gemini_client(GEMINI_API_KEY)
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
