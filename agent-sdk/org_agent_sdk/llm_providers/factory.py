"""LLM Provider Factory - Create the appropriate provider based on configuration."""

import os
from typing import Optional, Dict, Any

from .base import LLMProvider
from .google_ai_studio import GoogleAIStudioProvider
from .vertex_ai import VertexAIProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .unified_google import UnifiedGoogleProvider


# Provider name mappings
PROVIDER_MAP = {
    "google": UnifiedGoogleProvider,  # Unified API key-based provider
    "google_ai_studio": GoogleAIStudioProvider,  # Legacy
    "unified_google": UnifiedGoogleProvider,  # Explicit unified
    "vertex": VertexAIProvider,  # ADC-based Vertex
    "vertex_ai": VertexAIProvider,  # ADC-based Vertex
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "claude": AnthropicProvider,  # Alias
}

# Auto-detect provider from model name
MODEL_TO_PROVIDER = {
    "gemini": "google",
    "gpt": "openai",
    "claude": "anthropic",
}


def detect_provider_from_model(model_id: str) -> Optional[str]:
    """
    Auto-detect provider from model name.
    
    Args:
        model_id: Model identifier
    
    Returns:
        Provider name or None if can't detect
    """
    if not model_id:
        return None
    
    model_lower = model_id.lower()
    
    for prefix, provider in MODEL_TO_PROVIDER.items():
        if model_lower.startswith(prefix):
            return provider
    
    return None


def create_llm_provider(
    model_id: str,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    Create appropriate LLM provider based on configuration.
    
    Args:
        model_id: Model identifier (e.g., "gemini-2.0-flash-exp", "gpt-4", "claude-3-opus")
        provider: Optional provider name (e.g., "google", "openai", "anthropic")
                 If not provided, auto-detected from model_id or environment
        api_key: Optional API key (can also use environment variables)
        **kwargs: Provider-specific configuration
    
    Returns:
        LLMProvider instance
    
    Raises:
        ValueError: If provider can't be determined or is invalid
        ImportError: If required provider package not installed
    
    Examples:
        # Auto-detect from model name
        provider = create_llm_provider("gemini-2.0-flash-exp")
        
        # Explicit provider
        provider = create_llm_provider("gpt-4", provider="openai")
        
        # With configuration
        provider = create_llm_provider(
            "gemini-2.0-flash-exp",
            provider="vertex_ai",
            project="my-project",
            region="us-central1"
        )
        
        # Custom API key
        provider = create_llm_provider("gpt-4", api_key="sk-...")
    """
    # 1. Try explicit provider
    if provider:
        provider = provider.lower()
        if provider not in PROVIDER_MAP:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Supported providers: {', '.join(PROVIDER_MAP.keys())}"
            )
        provider_class = PROVIDER_MAP[provider]
        return provider_class(model_id=model_id, api_key=api_key, **kwargs)
    
    # 2. Try to detect from model name
    detected_provider = detect_provider_from_model(model_id)
    if detected_provider:
        provider_class = PROVIDER_MAP[detected_provider]
        try:
            return provider_class(model_id=model_id, api_key=api_key, **kwargs)
        except (ImportError, ValueError) as e:
            # Provider detected but not available
            pass
    
    # 3. Try environment variable
    env_provider = os.environ.get("LLM_PROVIDER")
    if env_provider:
        env_provider = env_provider.lower()
        if env_provider in PROVIDER_MAP:
            provider_class = PROVIDER_MAP[env_provider]
            return provider_class(model_id=model_id, api_key=api_key, **kwargs)
    
    # 4. Try each provider in order of preference (based on availability)
    tried_providers = []
    errors = []
    
    # Preference order: Google (most common), OpenAI, Anthropic, Vertex
    for provider_name in ["google", "openai", "anthropic", "vertex_ai"]:
        provider_class = PROVIDER_MAP[provider_name]
        try:
            instance = provider_class(model_id=model_id, api_key=api_key, **kwargs)
            if instance.is_available:
                return instance
        except (ImportError, ValueError) as e:
            tried_providers.append(provider_name)
            errors.append(str(e))
    
    # 5. Failed to create any provider
    error_details = "\n".join([f"  - {p}: {e}" for p, e in zip(tried_providers, errors)])
    raise ValueError(
        f"Could not create LLM provider for model '{model_id}'.\n"
        f"Tried providers:\n{error_details}\n\n"
        f"Solutions:\n"
        f"  1. Set explicit provider: create_llm_provider(model, provider='google')\n"
        f"  2. Set LLM_PROVIDER environment variable\n"
        f"  3. Ensure required package installed (pip install google-genai / openai / anthropic)\n"
        f"  4. Set API key environment variable (GOOGLE_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY)"
    )


# Convenience functions for specific providers

def create_google_provider(model_id: str = "gemini-2.0-flash-exp", **kwargs) -> GoogleAIStudioProvider:
    """Create Google AI Studio provider."""
    return GoogleAIStudioProvider(model_id=model_id, **kwargs)


def create_vertex_provider(model_id: str = "gemini-2.0-flash-exp", **kwargs) -> VertexAIProvider:
    """Create Vertex AI provider."""
    return VertexAIProvider(model_id=model_id, **kwargs)


def create_openai_provider(model_id: str = "gpt-4", **kwargs) -> OpenAIProvider:
    """Create OpenAI provider."""
    return OpenAIProvider(model_id=model_id, **kwargs)


def create_anthropic_provider(model_id: str = "claude-3-sonnet-20240229", **kwargs) -> AnthropicProvider:
    """Create Anthropic provider."""
    return AnthropicProvider(model_id=model_id, **kwargs)
