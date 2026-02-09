"""Google AI Studio Provider - Using google-genai package."""

import json
import os
from typing import Any, Dict, Optional

from .base import LLMProvider, LLMResponse

try:
    from google import genai
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai
        GOOGLE_GENAI_AVAILABLE = True
    except ImportError:
        GOOGLE_GENAI_AVAILABLE = False


class GoogleAIStudioProvider(LLMProvider):
    """
    Google AI Studio provider using google-genai package.
    
    Environment variables:
        GOOGLE_API_KEY: API key from Google AI Studio
    
    Model examples:
        - gemini-2.0-flash-exp
        - gemini-1.5-flash
        - gemini-1.5-pro
    """
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(model_id, api_key, **kwargs)
        
        if not GOOGLE_GENAI_AVAILABLE:
            raise ImportError(
                "google-genai not installed. Install with: pip install google-genai"
            )
        
        # Get API key
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Initialize client
        try:
            self.client = genai.Client(api_key=self.api_key)
        except AttributeError:
            # Old API
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_id)
            self.client = None
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """Generate text using Google AI Studio."""
        try:
            if self.client:
                # New API
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt
                )
                text = response.text
                raw = response
            else:
                # Old API
                response = self.model.generate_content(prompt)
                text = response.text
                raw = response
            
            return LLMResponse(
                text=text,
                model=self.model_id,
                provider="google_ai_studio",
                raw_response=raw
            )
        except Exception as e:
            raise RuntimeError(f"Google AI Studio generation failed: {e}")
    
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
            # Fallback: try to extract JSON from text
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            raise ValueError(f"Could not parse JSON response: {e}\nResponse: {text[:200]}")
    
    @property
    def provider_name(self) -> str:
        return "google_ai_studio"
    
    @property
    def is_available(self) -> bool:
        return GOOGLE_GENAI_AVAILABLE and bool(self.api_key)
