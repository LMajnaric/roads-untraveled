import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from llm_client import generate_chat_response
from prompts import ENDING_JSON_INSTRUCTIONS, SCENE_JSON_INSTRUCTIONS, SYSTEM_PROMPT


StoryMode = Literal["grounded", "strange", "cinematic"]

DEFAULT_MAX_STEPS = 6
MIN_STEPS = 5
MAX_STEPS = 7

DRAMATIC_BEATS = [
    "opening fork: three lives that cannot all be lived",
    "first consequence: show what the chosen road immediately gives and takes",
    "complication: introduce a cost, delay, rival desire, or fragile opportunity",
    "reversal: something once reassuring becomes unstable, or vice versa",
    "sacrifice: force a meaningful tradeoff between two real goods",
    "reckoning: make the protagonist face what this road has made of them",
    "ending: close the life with beauty, loss, and a sense of irreversible shape",
]

EMOTIONAL_POLARITIES = [
    "bittersweet",
    "hopeful with a cost",
    "uneasy",
    "tender",
    "painful but clarifying",
    "quietly triumphant",
    "ambiguous",
]

MODE_DIRECTIONS = {
    "grounded": (
        "Keep the story realistic and intimate. Drama should come from work, love, "
        "family, health, money, place, identity, ambition, and time."
    ),
    "strange": (
        "Let one uncanny or surreal pressure bend the life path, while keeping the "
        "emotional consequences human and coherent."
    ),
    "cinematic": (
        "Use bolder reversals, sharper images, and high-stakes turning points, but "
        "keep choices emotionally plausible rather than melodramatic."
    ),
}


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

    @model_validator(mode="after")
    def require_abc_choices(self) -> "SceneResponse":
        ids = [choice.id for choice in self.choices]
        if ids != ["A", "B", "C"]:
            raise ValueError("choices must contain exactly A, B, and C in order")
        return self


class AlternateLife(BaseModel):
    source_choice: str
    title: str
    summary: str
    emotional_aftertaste: str


class EndingResponse(BaseModel):
    time_jump: str
    final_scene: str
    chosen_life_summary: str
    alternate_lives: list[AlternateLife] = Field(min_length=2, max_length=2)
    memory_update: str


StoryResponse = SceneResponse | EndingResponse


def clamp_max_steps(max_steps: int | float | str | None) -> int:
    try:
        value = int(max_steps or DEFAULT_MAX_STEPS)
    except (TypeError, ValueError):
        value = DEFAULT_MAX_STEPS

    return max(MIN_STEPS, min(MAX_STEPS, value))


def normalize_mode(mode: str | None) -> StoryMode:
    if mode in MODE_DIRECTIONS:
        return mode  # type: ignore[return-value]
    return "grounded"


def choice_to_text(choice: dict[str, Any] | str | None) -> str:
    if choice is None:
        return "The story is starting."

    if isinstance(choice, str):
        return choice

    label = choice.get("label", "Untitled road")
    preview = choice.get("preview", "")
    choice_id = choice.get("id", "?")
    return f"{choice_id}: {label} - {preview}".strip()


def choice_id_from_selection(choice: dict[str, Any] | str | None) -> str | None:
    if choice is None:
        return None

    if isinstance(choice, dict):
        return choice.get("id")

    prefix = choice.split(":", 1)[0].strip()
    return prefix if prefix in {"A", "B", "C"} else None


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

    candidate = text[start : end + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON from model:\n\n{candidate}\n\nJSON error:\n{e}"
        )


