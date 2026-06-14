from html import escape

import gradio as gr

from story_engine import (
    EndingResponse,
    answer_untaken_road_question,
    create_initial_state,
    generate_scene,
    get_ending_markdown,
    get_scene_markdown,
)

CSS = """
:root {
    --lantern-bg: #171410;
    --lantern-panel: rgba(39, 31, 25, 0.86);
    --lantern-panel-strong: rgba(51, 39, 29, 0.92);
    --lantern-paper: #f4e5c4;
    --lantern-ink: #f8ecd1;
    --lantern-muted: #cbbf9f;
    --lantern-amber: #e7b85d;
    --lantern-copper: #b86f45;
    --lantern-moss: #7f9562;
    --lantern-berry: #9f5869;
    --lantern-border: rgba(231, 184, 93, 0.34);
}

.gradio-container {
    color: var(--lantern-ink) !important;
    background:
        radial-gradient(circle at 50% 0%, rgba(231, 184, 93, 0.16), transparent 28rem),
        radial-gradient(circle at 8% 22%, rgba(127, 149, 98, 0.14), transparent 22rem),
        radial-gradient(circle at 85% 70%, rgba(159, 88, 105, 0.12), transparent 24rem),
        linear-gradient(180deg, #16110f 0%, #1d1713 48%, #11100d 100%) !important;
    min-height: 100vh;
}

.gradio-container::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background-image:
        linear-gradient(rgba(255, 255, 255, 0.024) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.018) 1px, transparent 1px);
    background-size: 46px 46px;
    mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.75), transparent 80%);
}

.gradio-container a,
.gradio-container label,
.gradio-container .prose,
.gradio-container .prose * {
    color: var(--lantern-ink);
}

.app-shell {
    max-width: 1120px;
    margin: 0 auto;
}

#main-title h1 {
    text-align: center;
    margin: 0.4rem 0 0.2rem;
    color: #fff4db;
    font-family: Georgia, "Times New Roman", serif;
    font-size: clamp(2.6rem, 7vw, 5.2rem);
    font-weight: 500;
    letter-spacing: 0;
    text-shadow: 0 0 34px rgba(231, 184, 93, 0.26);
}

#subtitle {
    text-align: center;
    margin-bottom: 1.6rem;
}

#subtitle p {
    color: var(--lantern-muted);
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.08rem;
    font-style: italic;
}

.eyebrow {
    color: var(--lantern-amber);
    font-size: 0.72rem;
    letter-spacing: 0.28em;
    text-align: center;
    text-transform: uppercase;
}

.ritual-panel,
.story-box,
.choice-card,
.trail-box {
    border: 1px solid var(--lantern-border);
    border-radius: 8px;
    background:
        linear-gradient(135deg, rgba(255, 244, 219, 0.065), transparent 42%),
        var(--lantern-panel);
    box-shadow: 0 18px 70px rgba(0, 0, 0, 0.34);
}

.ritual-panel {
    padding: 22px;
    margin-bottom: 14px;
    background:
        linear-gradient(135deg, rgba(231, 184, 93, 0.1), transparent 38%),
        linear-gradient(180deg, rgba(45, 35, 25, 0.96), rgba(29, 23, 18, 0.95));
}

.ritual-panel .form,
.ritual-panel .block,
.ritual-panel .block-label,
.ritual-panel .label-wrap,
.ritual-panel .wrap,
.ritual-panel .container,
.ritual-panel .secondary-wrap {
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}

.ritual-panel .block-label,
.ritual-panel .label-wrap {
    padding-left: 0 !important;
    padding-right: 0 !important;
}

.ritual-panel label,
.ritual-panel .label-wrap,
.ritual-panel .block-label {
    color: var(--lantern-amber) !important;
    font-family: Georgia, "Palatino Linotype", "Times New Roman", serif !important;
    font-size: 0.82rem !important;
    font-weight: 700 !important;
    letter-spacing: 0;
}

.premise-field {
    padding: 0 !important;
    background: transparent !important;
}

.premise-field textarea {
    min-height: 8.8rem !important;
    padding: 1.1rem 1.15rem !important;
    border: 1px solid rgba(231, 184, 93, 0.42) !important;
    border-radius: 8px !important;
    background:
        linear-gradient(180deg, rgba(244, 229, 196, 0.055), rgba(244, 229, 196, 0.018)),
        rgba(18, 14, 11, 0.86) !important;
    color: #fff1d3 !important;
    font-family: Georgia, "Palatino Linotype", "Times New Roman", serif !important;
    font-size: 1.08rem !important;
    line-height: 1.7 !important;
    box-shadow: inset 0 0 28px rgba(0, 0, 0, 0.25) !important;
}

.premise-field textarea:focus {
    border-color: rgba(255, 213, 129, 0.82) !important;
    box-shadow:
        inset 0 0 28px rgba(0, 0, 0, 0.25),
        0 0 0 2px rgba(231, 184, 93, 0.16),
        0 0 32px rgba(231, 184, 93, 0.16) !important;
}

.premise-field textarea::placeholder {
    color: rgba(244, 229, 196, 0.58) !important;
}

.settings-strip {
    margin-top: 0.85rem !important;
    padding-top: 0.9rem !important;
    border-top: 1px solid rgba(231, 184, 93, 0.2);
    align-items: end;
    gap: 0.75rem !important;
    background: rgba(18, 14, 11, 0.18);
    border-radius: 8px;
}

.settings-strip .block {
    padding: 0 !important;
}

.setting-control {
    min-width: 0;
}

.setting-control .wrap,
.setting-control .container,
.setting-control .secondary-wrap {
    border-color: rgba(231, 184, 93, 0.24) !important;
    background: rgba(18, 14, 11, 0.55) !important;
    color: var(--lantern-ink) !important;
}

.setting-control input:not([type="checkbox"]),
.setting-control select {
    min-height: 2.4rem !important;
    border-radius: 8px !important;
    background: transparent !important;
    color: var(--lantern-ink) !important;
}

.setting-control .wrap:hover,
.setting-control .container:hover {
    border-color: rgba(231, 184, 93, 0.46) !important;
}

.custom-choice-toggle,
.custom-choice-toggle .wrap,
.custom-choice-toggle .container,
.custom-choice-toggle .checkbox,
.custom-choice-toggle label {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}

.custom-choice-toggle input[type="checkbox"] {
    width: 1.05rem !important;
    height: 1.05rem !important;
    min-height: 1.05rem !important;
    accent-color: var(--lantern-amber);
}

.custom-choice-toggle label {
    display: flex !important;
    align-items: center !important;
    gap: 0.45rem !important;
    min-height: 2.4rem;
}

.compact-controls {
    align-items: end;
}

button.primary,
.gradio-container button.primary {
    border: 1px solid rgba(255, 229, 167, 0.5) !important;
    background: linear-gradient(135deg, #e6b75d 0%, #bd7544 100%) !important;
    color: #20150d !important;
    font-weight: 700 !important;
    box-shadow: 0 8px 26px rgba(231, 184, 93, 0.28);
}

.gradio-container button:not(.primary) {
    border-color: rgba(231, 184, 93, 0.34) !important;
    background: rgba(33, 27, 23, 0.88) !important;
    color: var(--lantern-ink) !important;
}

.gradio-container button:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.26);
}

.status-text {
    color: var(--lantern-muted);
    font-family: Georgia, "Times New Roman", serif;
    font-style: italic;
    margin: 0.6rem 0 0.9rem;
}

.story-box {
    padding: 22px 24px;
    margin-bottom: 18px;
    background:
        linear-gradient(180deg, rgba(244, 229, 196, 0.09), rgba(244, 229, 196, 0.035)),
        var(--lantern-panel-strong);
}

.story-box h3,
.story-box h2 {
    color: #fff2d2;
    font-family: Georgia, "Times New Roman", serif;
    letter-spacing: 0;
}

.story-box p,
.story-box li {
    color: #f4e8ca;
    font-size: 1.03rem;
    line-height: 1.72;
}

.section-title h2 {
    color: #fff1cd;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.35rem;
    font-weight: 500;
    margin-top: 0.8rem;
}

.choice-card {
    min-height: 220px;
    padding: 16px;
    transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}

.choice-card:hover {
    border-color: rgba(231, 184, 93, 0.72);
    background:
        linear-gradient(135deg, rgba(231, 184, 93, 0.13), transparent 45%),
        var(--lantern-panel);
    transform: translateY(-2px);
}

.choice-card h3 {
    color: #fff0ca;
    font-family: Georgia, "Times New Roman", serif;
    margin-top: 0;
}

.choice-card strong {
    color: var(--lantern-amber);
}

.trail-box {
    padding: 18px;
    margin-bottom: 18px;
    overflow: hidden;
}

.trail-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.8rem;
}

.trail-title {
    color: #fff1cd;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.35rem;
}

.trail-kicker {
    color: var(--lantern-amber);
    font-size: 0.72rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
}

.chosen-trail {
    position: relative;
    display: grid;
    gap: 0.62rem;
    margin: 0.2rem 0 0.4rem;
}

.chosen-trail::before {
    content: "";
    position: absolute;
    left: 16px;
    top: 14px;
    bottom: 14px;
    width: 2px;
    background: linear-gradient(var(--lantern-amber), rgba(231, 184, 93, 0.12));
}

.trail-step {
    position: relative;
    display: grid;
    grid-template-columns: 34px 1fr;
    gap: 0.75rem;
    align-items: start;
}

.trail-dot {
    z-index: 1;
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border: 1px solid rgba(255, 230, 174, 0.62);
    border-radius: 999px;
    background: radial-gradient(circle, #ffe7a9 0%, #c9853f 52%, #44281a 100%);
    color: #24160d;
    font-size: 0.82rem;
    font-weight: 800;
    box-shadow: 0 0 22px rgba(231, 184, 93, 0.3);
}

.trail-dot.unlit {
    background: radial-gradient(circle, #8d826a 0%, #4b4032 58%, #211914 100%);
    color: #d7c8a5;
}

.trail-label {
    min-height: 34px;
    padding: 0.45rem 0.75rem;
    border: 1px solid rgba(231, 184, 93, 0.18);
    border-radius: 8px;
    background: rgba(17, 14, 12, 0.48);
    color: #f7e8c8;
}

.ending-map {
    margin-top: 1.1rem;
    padding-top: 1rem;
    border-top: 1px solid rgba(231, 184, 93, 0.18);
}

.ending-map-title {
    margin-bottom: 0.8rem;
    color: #fff1cd;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.18rem;
    text-align: center;
}

.branch-map {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(120px, 0.58fr) minmax(0, 1fr);
    gap: 0.8rem;
    align-items: start;
}

.shadow-branch {
    position: relative;
    display: grid;
    gap: 0.55rem;
    padding: 0.85rem;
    border: 1px solid rgba(231, 184, 93, 0.2);
    border-radius: 8px;
    background: rgba(17, 14, 12, 0.38);
}

.shadow-branch.left {
    transform: rotate(-4deg);
    transform-origin: top right;
}

.shadow-branch.right {
    transform: rotate(4deg);
    transform-origin: top left;
}

.shadow-branch.left::before,
.shadow-branch.right::before {
    content: "";
    position: absolute;
    top: -1.1rem;
    width: 54%;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(231, 184, 93, 0.65), transparent);
}

.shadow-branch.left::before {
    right: -0.3rem;
    transform: rotate(-24deg);
}

.shadow-branch.right::before {
    left: -0.3rem;
    transform: rotate(24deg);
}

.shadow-title {
    color: var(--lantern-amber);
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1rem;
}

.shadow-point {
    display: grid;
    grid-template-columns: 24px 1fr;
    gap: 0.5rem;
    color: #e9ddbd;
    font-size: 0.9rem;
    line-height: 1.35;
}

.shadow-dot {
    display: grid;
    place-items: center;
    width: 24px;
    height: 24px;
    border-radius: 999px;
    background: rgba(127, 149, 98, 0.24);
    color: #d9e2bd;
    font-size: 0.72rem;
}

.lived-stem {
    display: grid;
    place-items: center;
    min-height: 8.5rem;
    color: var(--lantern-muted);
    text-align: center;
}

.lived-stem::before {
    content: "";
    display: block;
    width: 2px;
    height: 5.2rem;
    margin: 0 auto 0.7rem;
    background: linear-gradient(rgba(231, 184, 93, 0.85), rgba(231, 184, 93, 0.16));
}

.road-answer {
    border: 1px solid rgba(231, 184, 93, 0.22);
    border-radius: 8px;
    padding: 12px;
    background: rgba(17, 14, 12, 0.42);
}

.custom-road-header,
.road-question-header {
    margin-top: 16px;
    padding: 14px 16px 0;
    border: 1px solid var(--lantern-border);
    border-bottom: 0;
    border-radius: 8px 8px 0 0;
    background:
        linear-gradient(135deg, rgba(255, 244, 219, 0.065), transparent 42%),
        var(--lantern-panel);
}

.custom-road-input,
.road-question-input {
    padding: 0 16px 14px !important;
    border-right: 1px solid var(--lantern-border);
    border-left: 1px solid var(--lantern-border);
    background: var(--lantern-panel);
}

.custom-road-input textarea,
.road-question-input textarea {
    border: 1px solid rgba(231, 184, 93, 0.34) !important;
    border-radius: 8px !important;
    background: rgba(18, 14, 11, 0.72) !important;
    color: var(--lantern-ink) !important;
}

.custom-road-input textarea::placeholder,
.road-question-input textarea::placeholder {
    color: rgba(244, 229, 196, 0.52) !important;
}

.custom-road-button {
    padding: 0 16px 16px;
    border-right: 1px solid var(--lantern-border);
    border-bottom: 1px solid var(--lantern-border);
    border-left: 1px solid var(--lantern-border);
    border-radius: 0 0 8px 8px;
    background: var(--lantern-panel);
}

.road-question-actions {
    margin-top: 0;
}

@media (max-width: 760px) {
    .branch-map {
        grid-template-columns: 1fr;
    }

    .lived-stem {
        min-height: auto;
    }

    .lived-stem::before {
        height: 2.5rem;
    }

    .shadow-branch.left,
    .shadow-branch.right {
        transform: none;
    }

    .shadow-branch.left::before,
    .shadow-branch.right::before {
        display: none;
    }
}
"""

