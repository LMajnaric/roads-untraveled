import os

import spaces
import torch
from transformers import pipeline

from llm_backends.message_format import extract_generated_text, messages_to_prompt, normalize_messages

MODEL_ID = os.getenv(
    "ZERO_GPU_MODEL_ID",
    "google/gemma-4-31B-it-qat-q4_0-gguf",
)
TASK = os.getenv("ZERO_GPU_TASK", "text-generation")
GPU_DURATION = int(os.getenv("ZERO_GPU_DURATION", "120"))
TOP_P = float(os.getenv("ZERO_GPU_TOP_P", "0.9"))


def _make_generator():
    token = os.getenv("HF_TOKEN") or None
    kwargs = {
        "model": MODEL_ID,
        "torch_dtype": "auto",
        "device_map": "auto",
    }
    if token:
        kwargs["token"] = token

    generator = pipeline(TASK, **kwargs)
    model = getattr(generator, "model", None)
    if model is not None and not getattr(model, "hf_device_map", None):
        model.to("cuda")
    return generator


_GENERATOR = _make_generator()


@spaces.GPU(duration=GPU_DURATION)
def _generate_on_gpu(messages, temperature, max_tokens):
    generation_kwargs = {
        "max_new_tokens": int(max_tokens),
        "do_sample": float(temperature) > 0,
        "temperature": max(float(temperature), 0.01),
        "top_p": TOP_P,
    }

    if TASK == "image-text-to-text":
        result = _GENERATOR(text=normalize_messages(messages), **generation_kwargs)
    else:
        prompt = messages_to_prompt(messages, tokenizer=getattr(_GENERATOR, "tokenizer", None))
        result = _GENERATOR(prompt, return_full_text=False, **generation_kwargs)

    return extract_generated_text(result)


def generate_chat_response(messages, temperature=0.8, max_tokens=800):
    with torch.inference_mode():
        return _generate_on_gpu(messages, temperature, max_tokens)
