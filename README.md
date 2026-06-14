---
title: Roads Untraveled
emoji: 🛤️
colorFrom: gray
colorTo: indigo
sdk: gradio
app_file: app.py
license: gpl-3.0
achievement: offgrid, llama
track: backyard
---

# Roads Untraveled

Explore lives you did not live using the power of small LLMs.

Roads Untraveled is a short interactive fiction experiment for the Hugging Face
build small hackathon. The user enters a major crossroads moment in their life, 
chooses one of three major "roads", and follows that life through a handful of irreversible decisions. 
At the end, the app compares the life they lived with two miniature lives 
simulated from the initial roads not taken.
It is also encouraged to ask each of the unchosen roads a question!

## How to run locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Start an OpenAI-compatible local or remote inference server, then configure:

```bash
LLM_BACKEND=llamacpp
LLM_BASE_URL=http://127.0.0.1:8080/v1
LLM_API_KEY=not-needed
LLM_MODEL=your-model-name
```

An example of my server command:
```bash
llama-server `
   -m "C:\path\to\gemma-4-31B_q4_0-it.gguf" `
   -ngl all `
   -c 16384 `
   -fa auto `
   -ctk f16 `
   -ctv f16 `
   --host 127.0.0.1 `
   --port 8080 `
   --chat-template-kwargs '{\"enable_thinking\":false}'
```

Run the Gradio app:

```bash
python app.py
```

Note: I've only tested this on the dev branch, the code and GUI was transformed for the HF Space. 

## Hugging Face Space

The submission target is a public Gradio Hugging Face Space using ZeroGPU. Set
the Space hardware to ZeroGPU and configure these Space variables:

```bash
LLM_BACKEND=zerogpu
ZERO_GPU_MODEL_ID=google/gemma-4-26B-A4B-it
ZERO_GPU_QUANTIZATION=bnb_4bit
ZERO_GPU_ENABLE_THINKING=false
ZERO_GPU_SIZE=large
```

ZeroGPU uses the in-process Transformers backend, so `ZERO_GPU_MODEL_ID` must be
a Transformers-native model repository. GGUF repositories such as
`google/gemma-4-31B-it-qat-q4_0-gguf` (absolutely recommended for 24GB VRAM) are for llama.cpp and should be used with
`LLM_BACKEND=llamacpp`, not the ZeroGPU backend. The current Space experiment
uses official Gemma 4 26B-A4B with bitsandbytes NF4 quantization. For an
already-quantized AWQ INT4 checkpoint, try
`ZERO_GPU_MODEL_ID=cyankiwi/gemma-4-26B-A4B-it-qat-AWQ-INT4` with
`ZERO_GPU_QUANTIZATION=none`. Add `HF_TOKEN` as a Space secret if the selected
model requires authenticated download or license acceptance.

Every model used for the hackathon submission should stay under the 32B total
parameter limit. The app can still point at an OpenAI-compatible backend by
setting `LLM_BACKEND=llamacpp`.

## Submission links

- Hugging Face Space: https://huggingface.co/spaces/build-small-hackathon/roads-untraveled
- Demo video: TODO
- Social post: TODO
- Public GitHub repo: https://github.com/LMajnaric/roads-untraveled

## Notes

- Main track target: Thousand Token Wood / overall app quality, but a story generator might be more of a Backyard-style app.
- Sponsor prize target: none by default.
- Full visual story map: MVP.
