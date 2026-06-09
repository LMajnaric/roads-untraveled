# Roads Untraveled

Explore lives you did not live with a local or remote LLM behind a Gradio app.

Roads Untraveled is a short interactive fiction experiment for the Hugging Face
hackathon. The user enters a life premise, chooses one of three major roads, and
then follows that life through a handful of irreversible decisions. At the end,
the app compares the life they lived with two miniature lives simulated from the
initial roads not taken.

## Running locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Start an OpenAI-compatible local or remote inference server, then configure:

```bash
LLM_BASE_URL=http://127.0.0.1:8080/v1
LLM_API_KEY=not-needed
LLM_MODEL=your-model-name
```

Run the Gradio app:

```bash
python app.py
```

## Hugging Face Space plan

The submission target is a Gradio Hugging Face Space. The Space can use the same
OpenAI-compatible client in `llm_client.py`, with `LLM_BASE_URL` pointing at a
remote 4090-backed inference endpoint for the demo.

Every model used for the hackathon submission should stay under the 32B total
parameter limit. The current app is model-agnostic and can point at any eligible
OpenAI-compatible backend.

## Submission links

- Hugging Face Space: TODO
- Demo video: TODO
- Social post: TODO
- Public GitHub repo: TODO

## Notes

- Main track target: Thousand Token Wood / overall app quality.
- Sponsor prize target: none by default.
- Full visual story map: future feature.
