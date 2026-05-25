"""
Unified LLM Client for Kimi and DeepSeek APIs.
"""

import os
import requests
from typing import Optional, List, Dict, Any


class LLMClient:
    """Unified client for calling Kimi and DeepSeek APIs."""
    
    def __init__(self, model_key: str):
        from ..config import AVAILABLE_MODELS, get_api_key
        
        self.model_key = model_key
        self.config = AVAILABLE_MODELS.get(model_key, {})
        self.provider = self.config.get("provider", "")
        self.api_base = self.config.get("api_base", "")
        self.model_id = self.config.get("model_id", "")
        self.api_key = get_api_key(self.provider)
    
    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 4096, temperature: float = 0.3) -> str:
        """Send chat request and return response text."""
        if not self.api_key:
            return f"[Error] API key not configured for {self.model_key}"
        
        if self.provider == "kimi":
            return self._call_kimi(messages, max_tokens, temperature)
        elif self.provider == "deepseek":
            return self._call_deepseek(messages, max_tokens, temperature)
        else:
            return f"[Error] Unknown provider: {self.provider}"
    
    def _call_kimi(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float) -> str:
        """Call Kimi API (Anthropic-compatible)."""
        try:
            # Convert OpenAI format to Anthropic format
            anthropic_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    # Anthropic uses system prompt differently
                    continue
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            response = requests.post(
                f"{self.api_base}/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": self.model_id,
                    "max_tokens": max_tokens,
                    "messages": anthropic_messages
                },
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            
            for block in data.get("content", []):
                if block.get("type") == "text":
                    return block.get("text", "")
            return "无回复"
            
        except Exception as e:
            return f"[Error] Kimi API call failed: {str(e)}"
    
    def _call_deepseek(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float) -> str:
        """Call DeepSeek API (OpenAI-compatible)."""
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model_id,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                },
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            
            return data.get("choices", [{}])[0].get("message", {}).get("content", "无回复")
            
        except Exception as e:
            return f"[Error] DeepSeek API call failed: {str(e)}"


if __name__ == "__main__":
    # Test
    client = LLMClient("deepseek-v4-flash")
    result = client.chat([{"role": "user", "content": "Hello, what is 2+2?"}])
    print(f"Result: {result}")
