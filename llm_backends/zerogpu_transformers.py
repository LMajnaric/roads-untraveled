import os

import spaces
import torch
from transformers import AutoModelForCausalLM, AutoProcessor

try:
    from transformers import AutoModelForMultimodalLM
except ImportError:
    AutoModelForMultimodalLM = None

from llm_backends.message_format import normalize_messages

MODEL_ID = os.getenv(
    "ZERO_GPU_MODEL_ID",
    "LilaRest/gemma-4-31B-it-NVFP4-turbo",
)
GPU_DURATION = int(os.getenv("ZERO_GPU_DURATION", "120"))
TOP_P = float(os.getenv("ZERO_GPU_TOP_P", "0.9"))
ENABLE_THINKING = os.getenv("ZERO_GPU_ENABLE_THINKING", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _model_kwargs(token):
    kwargs = {
        "device_map": "auto",
    }
    if token:
        kwargs["token"] = token
    return kwargs


def _load_model():
    if "gguf" in MODEL_ID.lower():
        raise ValueError(
            "ZERO_GPU_MODEL_ID points to a GGUF/llama.cpp model repository. "
            "The ZeroGPU backend uses Transformers, so choose a Transformers-native "
            "model such as LilaRest/gemma-4-31B-it-NVFP4-turbo, "
            "google/gemma-4-31B-it, or google/gemma-4-26B-A4B-it. "
            "Set LLM_BACKEND=llamacpp for a llama.cpp OpenAI-compatible server."
        )

    token = os.getenv("HF_TOKEN") or None
    processor_kwargs = {"token": token} if token else {}

    try:
        processor = AutoProcessor.from_pretrained(MODEL_ID, **processor_kwargs)
        model = _load_auto_model(token)
    except ValueError as exc:
        raise ValueError(
            f"Could not load ZERO_GPU_MODEL_ID={MODEL_ID!r} with Transformers. "
            "Use a Transformers-native model repository for LLM_BACKEND=zerogpu. "
            "GGUF repositories are for llama.cpp, not this ZeroGPU backend."
        ) from exc

    if not getattr(model, "hf_device_map", None):
        model.to("cuda")
    return processor, model


def _load_auto_model(token):
    loaders = [AutoModelForCausalLM]
    if AutoModelForMultimodalLM is not None:
        loaders.append(AutoModelForMultimodalLM)

    errors = []
    for loader in loaders:
        try:
            return loader.from_pretrained(
                MODEL_ID,
                dtype="auto",
                trust_remote_code=True,
                **_model_kwargs(token),
            )
        except TypeError:
            try:
                return loader.from_pretrained(
                    MODEL_ID,
                    torch_dtype="auto",
                    trust_remote_code=True,
                    **_model_kwargs(token),
                )
            except Exception as exc:
                errors.append(exc)
        except Exception as exc:
            errors.append(exc)

    raise ValueError(
        f"Could not load {MODEL_ID!r} with available Transformers auto model classes."
    ) from errors[-1]


_PROCESSOR, _MODEL = _load_model()


def _input_device():
    device = getattr(_MODEL, "device", None)
    if device is not None:
        return device
    return next(_MODEL.parameters()).device


def _apply_chat_template(messages):
    normalized = normalize_messages(messages)
    try:
        return _PROCESSOR.apply_chat_template(
            normalized,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=ENABLE_THINKING,
        )
    except TypeError:
        return _PROCESSOR.apply_chat_template(
            normalized,
            tokenize=False,
            add_generation_prompt=True,
        )


def _parse_response(text):
    if hasattr(_PROCESSOR, "parse_response"):
        parsed = _PROCESSOR.parse_response(text)
        if isinstance(parsed, str):
            return parsed.strip()
        if isinstance(parsed, dict):
            for key in ("answer", "content", "response", "text"):
                if key in parsed:
                    return str(parsed[key]).strip()
        return str(parsed).strip()
    return text.strip()


@spaces.GPU(duration=GPU_DURATION)
def _generate_on_gpu(messages, temperature, max_tokens):
    generation_kwargs = {
        "max_new_tokens": int(max_tokens),
        "do_sample": float(temperature) > 0,
        "temperature": max(float(temperature), 0.01),
        "top_p": TOP_P,
    }

    tokenizer = getattr(_PROCESSOR, "tokenizer", None)
    if tokenizer is not None and getattr(tokenizer, "eos_token_id", None) is not None:
        generation_kwargs["pad_token_id"] = tokenizer.eos_token_id

    text = _apply_chat_template(messages)
    inputs = _PROCESSOR(text=text, return_tensors="pt").to(_input_device())
    input_len = inputs["input_ids"].shape[-1]
    outputs = _MODEL.generate(**inputs, **generation_kwargs)
    response = _PROCESSOR.decode(
        outputs[0][input_len:],
        skip_special_tokens=False,
    )

    return _parse_response(response)


def generate_chat_response(messages, temperature=0.8, max_tokens=800):
    with torch.inference_mode():
        return _generate_on_gpu(messages, temperature, max_tokens)
