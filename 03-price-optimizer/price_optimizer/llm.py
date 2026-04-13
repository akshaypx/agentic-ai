from __future__ import annotations

import os
from typing import Any, Callable, Type

from pydantic import BaseModel

from price_optimizer.env import load_local_env
from price_optimizer.utils import safe_json_loads

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover - dependency is runtime-managed
    ChatGoogleGenerativeAI = None

load_local_env()


def get_llm() -> Any:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is required")
    if ChatGoogleGenerativeAI is None:
        raise RuntimeError(
            "langchain_google_genai is not installed. Add dependencies from requirements.txt."
        )
    return ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        temperature=0.2,
    )


def invoke_structured(
    model_cls: Type[BaseModel],
    prompt: str,
    fallback_factory: Callable[[], BaseModel],
) -> BaseModel:
    try:
        llm = get_llm()
        structured = llm.with_structured_output(model_cls)
        return structured.invoke(prompt)
    except Exception:
        try:
            llm = get_llm()
            response = llm.invoke(prompt)
            return model_cls.model_validate(safe_json_loads(response.content))
        except Exception:
            return fallback_factory()
