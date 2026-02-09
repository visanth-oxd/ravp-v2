"""Vertex AI Provider - Using Google Cloud Vertex AI."""

import json
import os
from typing import Any, Dict, Optional

from .base import LLMProvider, LLMResponse

try:
    from vertexai.generative_models import GenerativeModel
    import vertexai
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False


class VertexAIProvider(LLMProvider):
    """
    Google Vertex AI provider.
    
    Environment variables:
        GOOGLE_CLOUD_PROJECT: GCP project ID
        GOOGLE_CLOUD_REGION: GCP region (default: us-central1)
    
    Authentication:
        Uses Application Default Credentials (ADC):
        - gcloud auth application-default login
        - Or service account key via GOOGLE_APPLICATION_CREDENTIALS
    
    Model examples:
        - gemini-2.0-flash-exp
        - gemini-1.5-flash
        - gemini-1.5-pro
    """
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs):
        super().__init__(model_id, api_key, **kwargs)
        
        if not VERTEX_AI_AVAILABLE:
            raise ImportError(
                "vertexai not installed. Install with: pip install google-cloud-aiplatform"
            )
        
        # Get project and region
        self.project_id = kwargs.get("project") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.region = kwargs.get("region") or os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
        
        if not self.project_id:
            raise ValueError(
                "GCP project required. Set GOOGLE_CLOUD_PROJECT environment variable "
                "or pass project parameter."
            )
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.region)
        self.model = GenerativeModel(model_id)
    
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """Generate text using Vertex AI."""
        try:
            response = self.model.generate_content(prompt)
            
            return LLMResponse(
                text=response.text,
                model=self.model_id,
                provider="vertex_ai",
                raw_response=response
            )
        except Exception as e:
            raise RuntimeError(f"Vertex AI generation failed: {e}")
    
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
        return "vertex_ai"
    
    @property
    def is_available(self) -> bool:
        return VERTEX_AI_AVAILABLE and bool(self.project_id)
