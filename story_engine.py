import json
import re
from typing import Literal
from pydantic import BaseModel, Field

from llm_client import generate_chat_response
from prompts import SYSTEM_PROMPT, SCENE_JSON_INSTRUCTIONS


class Choice(BaseModel):
    id: Literal["A", "B", "C"]
    label: str
    tone: str
    preview: str


class SceneResponse(BaseModel):
    scene: str
    choices: list[Choice] = Field(min_length=3, max_length=3)
    memory_update: str


def extract_json(text: str) -> dict:
    """
    Tries to recover JSON even if the model accidentally adds extra text.
    """
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model output:\n{text}")

    return json.loads(match.group(0))


def create_initial_state(premise: str) -> dict:
    return {
        "premise": premise,
        "active_branch": "main",
        "branches": {
            "main": {
                "title": "The first road",
                "summary": "The story has just begun.",
                "recent_scene": "",
                "chosen_decisions": [],
                "last_choices": [],
            }
        },
    }


def generate_scene(state: dict, selected_choice: str | None = None) -> tuple[dict, SceneResponse]:
    active_branch_id = state["active_branch"]
    branch = state["branches"][active_branch_id]

    user_prompt = f"""
Premise:
{state["premise"]}

Current branch:
{active_branch_id}

Branch summary:
{branch["summary"]}

Recent scene:
{branch["recent_scene"]}

Chosen decisions:
{branch["chosen_decisions"]}

Selected choice:
{selected_choice or "The story is starting."}

Task:
Continue this branch only. Then provide exactly 3 new choices.

{SCENE_JSON_INSTRUCTIONS}
"""

    raw = generate_chat_response(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=900,
    )

    parsed = extract_json(raw)
    scene_response = SceneResponse.model_validate(parsed)

    branch["recent_scene"] = scene_response.scene
    branch["summary"] = scene_response.memory_update
    branch["last_choices"] = [choice.model_dump() for choice in scene_response.choices]

    if selected_choice:
        branch["chosen_decisions"].append(selected_choice)

    return state, scene_response


def format_scene_for_ui(scene_response: SceneResponse) -> str:
    choices_md = "\n".join(
        [
            f"**{choice.id}. {choice.label}**  \n"
            f"*Tone:* {choice.tone}  \n"
            f"*Preview:* {choice.preview}"
            for choice in scene_response.choices
        ]
    )

    return f"""
{scene_response.scene}

---

## Choices

{choices_md}
"""