CUSTOM_CHOICE_MIN_CHARS = 20
CUSTOM_CHOICE_MAX_CHARS = 180


def shorten_text(text: str, limit: int = 82) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def get_choice_label(choice_text: str) -> str:
    text = " ".join(str(choice_text).split())
    if ": " in text:
        text = text.split(": ", 1)[1]
    if " - " in text:
        text = text.split(" - ", 1)[0]
    return text


def choice_to_markdown(choice: dict) -> str:
    return f"""
<div class="choice-inner">
<div class="trail-kicker">Road {escape(choice["id"])}</div>

### {escape(choice["label"])}

<p><strong>{escape(choice["tone"])}</strong></p>
<p>{escape(choice["preview"])}</p>
</div>
"""


def empty_choice_cards():
    return "", "", ""


def get_choice_cards(scene_response):
    choices = [choice.model_dump() for choice in scene_response.choices]

    return (
        choice_to_markdown(choices[0]),
        choice_to_markdown(choices[1]),
        choice_to_markdown(choices[2]),
    )


def get_trail_markdown(state: dict | None) -> str:
    if not state:
        chosen_steps = """
<div class="trail-step">
  <div class="trail-dot unlit">0</div>
  <div class="trail-label">The first fork is waiting for a lantern.</div>
</div>
"""
        progress = "No road lit yet"
        ending_map = ""
    else:
        branch = state["branches"][state["active_branch"]]
        decisions = branch.get("chosen_decisions", [])
        if decisions:
            step_html = []
            for index, decision in enumerate(decisions, start=1):
                label = escape(shorten_text(get_choice_label(decision)))
                step_html.append(
                    f"""
<div class="trail-step">
  <div class="trail-dot">{index}</div>
  <div class="trail-label">{label}</div>
</div>
"""
                )
            chosen_steps = "\n".join(step_html)
        else:
            chosen_steps = """
<div class="trail-step">
  <div class="trail-dot unlit">0</div>
  <div class="trail-label">The first fork is lit. Choose the road that calls.</div>
</div>
"""

        made = len(decisions)
        max_steps = state.get("max_steps", "?")
        progress = f"{made} of {max_steps} major choices made"
        if branch.get("ended"):
            progress = "The lived road has reached its clearing"
        ending_map = get_ending_branch_map_markdown(state)

    return f"""
<div class="trail-box">
  <div class="trail-header">
    <div class="trail-title">Lantern Trail</div>
    <div class="trail-kicker">{escape(progress)}</div>
  </div>
  <div class="chosen-trail">
    {chosen_steps}
  </div>
  {ending_map}
</div>
"""


