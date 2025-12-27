import os
from typing import List, Dict, Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


class BaseLLMClient:
    def chat_completion(self, messages: List[Dict], model: str, temperature: float = 0.2, **kwargs) -> str:
        raise NotImplementedError()


class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        if OpenAI is None:
            raise RuntimeError("openai package not available")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OpenAI API key not configured")
        self.client = OpenAI(api_key=self.api_key)

    def chat_completion(self, messages: List[Dict], model: str, temperature: float = 0.2, **kwargs) -> str:
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            **kwargs,
        )
        return completion.choices[0].message.content or ""


class NoopClient(BaseLLMClient):
    def chat_completion(self, messages: List[Dict], model: str, temperature: float = 0.2, **kwargs) -> str:
        joined = "\n\n".join([m.get("content", "") for m in messages])
        return f"(No LLM configured) Echo of prompt:\n{joined}"


def get_llm_client(provider: Optional[str] = None, api_key: Optional[str] = None) -> BaseLLMClient:
    provider = (provider or os.getenv("LLM_PROVIDER") or "openai").lower()
    if provider == "openai":
        try:
            return OpenAIClient(api_key=api_key)
        except Exception:
            return NoopClient()
    return NoopClient()
