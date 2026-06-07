import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080/v1"),
    api_key=os.getenv("LLM_API_KEY", "not-needed"),
)

MODEL = os.getenv("LLM_MODEL", "gemma-4-local")


def generate_chat_response(messages, temperature=0.8, max_tokens=800):
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
        top_p=0.9,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content