"""Base LLM Provider Interface - Abstract class for all LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standardized LLM response across all providers."""
    text: str
    model: str
    provider: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All LLM providers (Google, OpenAI, Anthropic, etc.) must implement this interface.
    This ensures agents work regardless of which LLM backend is used.
    """
    
    def __init__(self, model_id: str, api_key: Optional[str] = None, **kwargs):
        """
        Initialize LLM provider.
        
        Args:
            model_id: Model identifier (e.g., "gemini-2.0-flash-exp", "gpt-4", "claude-3-opus")
            api_key: Optional API key (can also use environment variables)
            **kwargs: Provider-specific configuration
        """
        self.model_id = model_id
        self.api_key = api_key
        self.config = kwargs
    
    @abstractmethod
    def generate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Text prompt
            context: Optional context dictionary
        
        Returns:
            LLMResponse with generated text
        """
        pass
    
    @abstractmethod
    def generate_with_json(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate structured JSON response.
        
        Args:
            prompt: Text prompt (should request JSON output)
            context: Optional context dictionary
        
        Returns:
            Parsed JSON dictionary
        """
        pass
    
    def reason(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate structured reasoning (decision, confidence, evidence).
        
        Default implementation uses generate_with_json.
        Override for provider-specific reasoning modes.
        
        Args:
            prompt: Reasoning prompt
            context: Optional context dictionary
        
        Returns:
            Dict with decision, confidence, evidence
        """
        reasoning_prompt = f"""{prompt}

Respond ONLY with valid JSON in this format:
{{
  "decision": "your decision here",
  "confidence": 0.0 to 1.0,
  "evidence": ["reasoning point 1", "reasoning point 2", ...]
}}"""
        
        result = self.generate_with_json(reasoning_prompt, context)
        
        # Ensure required fields
        if "decision" not in result:
            result["decision"] = "unknown"
        if "confidence" not in result:
            result["confidence"] = 0.5
        if "evidence" not in result:
            result["evidence"] = []
        
        return result
    
    def explain(self, question: str) -> str:
        """
        Generate a simple explanation.
        
        Args:
            question: Question or topic to explain
        
        Returns:
            Explanation text
        """
        prompt = f"Explain concisely: {question}"
        response = self.generate(prompt)
        return response.text
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name (e.g., 'google', 'openai', 'anthropic')."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available (credentials, package installed, etc.)."""
        pass