def get_shadow_branch_markdown(life: dict, side: str) -> str:
    title = escape(life.get("title", "An unlived road"))
    points = life.get("turning_points", [])[:3]
    point_html = []
    for index, point in enumerate(points, start=1):
        point_html.append(
            f"""
<div class="shadow-point">
  <div class="shadow-dot">{index}</div>
  <div>{escape(shorten_text(point, 68))}</div>
</div>
"""
        )

    while len(point_html) < 3:
        index = len(point_html) + 1
        point_html.append(
            f"""
<div class="shadow-point">
  <div class="shadow-dot">{index}</div>
  <div>A hidden turn the road keeps to itself.</div>
</div>
"""
        )

    return f"""
<div class="shadow-branch {side}">
  <div class="shadow-title">{title}</div>
  {''.join(point_html)}
</div>
"""


def get_ending_branch_map_markdown(state: dict | None) -> str:
    if not state or not state.get("ending"):
        return ""

    alternate_lives = state["ending"].get("alternate_lives", [])
    if len(alternate_lives) < 2:
        return ""

    left_branch = get_shadow_branch_markdown(alternate_lives[0], "left")
    right_branch = get_shadow_branch_markdown(alternate_lives[1], "right")

    return (
        '<div class="ending-map">'
        '<div class="ending-map-title">The roads that kept walking without you</div>'
        '<div class="branch-map">'
        f"{left_branch}"
        '<div class="lived-stem">the life you lived</div>'
        f"{right_branch}"
        "</div>"
        "</div>"
    )