def repair_json_with_model(
    broken_text: str,
    error_message: str = "",
    required_structure: str = SCENE_JSON_INSTRUCTIONS,
) -> dict:
    """
    Asks the model to repair malformed or incomplete JSON.
    """
    repair_prompt = f"""
The following text was supposed to be valid JSON, but it failed to parse or validate.

Repair it into valid JSON using this required structure:

{required_structure}

Rules:
- Return only valid JSON.
- Do not add markdown.
- Do not add explanation.
- Preserve the meaning when possible.
- If the text was cut off, complete the missing fields yourself.

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


def create_initial_state(
    premise: str,
    mode: str | None = "grounded",
    max_steps: int | float | str | None = DEFAULT_MAX_STEPS,
) -> dict:
    return {
        "premise": premise,
        "mode": normalize_mode(mode),
        "max_steps": clamp_max_steps(max_steps),
        "active_branch": "main",
        "initial_choices": [],
        "initial_chosen_choice": None,
        "initial_roads_not_taken": [],
        "branches": {
            "main": {
                "title": "The first road",
                "summary": "The story has just begun.",
                "recent_scene": "",
                "chosen_decisions": [],
                "last_choices": [],
                "choice_memory": [],
                "step": 0,
                "ended": False,
            }
        },
    }


def get_director_context(decision_count: int, mode: StoryMode, max_steps: int) -> str:
    beat_index = min(decision_count, len(DRAMATIC_BEATS) - 1)
    polarity = EMOTIONAL_POLARITIES[decision_count % len(EMOTIONAL_POLARITIES)]

    if decision_count == 0:
        time_instruction = "Begin at the first major fork. The choices should be three incompatible life directions."
    elif decision_count == 1:
        time_instruction = "Jump weeks or months forward and show the first real consequence."
    elif decision_count == 2:
        time_instruction = "Jump several months or one year forward."
    elif decision_count < max_steps - 1:
        time_instruction = "Jump 1 to 3 years forward and compress routine events."
    else:
        time_instruction = "Jump several years forward and move clearly toward closure."

    return f"""
Story director:
- Mode: {mode}
- Mode direction: {MODE_DIRECTIONS[mode]}
- Dramatic beat: {DRAMATIC_BEATS[beat_index]}
- Emotional polarity: {polarity}
- Story length target: {max_steps} major choices before the ending.
- Time jump: {time_instruction}
- Novelty rule: do not reuse the same life domain, emotional bargain, or choice shape unless it has clearly transformed.
"""


def remember_initial_fork(
    state: dict,
    branch: dict,
    selected_choice: dict[str, Any] | str | None,
) -> None:
    if branch["chosen_decisions"]:
        return

    initial_choices = branch.get("last_choices", [])
    if not initial_choices:
        return

    selected_id = choice_id_from_selection(selected_choice)
    state["initial_choices"] = initial_choices
    state["initial_chosen_choice"] = choice_to_text(selected_choice)
    state["initial_roads_not_taken"] = [
        choice for choice in initial_choices if choice.get("id") != selected_id
    ][:2]


def record_selected_choice(
    state: dict,
    branch: dict,
    selected_choice: dict[str, Any] | str | None,
) -> str:
    selected_text = choice_to_text(selected_choice)

    if selected_choice is not None:
        remember_initial_fork(state, branch, selected_choice)
        branch["chosen_decisions"].append(selected_text)

    return selected_text


def update_choice_memory(branch: dict, scene_response: SceneResponse) -> None:
    memory = branch.setdefault("choice_memory", [])
    memory.extend(
        [
            f'{choice.id}: {choice.label} - {choice.preview}'
            for choice in scene_response.choices
        ]
    )
    branch["choice_memory"] = memory[-12:]


def parse_scene_response(raw: str) -> SceneResponse:
    try:
        parsed = extract_json(raw)
        return SceneResponse.model_validate(parsed)
    except (ValueError, ValidationError) as e:
        print("\n--- RAW MODEL OUTPUT FAILED SCENE JSON PARSING OR VALIDATION ---")
        print(raw)
        print("\n--- ERROR ---")
        print(e)
        print("--- END RAW MODEL OUTPUT ---\n")

        parsed = repair_json_with_model(
            raw,
            error_message=str(e),
            required_structure=SCENE_JSON_INSTRUCTIONS,
        )
        return SceneResponse.model_validate(parsed)


def parse_ending_response(raw: str) -> EndingResponse:
    try:
        parsed = extract_json(raw)
        return EndingResponse.model_validate(parsed)
    except (ValueError, ValidationError) as e:
        print("\n--- RAW MODEL OUTPUT FAILED ENDING JSON PARSING OR VALIDATION ---")
        print(raw)
        print("\n--- ERROR ---")
        print(e)
        print("--- END RAW MODEL OUTPUT ---\n")

        parsed = repair_json_with_model(
            raw,
            error_message=str(e),
            required_structure=ENDING_JSON_INSTRUCTIONS,
        )
        return EndingResponse.model_validate(parsed)


def get_scene_markdown(scene_response: SceneResponse) -> str:
    return f"""
### {scene_response.time_jump}

