import json
import re
from typing import Literal
from pydantic import BaseModel, Field, ValidationError
from llm_client import generate_chat_response
from prompts import SYSTEM_PROMPT, SCENE_JSON_INSTRUCTIONS


class Choice(BaseModel):
    id: Literal["A", "B", "C"]
    label: str
    tone: str
    preview: str


class SceneResponse(BaseModel):
    time_jump: str
    scene: str
    choices: list[Choice] = Field(min_length=3, max_length=3)
    memory_update: str


def extract_json(text: str) -> dict:
    """
    Extracts the first likely JSON object from model output.
    Raises ValueError if parsing fails.
    """
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in model output:\n{text}")

    candidate = text[start:end + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON from model:\n\n{candidate}\n\nJSON error:\n{e}"
        )


def repair_json_with_model(broken_text: str, error_message: str = "") -> dict:
    """
    Asks the model to repair malformed or incomplete JSON.
    """
    repair_prompt = f"""
The following text was supposed to be valid JSON, but it failed to parse or validate.

Repair it into valid JSON.

Required JSON structure:

{{
  "time_jump": "A clear time jump, such as Six months later or Two years later.",
  "scene": "The next story scene. Maximum 140 words.",
  "choices": [
    {{
      "id": "A",
      "label": "Short choice label",
      "tone": "emotional tone",
      "preview": "One short sentence."
    }},
    {{
      "id": "B",
      "label": "Short choice label",
      "tone": "emotional tone",
      "preview": "One short sentence."
    }},
    {{
      "id": "C",
      "label": "Short choice label",
      "tone": "emotional tone",
      "preview": "One short sentence."
    }}
  ],
  "memory_update": "One concise sentence summarizing what changed in this branch."
}}

Rules:
- Return only valid JSON.
- Do not add markdown.
- Do not add explanation.
- Preserve the meaning when possible.
- If the text was cut off, complete the missing fields yourself.
- The choices array must contain exactly A, B, and C.
- The JSON must include time_jump, scene, choices, and memory_update.

Validation error:
{error_message}

Broken text:
{broken_text}
"""

    repaired = generate_chat_response(
        messages=[
            {
                "role": "system",
                "content": "You repair malformed JSON. Return valid JSON only.",
            },
            {
                "role": "user",
                "content": repair_prompt,
            },
        ],
        temperature=0.1,
        max_tokens=1000,
    )

    return extract_json(repaired)

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
                "step": 0,
            }
        },
    }


def get_scene_markdown(scene_response: SceneResponse) -> str:
    return f"""
### {scene_response.time_jump}

{scene_response.scene}
"""


def generate_scene(state: dict, selected_choice: str | None = None) -> tuple[dict, SceneResponse]:
    active_branch_id = state["active_branch"]
    branch = state["branches"][active_branch_id]
    step = branch.get("step", 0)

    user_prompt = f"""
Story step:
{step}

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

Forbidden choice types:
- Do not offer a choice to undo the selected choice.
- Do not offer a choice to go back to the exact earlier decision.
- Do not offer tiny tactical choices like call, text, sleep, wait, or walk away unless they permanently reshape the life path.
- Each choice must move the protagonist into a different future.

Time jump instruction:
If step is 0, begin near the first major decision.
If step is 1, jump weeks or months forward.
If step is 2, jump months or 1 year forward.
If step is 3, jump 1 to 3 years forward.
If step is 4 or higher, jump several years forward and move toward an ending.
Never continue minute-by-minute or day-by-day unless the premise absolutely requires it.

{SCENE_JSON_INSTRUCTIONS}
"""

    raw = generate_chat_response(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.75,
        max_tokens=900,
    )

    try:
        parsed = extract_json(raw)
        scene_response = SceneResponse.model_validate(parsed)

    except (ValueError, ValidationError) as e:
        print("\n--- RAW MODEL OUTPUT FAILED JSON PARSING OR VALIDATION ---")
        print(raw)
        print("\n--- ERROR ---")
        print(e)
        print("--- END RAW MODEL OUTPUT ---\n")

        parsed = repair_json_with_model(raw, error_message=str(e))
        scene_response = SceneResponse.model_validate(parsed)

    scene_response = SceneResponse.model_validate(parsed)

    branch["recent_scene"] = scene_response.scene
    branch["summary"] = scene_response.memory_update
    branch["last_choices"] = [choice.model_dump() for choice in scene_response.choices]
    branch["step"] = step + 1

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