def get_hidden_custom_choice_outputs():
    return (
        gr.update(value="", visible=False),
        gr.update(value="", visible=False, interactive=False),
        gr.update(value="Choose custom road", visible=False, interactive=False),
    )


def should_show_custom_choice(state: dict | None) -> bool:
    if not state or not state.get("custom_choices_enabled"):
        return False

    branch = state["branches"][state["active_branch"]]
    return (
        bool(branch.get("last_choices"))
        and bool(branch.get("chosen_decisions"))
        and not branch.get("ended")
    )


def get_custom_choice_outputs(state: dict | None, value: str = ""):
    if not should_show_custom_choice(state):
        return get_hidden_custom_choice_outputs()

    return (
        gr.update(value="### Write your own road", visible=True),
        gr.update(
            label="Custom choice",
            placeholder="Choose a life-shaping road the three options missed...",
            value=value,
            visible=True,
            interactive=True,
        ),
        gr.update(
            value="Choose custom road",
            visible=True,
            interactive=True,
        ),
    )


def validate_custom_choice_text(custom_choice: str) -> tuple[str | None, str]:
    text = custom_choice.strip()
    if not text:
        return (
            f"Write a custom road first ({CUSTOM_CHOICE_MIN_CHARS}-"
            f"{CUSTOM_CHOICE_MAX_CHARS} characters).",
            text,
        )

    length = len(text)
    if length < CUSTOM_CHOICE_MIN_CHARS:
        return (
            f"Custom roads need at least {CUSTOM_CHOICE_MIN_CHARS} characters.",
            text,
        )
    if length > CUSTOM_CHOICE_MAX_CHARS:
        return (
            f"Custom roads must be {CUSTOM_CHOICE_MAX_CHARS} characters or fewer.",
            text,
        )

    return None, text


