"""OpenAI Provider - Using openai package."""

import json
import os
from typing import Any, Dict, Optional

from .base import LLMProvider, LLMResponse

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIProvider(LLMProvider):
    """
    OpenAI provider supporting GPT models.
    
    Environment variables:
        OPENAI_API_KEY: OpenAI API key
        OPENAI_BASE_URL: Optional custom base URL (for Azure OpenAI, proxies, etc.)
        OPENAI_ORG_ID: Optional organization ID
    
    Model examples:
        - gpt-4
        - gpt-4-turbo
        - gpt-3.5-turbo
        - gpt-4o
    """
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(model_id, api_key, **kwargs)
        
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai not installed. Install with: pip install openai"
            )
        
        # Get API key
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Initialize client
        client_kwargs = {"api_key": self.api_key}
        
        # Support custom base URL (for Azure OpenAI or proxies)
        base_url = kwargs.get("base_url") or os.environ.get("OPENAI_BASE_URL")
        if base_url:
            client_kwargs["base_url"] = base_url
        
        # Support organization ID
        org_id = kwargs.get("organization") or os.environ.get("OPENAI_ORG_ID")
        if org_id:
            client_kwargs["organization"] = org_id
        
        self.client = openai.OpenAI(**client_kwargs)
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """Generate text using OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            
            message = response.choices[0].message
            
            return LLMResponse(
                text=message.content,
                model=response.model,
                provider="openai",
                finish_reason=response.choices[0].finish_reason,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                raw_response=response
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI generation failed: {e}")
    
    def generate_with_json(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate structured JSON response."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            
            text = response.choices[0].message.content
            return json.loads(text)
        except Exception as e:
            # Fallback to regular generation
            response = self.generate(prompt + "\n\nRespond with valid JSON only.", context)
            text = response.text.strip()
            
            # Clean up markdown code blocks
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            return json.loads(text)
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    @property
    def is_available(self) -> bool:
        return OPENAI_AVAILABLE and bool(self.api_key)