{scene_response.scene}
"""


def get_ending_markdown(ending_response: EndingResponse) -> str:
    alternate_lives = "\n\n".join(
        [
            f"### {life.title}\n"
            f"**Began from:** {life.source_choice}\n\n"
            f"{life.summary}\n\n"
            f"*Aftertaste:* {life.emotional_aftertaste}"
            for life in ending_response.alternate_lives
        ]
    )

    return f"""
### {ending_response.time_jump}

{ending_response.final_scene}

---

## The life you lived

{ending_response.chosen_life_summary}

---

## Roads not taken

{alternate_lives}
"""


def get_alternate_life_seeds(state: dict) -> list[dict[str, str]]:
    seeds = state.get("initial_roads_not_taken", [])[:2]

    while len(seeds) < 2:
        seeds.append(
            {
                "id": "?",
                "label": "An unseen first road",
                "tone": "unknown",
                "preview": "A different life began from the first fork.",
            }
        )

    return seeds


def generate_ending(
    state: dict,
    branch: dict,
    selected_text: str,
) -> tuple[dict, EndingResponse]:
    mode = normalize_mode(state.get("mode"))
    max_steps = clamp_max_steps(state.get("max_steps"))
    decision_count = len(branch["chosen_decisions"])
    director_context = get_director_context(decision_count, mode, max_steps)

    user_prompt = f"""
Premise:
{state["premise"]}

Chosen initial road:
{state.get("initial_chosen_choice") or "Unknown"}

Initial roads not taken:
{get_alternate_life_seeds(state)}

Chosen decisions in the lived road:
{branch["chosen_decisions"]}

Current branch summary:
{branch["summary"]}

Recent scene:
{branch["recent_scene"]}

Final selected choice:
{selected_text}

{director_context}

Task:
End the chosen life path. Then simulate exactly two miniature alternate lives, each based only on one of the two initial roads not taken.

Rules:
- Do not use later unchosen choices as alternate-life seeds.
- The alternate lives should feel coherent from the initial fork, not related to later choices in the chosen road.
- Give every life beauty and loss.
- Do not provide new choices.

{ENDING_JSON_INSTRUCTIONS}
"""

    raw = generate_chat_response(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.78,
        max_tokens=1000,
    )

    ending_response = parse_ending_response(raw)
    branch["recent_scene"] = ending_response.final_scene
    branch["summary"] = ending_response.memory_update
    branch["last_choices"] = []
    branch["ended"] = True
    branch["step"] = branch.get("step", 0) + 1

    return state, ending_response


def generate_scene(
    state: dict,
    selected_choice: dict[str, Any] | str | None = None,
) -> tuple[dict, StoryResponse]:
    active_branch_id = state["active_branch"]
    branch = state["branches"][active_branch_id]
    step = branch.get("step", 0)
    mode = normalize_mode(state.get("mode"))
    max_steps = clamp_max_steps(state.get("max_steps"))
    selected_text = record_selected_choice(state, branch, selected_choice)
    decision_count = len(branch["chosen_decisions"])

    if selected_choice is not None and decision_count >= max_steps:
        return generate_ending(state, branch, selected_text)

    director_context = get_director_context(decision_count, mode, max_steps)

    user_prompt = f"""
Story step:
{step}

Decisions chosen so far:
{decision_count} of {max_steps}

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

Recent choice patterns to avoid repeating:
{branch.get("choice_memory", [])}

Selected choice:
{selected_text}

{director_context}

Task:
Continue this branch only. Then provide exactly 3 new choices.

Forbidden choice types:
- Do not offer a choice to undo the selected choice.
- Do not offer a choice to go back to the exact earlier decision.
- Do not offer tiny tactical choices like call, text, sleep, wait, or walk away unless they permanently reshape the life path.
- Each choice must move the protagonist into a different future.
- Do not make all choices versions of the same desire, career move, relationship move, or escape.

Choice design:
- Make one choice open a promising cost.
- Make one choice protect something meaningful while losing something else.
- Make one choice introduce a surprising but plausible turn for the selected mode.

{SCENE_JSON_INSTRUCTIONS}
"""

    raw = generate_chat_response(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.82,
        max_tokens=950,
    )

    scene_response = parse_scene_response(raw)

    branch["recent_scene"] = scene_response.scene
    branch["summary"] = scene_response.memory_update
    branch["last_choices"] = [choice.model_dump() for choice in scene_response.choices]
    branch["step"] = step + 1
    update_choice_memory(branch, scene_response)

    if step == 0:
        state["initial_choices"] = branch["last_choices"]

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