def custom_choice_to_selection(custom_choice: str) -> dict:
    return {
        "id": "D",
        "label": custom_choice,
        "tone": "self-authored",
        "preview": "A self-authored road with consequences the story must honor.",
    }


def active_choice_buttons(state: dict | None):
    if not state:
        return (
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
        )

    branch = state["branches"][state["active_branch"]]
    interactive = bool(branch.get("last_choices")) and not branch.get("ended")
    return (
        gr.update(interactive=interactive),
        gr.update(interactive=interactive),
        gr.update(interactive=interactive),
    )


def get_hidden_road_question_outputs():
    return (
        gr.update(value="", visible=False),
        gr.update(value="", visible=False, interactive=False),
        gr.update(value="Ask", visible=False, interactive=False),
        gr.update(value="", visible=False),
        gr.update(value="Ask", visible=False, interactive=False),
        gr.update(value="", visible=False),
    )


def get_road_question_outputs_for_ending(ending_response: EndingResponse):
    first_road = ending_response.alternate_lives[0]
    second_road = ending_response.alternate_lives[1]

    return (
        gr.update(value="## Ask the roads not taken", visible=True),
        gr.update(
            label="Your question",
            placeholder="What did you have that I lost?",
            value="",
            visible=True,
            interactive=True,
        ),
        gr.update(
            value=f"Ask {first_road.title}",
            visible=True,
            interactive=True,
        ),
        gr.update(value="", visible=True),
        gr.update(
            value=f"Ask {second_road.title}",
            visible=True,
            interactive=True,
        ),
        gr.update(value="", visible=True),
    )


def format_road_answer(response) -> str:
    return f"""
### {response.speaker}

{response.answer}
"""


def get_stored_road_answer(state: dict | None, source: str) -> str:
    if not state:
        return ""

    answer = state.get("road_questions", {}).get(source, {}).get("answer")
    if not answer:
        return ""

    return f"""
### {answer["speaker"]}

{answer["answer"]}
"""


