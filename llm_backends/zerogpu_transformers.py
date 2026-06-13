import os
from collections import Counter

import spaces
import torch
from transformers import AutoModelForCausalLM, AutoProcessor

try:
    from transformers import AutoModelForMultimodalLM
except ImportError:
    AutoModelForMultimodalLM = None

from llm_backends.message_format import normalize_messages
from llm_backends.quantization import build_quantization_config

MODEL_ID = os.getenv(
    "ZERO_GPU_MODEL_ID",
    "google/gemma-4-26B-A4B-it",
)
GPU_DURATION = int(os.getenv("ZERO_GPU_DURATION", "120"))
GPU_SIZE = os.getenv("ZERO_GPU_SIZE", "large").strip().lower()
TOP_P = float(os.getenv("ZERO_GPU_TOP_P", "0.9"))
DIAGNOSTICS_ENABLED = os.getenv("ZERO_GPU_DIAGNOSTICS", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ENABLE_THINKING = os.getenv("ZERO_GPU_ENABLE_THINKING", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _log(message):
    if DIAGNOSTICS_ENABLED:
        print(f"[zerogpu] {message}", flush=True)


def _model_kwargs(token):
    quantization_config = build_quantization_config()
    kwargs = {
        "device_map": "auto",
        "quantization_config": quantization_config,
    }
    if token:
        kwargs["token"] = token
    if kwargs["quantization_config"] is None:
        del kwargs["quantization_config"]
    return kwargs


def _requested_quantization_config():
    return build_quantization_config()


def _load_model():
    if "gguf" in MODEL_ID.lower():
        raise ValueError(
            "ZERO_GPU_MODEL_ID points to a GGUF/llama.cpp model repository. "
            "The ZeroGPU backend uses Transformers, so choose a Transformers-native "
            "model such as google/gemma-4-31B-it or google/gemma-4-26B-A4B-it. "
            "Set LLM_BACKEND=llamacpp for a llama.cpp OpenAI-compatible server."
        )

    token = os.getenv("HF_TOKEN") or None
    processor_kwargs = {"token": token} if token else {}
    _log(
        "loading model "
        f"model_id={MODEL_ID!r} "
        f"quantization={os.getenv('ZERO_GPU_QUANTIZATION', 'bnb_4bit')!r} "
        f"enable_thinking={ENABLE_THINKING} "
        f"gpu_duration={GPU_DURATION} "
        f"gpu_size={GPU_SIZE!r}"
    )

    try:
        processor = AutoProcessor.from_pretrained(MODEL_ID, **processor_kwargs)
        model = _load_auto_model(token)
    except Exception as exc:
        raise RuntimeError(
            f"Could not load ZERO_GPU_MODEL_ID={MODEL_ID!r} with Transformers. "
            "If this is a compressed or AWQ checkpoint, confirm its required "
            "runtime dependencies are installed and set ZERO_GPU_QUANTIZATION=none. "
            f"Original error: {type(exc).__name__}: {exc}"
        ) from exc

    if not getattr(model, "hf_device_map", None):
        model.to("cuda")
    _log_model_diagnostics(model)
    return processor, model


def _load_auto_model(token):
    loaders = [AutoModelForCausalLM]
    if AutoModelForMultimodalLM is not None:
        loaders.append(AutoModelForMultimodalLM)

    errors = []
    for loader in loaders:
        try:
            model = loader.from_pretrained(
                MODEL_ID,
                dtype="auto",
                trust_remote_code=True,
                **_model_kwargs(token),
            )
            _log(f"loaded with {loader.__name__}")
            return model
        except TypeError:
            try:
                model = loader.from_pretrained(
                    MODEL_ID,
                    torch_dtype="auto",
                    trust_remote_code=True,
                    **_model_kwargs(token),
                )
                _log(f"loaded with {loader.__name__} using torch_dtype fallback")
                return model
            except Exception as exc:
                errors.append(exc)
        except Exception as exc:
            errors.append(exc)

    raise ValueError(
        f"Could not load {MODEL_ID!r} with available Transformers auto model classes."
    ) from errors[-1]


def _log_model_diagnostics(model):
    config = getattr(model, "config", None)
    quantization_config = getattr(model, "quantization_config", None)
    hf_device_map = getattr(model, "hf_device_map", None)
    parameter_count = _count_parameters(model)
    parameter_gib = _estimate_parameter_gib(model)

    _log(f"model_class={model.__class__.__name__}")
    if config is not None:
        _log(
            "config "
            f"model_type={getattr(config, 'model_type', None)!r} "
            f"max_position_embeddings={getattr(config, 'max_position_embeddings', None)!r} "
            f"sliding_window={getattr(config, 'sliding_window', None)!r}"
        )
    _log(f"requested_quantization_config={_requested_quantization_config()}")
    _log(f"model_quantization_config={quantization_config}")
    _log(f"is_loaded_in_4bit={getattr(model, 'is_loaded_in_4bit', None)!r}")
    _log(f"is_loaded_in_8bit={getattr(model, 'is_loaded_in_8bit', None)!r}")
    _log(f"bnb_parameter_summary={_bnb_parameter_summary(model)}")
    _log(f"bnb_module_summary={_bnb_module_summary(model)}")
    _log(f"parameter_count={parameter_count:,}")
    _log(f"estimated_parameter_storage_gib={parameter_gib:.2f}")
    if hf_device_map:
        _log(f"device_map_summary={dict(Counter(hf_device_map.values()))}")
        _log(f"device_map_entries={len(hf_device_map)}")
    else:
        _log(f"model_device={getattr(model, 'device', None)!r}")
    _log_gpu_memory("after_load")


def _count_parameters(model):
    return sum(parameter.numel() for parameter in model.parameters())


def _estimate_parameter_gib(model):
    total_bytes = 0
    for parameter in model.parameters():
        try:
            total_bytes += parameter.numel() * parameter.element_size()
        except RuntimeError:
            pass
    return total_bytes / (1024**3)


def _bnb_parameter_summary(model):
    summary = Counter()
    for parameter in model.parameters():
        summary[parameter.__class__.__name__] += 1
    return dict(summary)


def _bnb_module_summary(model):
    summary = Counter()
    for module in model.modules():
        module_name = module.__class__.__name__
        if "4bit" in module_name.lower() or "8bit" in module_name.lower():
            summary[module_name] += 1
    return dict(summary)


def _log_gpu_memory(label):
    if not DIAGNOSTICS_ENABLED:
        return
    if not torch.cuda.is_available():
        _log(f"gpu_memory[{label}]=cuda_unavailable")
        return

    parts = []
    for index in range(torch.cuda.device_count()):
        allocated = torch.cuda.memory_allocated(index) / (1024**3)
        reserved = torch.cuda.memory_reserved(index) / (1024**3)
        try:
            free, total = torch.cuda.mem_get_info(index)
            free_gib = free / (1024**3)
            total_gib = total / (1024**3)
            parts.append(
                f"cuda:{index} allocated={allocated:.2f}GiB "
                f"reserved={reserved:.2f}GiB free={free_gib:.2f}GiB total={total_gib:.2f}GiB"
            )
        except RuntimeError:
            parts.append(
                f"cuda:{index} allocated={allocated:.2f}GiB reserved={reserved:.2f}GiB"
            )
    _log(f"gpu_memory[{label}]: " + " | ".join(parts))


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


@spaces.GPU(duration=GPU_DURATION, size=GPU_SIZE)
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

    _log_gpu_memory("before_generate")
    text = _apply_chat_template(messages)
    inputs = _PROCESSOR(text=text, return_tensors="pt").to(_input_device())
    input_len = inputs["input_ids"].shape[-1]
    _log(
        "generation_request "
        f"input_tokens={input_len} "
        f"max_new_tokens={int(max_tokens)} "
        f"temperature={float(temperature):.3f}"
    )
    outputs = _MODEL.generate(**inputs, **generation_kwargs)
    output_len = outputs[0].shape[-1] - input_len
    _log(f"generation_result output_tokens={output_len}")
    _log_gpu_memory("after_generate")
    response = _PROCESSOR.decode(
        outputs[0][input_len:],
        skip_special_tokens=False,
    )

    return _parse_response(response)


def generate_chat_response(messages, temperature=0.8, max_tokens=800):
    with torch.inference_mode():
        return _generate_on_gpu(messages, temperature, max_tokens)
