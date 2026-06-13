import importlib
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

BACKEND_MODULES = {
    "llamacpp": "llm_backends.openai_compatible",
    "openai": "llm_backends.openai_compatible",
    "zerogpu": "llm_backends.zerogpu_transformers",
}


def resolve_backend_name(value: str | None = None) -> str:
    backend = (value or os.getenv("LLM_BACKEND") or "").strip().lower()
    if not backend:
        backend = "zerogpu" if _is_hugging_face_space() else "llamacpp"

    if backend not in BACKEND_MODULES:
        allowed = ", ".join(sorted(BACKEND_MODULES))
        raise ValueError(f"Unsupported LLM_BACKEND={backend!r}. Expected one of: {allowed}")

    return backend


def _is_hugging_face_space() -> bool:
    return bool(
        os.getenv("SPACE_ID")
        or os.getenv("SPACE_HOST")
        or os.getenv("SPACE_REPO_NAME")
        or os.getenv("HF_SPACE_ID")
    )


@lru_cache(maxsize=1)
def _load_backend():
    backend_name = resolve_backend_name()
    return importlib.import_module(BACKEND_MODULES[backend_name])


def generate_chat_response(messages, temperature=0.8, max_tokens=800):
    backend = _load_backend()
    return backend.generate_chat_response(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )


if resolve_backend_name() == "zerogpu":
    _load_backend()