def get_road_button_update(state: dict | None, source: str):
    used = bool(state and state.get("road_questions", {}).get(source, {}).get("used"))
    return gr.update(interactive=not used)


def any_road_question_available(state: dict | None) -> bool:
    if not state:
        return False
    questions = state.get("road_questions", {})
    return any(
        not questions.get(source, {}).get("used")
        for source in ("untaken_1", "untaken_2")
    )


def road_answer_outputs(
    state: dict | None,
    source: str,
    message: str,
) -> tuple[str, str]:
    road_1_answer = get_stored_road_answer(state, "untaken_1")
    road_2_answer = get_stored_road_answer(state, "untaken_2")
    if source == "untaken_1":
        road_1_answer = message
    else:
        road_2_answer = message
    return road_1_answer, road_2_answer


def start_story(
    premise: str,
    mode: str,
    max_steps: int,
    custom_choices_enabled: bool,
    ending_tone: str,
):
    if not premise.strip():
        yield (
            "Please enter a premise first.",
            "",
            "",
            "",
            "Nothing generated yet.",
            get_trail_markdown(None),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            None,
            *get_hidden_road_question_outputs(),
            *get_hidden_custom_choice_outputs(),
        )
        return

    yield (
        "Generating the first road...",
            "",
            "",
            "",
            "The lantern is searching the first bend. Local or remote inference can be slow.",
            get_trail_markdown(None),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            None,
        *get_hidden_road_question_outputs(),
        *get_hidden_custom_choice_outputs(),
    )

    state = create_initial_state(
        premise,
        mode=mode,
        max_steps=max_steps,
        ending_tone=ending_tone,
        custom_choices_enabled=custom_choices_enabled,
    )
    state, scene_response = generate_scene(state)

    choice_a, choice_b, choice_c = get_choice_cards(scene_response)

    yield (
        get_scene_markdown(scene_response),
        choice_a,
        choice_b,
        choice_c,
        f"Choose one road to continue. This story will end after {state['max_steps']} major choices.",
        get_trail_markdown(state),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        state,
        *get_hidden_road_question_outputs(),
        *get_custom_choice_outputs(state),
    )


def choose_path(choice_id: str, state: dict):
    if state is None:
        yield (
            "Start a story first.",
            "",
            "",
            "",
            "No active story.",
            get_trail_markdown(state),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            state,
            *get_hidden_road_question_outputs(),
            *get_hidden_custom_choice_outputs(),
        )
        return

    branch = state["branches"][state["active_branch"]]
    choices = branch.get("last_choices", [])

    selected = next((choice for choice in choices if choice["id"] == choice_id), None)

    if selected is None:
        yield (
            "That choice does not exist for the current scene.",
            "",
            "",
            "",
            "Choice error.",
            get_trail_markdown(state),
            *active_choice_buttons(state),
            state,
            *get_hidden_road_question_outputs(),
            *get_custom_choice_outputs(state),
        )
        return

    yield from continue_from_selection(state, selected)


def continue_from_selection(state: dict, selected: dict):
    selected_text = f'{selected["id"]}: {selected["label"]}'

    yield (
        f"Continuing from **{selected_text}**...",
        "",
        "",
        "",
        "The lantern is carrying your choice into the years ahead.",
        get_trail_markdown(state),
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        state,
        *get_hidden_road_question_outputs(),
        *get_hidden_custom_choice_outputs(),
    )

    state, story_response = generate_scene(state, selected_choice=selected)

    if isinstance(story_response, EndingResponse):
        yield (
            get_ending_markdown(story_response),
            "",
            "",
            "",
            "This road has reached its ending.",
            get_trail_markdown(state),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            state,
            *get_road_question_outputs_for_ending(story_response),
            *get_hidden_custom_choice_outputs(),
        )
        return

    scene_response = story_response
    branch = state["branches"][state["active_branch"]]
    choice_a, choice_b, choice_c = get_choice_cards(scene_response)

    yield (
        get_scene_markdown(scene_response),
        choice_a,
        choice_b,
        choice_c,
        f"Choose one road to continue. {len(branch['chosen_decisions'])} of {state['max_steps']} choices made.",
        get_trail_markdown(state),
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        state,
        *get_hidden_road_question_outputs(),
        *get_custom_choice_outputs(state),
    )


