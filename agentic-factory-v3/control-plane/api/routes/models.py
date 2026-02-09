"""List Gemini/Google AI Studio models for agent creation (dropdown)."""

import os

from fastapi import APIRouter

router = APIRouter(prefix="/api/v2", tags=["models"])

# Fallback list when API key is not set or list fails (latest as of 2025/2026)
DEFAULT_GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-preview",
    "gemini-2.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-1.5-pro-002",
    "gemini-1.0-pro",
    # Gemini 3 series (2025+)
    "gemini-3-pro-preview",
    "gemini-3-flash-preview",
]


def _list_models_from_api() -> list[str] | None:
    """Call Google AI list models if GOOGLE_API_KEY is set and google-genai is available."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        names = []
        for m in client.models.list():
            name = getattr(m, "name", None) or getattr(m, "display_name", None)
            if name is None and hasattr(m, "model"):
                name = getattr(m.model, "name", None) if hasattr(m.model, "name") else None
            if name and isinstance(name, str):
                if "/" in name:
                    name = name.split("/")[-1]
                if name not in names and "gemini" in name.lower():
                    names.append(name)
        return sorted(names) if names else None
    except Exception:
        return None


@router.get("/models")
def list_models():
    """
    List Gemini model IDs suitable for agent model selection.
    Uses Google AI Studio API when GOOGLE_API_KEY is set; otherwise returns a static list.
    """
    models = _list_models_from_api()
    if not models:
        models = list(DEFAULT_GEMINI_MODELS)
    return {"models": models}
