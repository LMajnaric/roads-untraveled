import gradio as gr

from story_engine import (
    EndingResponse,
    create_initial_state,
    generate_scene,
    get_ending_markdown,
    get_scene_markdown,
)

CSS = """
#main-title {
    text-align: center;
    margin-bottom: 0.2rem;
}

#subtitle {
    text-align: center;
    opacity: 0.8;
    margin-bottom: 1.5rem;
}

.story-box {
    border: 1px solid #333;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 18px;
    background: rgba(255, 255, 255, 0.03);
}

.choice-card {
    border: 1px solid #444;
    border-radius: 14px;
    padding: 14px;
    min-height: 210px;
    background: rgba(255, 255, 255, 0.04);
}

.choice-card h3 {
    margin-top: 0;
}

.status-text {
    opacity: 0.75;
    font-style: italic;
}
"""


def choice_to_markdown(choice: dict) -> str:
    return f"""
### {choice["id"]}. {choice["label"]}

**Tone:** {choice["tone"]}

**Preview:**  
{choice["preview"]}
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


def start_story(premise: str, mode: str, max_steps: int):
    if not premise.strip():
        yield (
            "Please enter a premise first.",
            "",
            "",
            "",
            "Nothing generated yet.",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            None,
        )
        return

    yield (
        "Generating the first road...",
        "",
        "",
        "",
        "The model is writing. Local or remote inference can be slow.",
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        None,
    )

    state = create_initial_state(premise, mode=mode, max_steps=max_steps)
    state, scene_response = generate_scene(state)

    choice_a, choice_b, choice_c = get_choice_cards(scene_response)

    yield (
        get_scene_markdown(scene_response),
        choice_a,
        choice_b,
        choice_c,
        f"Choose one road to continue. This story will end after {state['max_steps']} major choices.",
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        state,
    )


def choose_path(choice_id: str, state: dict):
    if state is None:
        yield (
            "Start a story first.",
            "",
            "",
            "",
            "No active story.",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            state,
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
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            state,
        )
        return

    selected_text = f'{selected["id"]}: {selected["label"]}'

    yield (
        f"Continuing from **{selected_text}**...",
        "",
        "",
        "",
        "The model is generating the next branch.",
        gr.update(interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        state,
    )

    state, story_response = generate_scene(state, selected_choice=selected)

    if isinstance(story_response, EndingResponse):
        yield (
            get_ending_markdown(story_response),
            "",
            "",
            "",
            "This road has reached its ending.",
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            state,
        )
        return

    scene_response = story_response
    choice_a, choice_b, choice_c = get_choice_cards(scene_response)

    yield (
        get_scene_markdown(scene_response),
        choice_a,
        choice_b,
        choice_c,
        f"Choose one road to continue. {len(branch['chosen_decisions'])} of {state['max_steps']} choices made.",
        gr.update(interactive=True),
        gr.update(interactive=True),
        gr.update(interactive=True),
        state,
    )


def choose_a(state):
    yield from choose_path("A", state)


def choose_b(state):
    yield from choose_path("B", state)


def choose_c(state):
    yield from choose_path("C", state)


with gr.Blocks(title="Roads Untraveled", css=CSS) as demo:
    gr.Markdown("# Roads Untraveled", elem_id="main-title")
    gr.Markdown(
        "Choose one path. The others still echo.",
        elem_id="subtitle",
    )

    state = gr.State(None)

    with gr.Row():
        premise = gr.Textbox(
            label="Story premise",
            placeholder="A robotics engineer receives an offer that would change the rest of his life...",
            lines=4,
            scale=4,
        )

    with gr.Row():
        mode = gr.Dropdown(
            label="Story mode",
            choices=["grounded", "strange", "cinematic"],
            value="grounded",
            scale=2,
        )
        max_steps = gr.Slider(
            label="Major choices before ending",
            minimum=5,
            maximum=7,
            step=1,
            value=6,
            scale=2,
        )

    start_button = gr.Button("Begin story", variant="primary")

    status = gr.Markdown("Nothing generated yet.", elem_classes=["status-text"])

    story_output = gr.Markdown(
        "",
        label="Current road",
        elem_classes=["story-box"],
    )

    gr.Markdown("## Roads ahead")

    with gr.Row():
        with gr.Column():
            choice_a_card = gr.Markdown("", elem_classes=["choice-card"])
            choice_a_button = gr.Button("Choose A", interactive=False)

        with gr.Column():
            choice_b_card = gr.Markdown("", elem_classes=["choice-card"])
            choice_b_button = gr.Button("Choose B", interactive=False)

        with gr.Column():
            choice_c_card = gr.Markdown("", elem_classes=["choice-card"])
            choice_c_button = gr.Button("Choose C", interactive=False)

    outputs = [
        story_output,
        choice_a_card,
        choice_b_card,
        choice_c_card,
        status,
        choice_a_button,
        choice_b_button,
        choice_c_button,
        state,
    ]

    start_button.click(
        fn=start_story,
        inputs=[premise, mode, max_steps],
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


if __name__ == "__main__":
    demo.queue()
    demo.launch(inbrowser=False)
