"""Anthropic Provider - Using anthropic package for Claude models."""

import json
import os
from typing import Any, Dict, Optional

from .base import LLMProvider, LLMResponse

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicProvider(LLMProvider):
    """
    Anthropic provider supporting Claude models.
    
    Environment variables:
        ANTHROPIC_API_KEY: Anthropic API key
    
    Model examples:
        - claude-3-opus-20240229
        - claude-3-sonnet-20240229
        - claude-3-haiku-20240307
    """
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(model_id, api_key, **kwargs)
        
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic not installed. Install with: pip install anthropic"
            )
        
        # Get API key
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Initialize client
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.max_tokens = kwargs.get("max_tokens", 1024)
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """Generate text using Anthropic Claude."""
        try:
            response = self.client.messages.create(
                model=self.model_id,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            
            text = response.content[0].text
            
            return LLMResponse(
                text=text,
                model=response.model,
                provider="anthropic",
                finish_reason=response.stop_reason,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                raw_response=response
            )
        except Exception as e:
            raise RuntimeError(f"Anthropic generation failed: {e}")
    
    def generate_with_json(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate structured JSON response."""
        json_prompt = f"""{prompt}

IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanations, just JSON."""
        
        response = self.generate(json_prompt, context)
        text = response.text.strip()
        
        # Clean up markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Could not parse JSON response: {e}\nResponse: {text[:200]}")
    
    @property
    def provider_name(self) -> str:
        return "anthropic"
    
    @property
    def is_available(self) -> bool:
        return ANTHROPIC_AVAILABLE and bool(self.api_key)