def choose_custom_path(
    custom_choice: str,
    current_story: str,
    choice_a: str,
    choice_b: str,
    choice_c: str,
    state: dict,
):
    if state is None:
        yield (
            "Start a story first.",
            "",
            "",
            "",
            "No active story.",
            get_trail_markdown(state),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            state,
            *get_hidden_road_question_outputs(),
            *get_hidden_custom_choice_outputs(),
        )
        return

    if not should_show_custom_choice(state):
        yield (
            current_story,
            choice_a,
            choice_b,
            choice_c,
            "Custom choices are not available for this story yet.",
            get_trail_markdown(state),
            *active_choice_buttons(state),
            state,
            *get_hidden_road_question_outputs(),
            *get_custom_choice_outputs(state, custom_choice),
        )
        return

    error, custom_choice = validate_custom_choice_text(custom_choice)
    if error:
        yield (
            current_story,
            choice_a,
            choice_b,
            choice_c,
            error,
            get_trail_markdown(state),
            *active_choice_buttons(state),
            state,
            *get_hidden_road_question_outputs(),
            *get_custom_choice_outputs(state, custom_choice),
        )
        return

    selected = custom_choice_to_selection(custom_choice)
    yield from continue_from_selection(state, selected)


def choose_a(state):
    yield from choose_path("A", state)


def choose_b(state):
    yield from choose_path("B", state)


def choose_c(state):
    yield from choose_path("C", state)


def ask_untaken_road(source: str, question: str, state: dict):
    if state is None:
        yield (
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            "Start and finish a story first.",
            gr.update(interactive=False),
            "",
            state,
        )
        return

    if not question.strip():
        road_1_answer, road_2_answer = road_answer_outputs(
            state,
            source,
            "Ask a question first.",
        )
        yield (
            gr.update(value=question, interactive=True),
            gr.update(interactive=True),
            road_1_answer,
            gr.update(interactive=True),
            road_2_answer,
            state,
        )
        return

    road_1_answer, road_2_answer = road_answer_outputs(
        state,
        source,
        "The road is answering...",
    )
    yield (
        gr.update(value=question, interactive=False),
        gr.update(interactive=False),
        road_1_answer,
        gr.update(interactive=False),
        road_2_answer,
        state,
    )

    try:
        state, response = answer_untaken_road_question(state, source, question)
    except ValueError as e:
        road_1_answer, road_2_answer = road_answer_outputs(state, source, str(e))
        yield (
            gr.update(value=question, interactive=any_road_question_available(state)),
            get_road_button_update(state, "untaken_1"),
            road_1_answer,
            get_road_button_update(state, "untaken_2"),
            road_2_answer,
            state,
        )
        return

    road_1_answer = get_stored_road_answer(state, "untaken_1")
    road_2_answer = get_stored_road_answer(state, "untaken_2")
    if source == "untaken_1" and not road_1_answer:
        road_1_answer = format_road_answer(response)
    if source == "untaken_2" and not road_2_answer:
        road_2_answer = format_road_answer(response)

    yield (
        gr.update(value="", interactive=any_road_question_available(state)),
        get_road_button_update(state, "untaken_1"),
        road_1_answer,
        get_road_button_update(state, "untaken_2"),
        road_2_answer,
        state,
    )


def ask_untaken_1(question: str, state: dict):
    yield from ask_untaken_road("untaken_1", question, state)


def ask_untaken_2(question: str, state: dict):
    yield from ask_untaken_road("untaken_2", question, state)


