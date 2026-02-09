"""LLM Client – direct integration with Google Gemini API for reasoning."""

import json
import os
from typing import Any

try:
    # Try new google-genai package first
    from google import genai
    GEMINI_AVAILABLE = True
    USE_NEW_API = True
except ImportError:
    # Fallback to deprecated package if new one not available
    try:
        import google.generativeai as genai
        GEMINI_AVAILABLE = True
        USE_NEW_API = False
    except ImportError:
        GEMINI_AVAILABLE = False
        USE_NEW_API = False


class LLMClient:
    """
    Client for Google Gemini LLM API.
    
    Provides structured reasoning capabilities for agents.
    """

    # Default model when "auto" is selected (balanced speed vs quality)
    AUTO_MODEL_DEFAULT = "gemini-2.5-flash"

    def __init__(self, model_id: str = "gemini-2.5-flash"):
        """
        Initialize LLM client.
        
        Args:
            model_id: Model identifier (e.g. "gemini-2.0-flash-exp", "gemini-1.5-flash"). Use "auto" to let the client pick a balanced default.
        
        Raises:
            ImportError: If google-genai not installed
        """
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-genai not installed. Install with: pip install google-genai\n"
                "Or use deprecated package: pip install google-generativeai"
            )
        
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable not set. "
                "Set it with: export GOOGLE_API_KEY=your_key"
            )
        
        # Resolve "auto" to a concrete model (best default for general work)
        if model_id and model_id.strip().lower() == "auto":
            model_id = self.AUTO_MODEL_DEFAULT
        
        # Configure API key
        if USE_NEW_API:
            # New google-genai API
            self.client = genai.Client(api_key=api_key)
            self.model_id = model_id
            self.model = None
            self._use_new_api = True
        else:
            # Deprecated google.generativeai API
            genai.configure(api_key=api_key)
            self.model_id = model_id
            self.model = genai.GenerativeModel(model_id)
            self.client = None
            self._use_new_api = False

    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text using LLM.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
        
        Returns:
            Generated text
        """
        if hasattr(self, '_use_new_api') and self._use_new_api and self.client:
            # New google-genai API
            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt
                )
                # Extract text from response
                if hasattr(response, 'text'):
                    return response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    # Fallback for different response structures
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        return candidate.content.parts[0].text
                    elif hasattr(candidate, 'text'):
                        return candidate.text
                # Last resort: convert to string
                return str(response)
            except Exception as e:
                raise RuntimeError(f"LLM generation failed: {e}")
        else:
            # Deprecated google.generativeai API
            response = self.model.generate_content(prompt, **kwargs)
            return response.text

    def reason(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        require_json: bool = True,
    ) -> dict[str, Any]:
        """
        Structured reasoning with decision, confidence, evidence.
        
        Args:
            prompt: Reasoning prompt
            context: Optional context dict
            require_json: Whether to require JSON response format
        
        Returns:
            Dict with "decision", "confidence", "evidence" keys
        """
        # Build full prompt
        full_prompt = prompt
        if context:
            full_prompt += f"\n\nContext: {json.dumps(context, indent=2)}"
        
        if require_json:
            full_prompt += "\n\nRespond in JSON format with keys: decision (string), confidence (float 0-1), evidence (array of strings)."
        
        # Generate response
        response_text = self.generate(full_prompt)
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            text = response_text.strip()
            if text.startswith("```"):
                # Extract JSON from code block
                parts = text.split("```")
                for part in parts:
                    if part.strip().startswith("json"):
                        text = part[4:].strip()
                    elif part.strip().startswith("{"):
                        text = part.strip()
                        break
            elif text.startswith("{"):
                text = text
            
            result = json.loads(text)
            
            # Ensure required keys
            if "decision" not in result:
                result["decision"] = "unknown"
            if "confidence" not in result:
                result["confidence"] = 0.5
            if "evidence" not in result:
                result["evidence"] = []
            
            return result
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "decision": "unable_to_parse",
                "confidence": 0.0,
                "evidence": [f"Failed to parse LLM response: {response_text[:200]}"]
            }

    def explain(self, prompt: str, context: dict[str, Any] | None = None) -> str:
        """
        Generate human-readable explanation.
        
        Args:
            prompt: Explanation prompt
            context: Optional context dict
        
        Returns:
            Human-readable explanation text
        """
        full_prompt = prompt
        if context:
            full_prompt += f"\n\nContext: {json.dumps(context, indent=2)}"
        
        return self.generate(full_prompt)
