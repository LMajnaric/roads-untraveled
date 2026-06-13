import os

SUPPORTED_QUANTIZATIONS = {"none", "bnb_4bit", "bnb_8bit"}


def resolve_quantization(value: str | None = None) -> str:
    quantization = (value or os.getenv("ZERO_GPU_QUANTIZATION") or "bnb_4bit").strip().lower()
    if quantization not in SUPPORTED_QUANTIZATIONS:
        allowed = ", ".join(sorted(SUPPORTED_QUANTIZATIONS))
        raise ValueError(
            f"Unsupported ZERO_GPU_QUANTIZATION={quantization!r}. "
            f"Expected one of: {allowed}"
        )
    return quantization


def build_quantization_config(value: str | None = None):
    quantization = resolve_quantization(value)
    if quantization == "none":
        return None

    if quantization == "bnb_8bit":
        return _bitsandbytes_config(load_in_8bit=True)

    return _bitsandbytes_config(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=_bfloat16(),
        bnb_4bit_use_double_quant=True,
    )


def _bitsandbytes_config(**kwargs):
    from transformers import BitsAndBytesConfig

    return BitsAndBytesConfig(**kwargs)


def _bfloat16():
    import torch

    return torch.bfloat16