with gr.Blocks(title="Roads Untraveled") as demo:
    gr.Markdown('<div class="eyebrow">Weep not for</div>')
    gr.Markdown("# Roads Untraveled", elem_id="main-title")
    gr.Markdown(
        "Weep not for paths left 'lone." \
        "'Cause beyond every bend is a long binding end " \
        "it's the worst kind of pain I've known...",
        elem_id="subtitle",
    )

    state = gr.State(None)

    with gr.Column(elem_classes=["ritual-panel"]):
        premise = gr.Textbox(
            label="First fork",
            placeholder="Describe a point in your life when a major crossroad occurred, " \
            "add additional context such as age, relationship status, country of residence etc.",
            lines=4,
            scale=4,
            elem_classes=["premise-field"],
        )

        with gr.Row(elem_classes=["compact-controls", "settings-strip"]):
            mode = gr.Dropdown(
                label="Story mode",
                choices=["grounded", "strange", "cinematic"],
                value="grounded",
                scale=2,
                elem_classes=["setting-control"],
            )
            max_steps = gr.Slider(
                label="Major choices before ending",
                minimum=5,
                maximum=7,
                step=1,
                value=6,
                scale=2,
                elem_classes=["setting-control"],
            )
            custom_choices_enabled = gr.Checkbox(
                label="Custom choices",
                value=False,
                scale=1,
                elem_classes=["setting-control", "custom-choice-toggle"],
            )
            ending_tone = gr.Dropdown(
                label="Ending conversation",
                choices=["poetic", "weird", "direct"],
                value="poetic",
                scale=2,
                elem_classes=["setting-control"],
            )

    start_button = gr.Button("Light the first road", variant="primary")

    status = gr.Markdown(
        "The story is untold. Write the first crossroad to begin.",
        elem_classes=["status-text"],
    )

    trail_output = gr.Markdown(get_trail_markdown(None))

    story_output = gr.Markdown(
        "",
        label="Current road",
        elem_classes=["story-box"],
    )

    gr.Markdown("## Roads ahead", elem_classes=["section-title"])

    with gr.Row():
        with gr.Column():
            choice_a_card = gr.Markdown("", elem_classes=["choice-card"])
            choice_a_button = gr.Button("Take Road A", interactive=False)

        with gr.Column():
            choice_b_card = gr.Markdown("", elem_classes=["choice-card"])
            choice_b_button = gr.Button("Take Road B", interactive=False)

        with gr.Column():
            choice_c_card = gr.Markdown("", elem_classes=["choice-card"])
            choice_c_button = gr.Button("Take Road C", interactive=False)

    custom_choice_header = gr.Markdown(
        "",
        visible=False,
        elem_classes=["custom-road-header"],
    )
    custom_choice_text = gr.Textbox(
        label="Custom choice",
        lines=2,
        visible=False,
        interactive=False,
        elem_classes=["custom-road-input"],
    )
    custom_choice_button = gr.Button(
        "Choose custom road",
        visible=False,
        interactive=False,
        elem_classes=["custom-road-button"],
    )

    road_question_header = gr.Markdown(
        "",
        visible=False,
        elem_classes=["road-question-header"],
    )
    road_question_text = gr.Textbox(
        label="Your question",
        placeholder="Were you happier than me?",
        lines=2,
        visible=False,
        interactive=False,
        elem_classes=["road-question-input"],
    )

    with gr.Row(elem_classes=["road-question-actions"]):
        with gr.Column():
            road_1_button = gr.Button("Ask", visible=False, interactive=False)
            road_1_answer = gr.Markdown(
                "",
                visible=False,
                elem_classes=["road-answer"],
            )

        with gr.Column():
            road_2_button = gr.Button("Ask", visible=False, interactive=False)
            road_2_answer = gr.Markdown(
                "",
                visible=False,
                elem_classes=["road-answer"],
            )

    outputs = [
        story_output,
        choice_a_card,
        choice_b_card,
        choice_c_card,
        status,
        trail_output,
        choice_a_button,
        choice_b_button,
        choice_c_button,
        state,
        road_question_header,
        road_question_text,
        road_1_button,
        road_1_answer,
        road_2_button,
        road_2_answer,
        custom_choice_header,
        custom_choice_text,
        custom_choice_button,
    ]

    start_button.click(
        fn=start_story,
        inputs=[
            premise,
            mode,
            max_steps,
            custom_choices_enabled,
            ending_tone,
        ],
        outputs=outputs,
        show_progress="full",
    )

    choice_a_button.click(
        fn=choose_a,
        inputs=[state],
        outputs=outputs,
        show_progress="full",
    )

    choice_b_button.click(
        fn=choose_b,
        inputs=[state],
        outputs=outputs,
        show_progress="full",
    )

    choice_c_button.click(
        fn=choose_c,
        inputs=[state],
        outputs=outputs,
        show_progress="full",
    )

    custom_choice_button.click(
        fn=choose_custom_path,
        inputs=[
            custom_choice_text,
            story_output,
            choice_a_card,
            choice_b_card,
            choice_c_card,
            state,
        ],
        outputs=outputs,
        show_progress="full",
    )

    road_1_button.click(
        fn=ask_untaken_1,
        inputs=[road_question_text, state],
        outputs=[
            road_question_text,
            road_1_button,
            road_1_answer,
            road_2_button,
            road_2_answer,
            state,
        ],
        show_progress="full",
    )

    road_2_button.click(
        fn=ask_untaken_2,
        inputs=[road_question_text, state],
        outputs=[
            road_question_text,
            road_1_button,
            road_1_answer,
            road_2_button,
            road_2_answer,
            state,
        ],
        show_progress="full",
    )


if __name__ == "__main__":
    demo.queue()
    demo.launch(inbrowser=False, css=CSS)
