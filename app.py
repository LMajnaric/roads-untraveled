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


def show_roads_ahead_header():
    return gr.update(value="## Roads ahead", visible=True)


def hide_roads_ahead_header():
    return gr.update(value="", visible=False)


def visible_choice_card(value: str):
    return gr.update(value=value, visible=True)


def hidden_choice_card():
    return gr.update(value="", visible=False)


def choice_button(interactive: bool):
    return gr.update(visible=True, interactive=interactive)


def hidden_choice_button():
    return gr.update(visible=False, interactive=False)


def get_hidden_road_question_outputs():
    return (
        gr.update(value="", visible=False),
        gr.update(value="", visible=False),
        gr.update(value="", visible=False, interactive=False),
        gr.update(value="Ask", visible=False, interactive=False),
        gr.update(value="", visible=False),
        gr.update(value="", visible=False),
        gr.update(value="", visible=False, interactive=False),
        gr.update(value="Ask", visible=False, interactive=False),
        gr.update(value="", visible=False),
    )


def get_road_question_outputs_for_ending(ending_response: EndingResponse):
    first_road = ending_response.alternate_lives[0]
    second_road = ending_response.alternate_lives[1]

    return (
        gr.update(value="## Ask the roads not taken", visible=True),
        gr.update(value=f"### Ask {first_road.title}", visible=True),
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
        gr.update(value=f"### Ask {second_road.title}", visible=True),
        gr.update(
            label="Your question",
            placeholder="Were you happier than me?",
            value="",
            visible=True,
            interactive=True,
        ),
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


def start_story(premise: str, mode: str, max_steps: int, ending_tone: str):
    if not premise.strip():
        yield (
            "Please enter a premise first.",
            hide_roads_ahead_header(),
            "",
            "",
            "",
            "Nothing generated yet.",
            hidden_choice_button(),
            hidden_choice_button(),
            hidden_choice_button(),
            None,
            *get_hidden_road_question_outputs(),
        )
        return

    yield (
        "Generating the first road...",
        hide_roads_ahead_header(),
        hidden_choice_card(),
        hidden_choice_card(),
        hidden_choice_card(),
        "The model is writing. Local or remote inference can be slow.",
        hidden_choice_button(),
        hidden_choice_button(),
        hidden_choice_button(),
        None,
        *get_hidden_road_question_outputs(),
    )

    state = create_initial_state(
        premise,
        mode=mode,
        max_steps=max_steps,
        ending_tone=ending_tone,
    )
    state, scene_response = generate_scene(state)

    choice_a, choice_b, choice_c = get_choice_cards(scene_response)

    yield (
        get_scene_markdown(scene_response),
        show_roads_ahead_header(),
        visible_choice_card(choice_a),
        visible_choice_card(choice_b),
        visible_choice_card(choice_c),
        f"Choose one road to continue. This story will end after {state['max_steps']} major choices.",
        choice_button(interactive=True),
        choice_button(interactive=True),
        choice_button(interactive=True),
        state,
        *get_hidden_road_question_outputs(),
    )


def choose_path(choice_id: str, state: dict):
    if state is None:
        yield (
            "Start a story first.",
            hide_roads_ahead_header(),
            hidden_choice_card(),
            hidden_choice_card(),
            hidden_choice_card(),
            "No active story.",
            hidden_choice_button(),
            hidden_choice_button(),
            hidden_choice_button(),
            state,
            *get_hidden_road_question_outputs(),
        )
        return

    branch = state["branches"][state["active_branch"]]
    choices = branch.get("last_choices", [])

    selected = next((choice for choice in choices if choice["id"] == choice_id), None)

    if selected is None:
        yield (
            "That choice does not exist for the current scene.",
            show_roads_ahead_header(),
            hidden_choice_card(),
            hidden_choice_card(),
            hidden_choice_card(),
            "Choice error.",
            hidden_choice_button(),
            hidden_choice_button(),
            hidden_choice_button(),
            state,
            *get_hidden_road_question_outputs(),
        )
        return

    selected_text = f'{selected["id"]}: {selected["label"]}'

    yield (
        f"Continuing from **{selected_text}**...",
        hide_roads_ahead_header(),
        hidden_choice_card(),
        hidden_choice_card(),
        hidden_choice_card(),
        "The model is generating the next branch.",
        hidden_choice_button(),
        hidden_choice_button(),
        hidden_choice_button(),
        state,
        *get_hidden_road_question_outputs(),
    )

    state, story_response = generate_scene(state, selected_choice=selected)

    if isinstance(story_response, EndingResponse):
        yield (
            get_ending_markdown(story_response),
            hide_roads_ahead_header(),
            hidden_choice_card(),
            hidden_choice_card(),
            hidden_choice_card(),
            "This road has reached its ending.",
            hidden_choice_button(),
            hidden_choice_button(),
            hidden_choice_button(),
            state,
            *get_road_question_outputs_for_ending(story_response),
        )
        return

    scene_response = story_response
    choice_a, choice_b, choice_c = get_choice_cards(scene_response)

    yield (
        get_scene_markdown(scene_response),
        show_roads_ahead_header(),
        visible_choice_card(choice_a),
        visible_choice_card(choice_b),
        visible_choice_card(choice_c),
        f"Choose one road to continue. {len(branch['chosen_decisions'])} of {state['max_steps']} choices made.",
        choice_button(interactive=True),
        choice_button(interactive=True),
        choice_button(interactive=True),
        state,
        *get_hidden_road_question_outputs(),
    )


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
            "Start and finish a story first.",
            state,
        )
        return

    if not question.strip():
        yield (
            gr.update(interactive=True),
            gr.update(interactive=True),
            "Ask this road a question first.",
            state,
        )
        return

    yield (
        gr.update(interactive=False),
        gr.update(interactive=False),
        "The road is answering...",
        state,
    )

    try:
        state, response = answer_untaken_road_question(state, source, question)
    except ValueError as e:
        yield (
            gr.update(interactive=False),
            gr.update(interactive=False),
            str(e),
            state,
        )
        return

    yield (
        gr.update(interactive=False),
        gr.update(interactive=False),
        format_road_answer(response),
        state,
    )


def ask_untaken_1(question: str, state: dict):
    yield from ask_untaken_road("untaken_1", question, state)


def ask_untaken_2(question: str, state: dict):
    yield from ask_untaken_road("untaken_2", question, state)


with gr.Blocks(title="Roads Untraveled", css=CSS) as demo:
    gr.Markdown("# Roads Untraveled", elem_id="main-title")
    gr.Markdown(
        "Weep not for roads untraveled, weep not for sights unseen, cause beyond every bend is a long blinding end, it's the worst kind of pain I've known",
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
        ending_tone = gr.Dropdown(
            label="Ending conversation",
            choices=["poetic", "weird", "direct"],
            value="poetic",
            scale=2,
        )

    start_button = gr.Button("Begin story", variant="primary")

    status = gr.Markdown("Nothing generated yet.", elem_classes=["status-text"])

    story_output = gr.Markdown(
        "",
        label="Current road",
        elem_classes=["story-box"],
    )

    roads_ahead_header = gr.Markdown("## Roads ahead")

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

    road_question_header = gr.Markdown("", visible=False)

    with gr.Row():
        with gr.Column():
            road_1_title = gr.Markdown("", visible=False)
            road_1_question = gr.Textbox(
                label="Your question",
                lines=2,
                visible=False,
                interactive=False,
            )
            road_1_button = gr.Button("Ask", visible=False, interactive=False)
            road_1_answer = gr.Markdown("", visible=False)

        with gr.Column():
            road_2_title = gr.Markdown("", visible=False)
            road_2_question = gr.Textbox(
                label="Your question",
                lines=2,
                visible=False,
                interactive=False,
            )
            road_2_button = gr.Button("Ask", visible=False, interactive=False)
            road_2_answer = gr.Markdown("", visible=False)

    outputs = [
        story_output,
        roads_ahead_header,
        choice_a_card,
        choice_b_card,
        choice_c_card,
        status,
        choice_a_button,
        choice_b_button,
        choice_c_button,
        state,
        road_question_header,
        road_1_title,
        road_1_question,
        road_1_button,
        road_1_answer,
        road_2_title,
        road_2_question,
        road_2_button,
        road_2_answer,
    ]

    start_button.click(
        fn=start_story,
        inputs=[premise, mode, max_steps, ending_tone],
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

    road_1_button.click(
        fn=ask_untaken_1,
        inputs=[road_1_question, state],
        outputs=[road_1_question, road_1_button, road_1_answer, state],
        show_progress="full",
    )

    road_2_button.click(
        fn=ask_untaken_2,
        inputs=[road_2_question, state],
        outputs=[road_2_question, road_2_button, road_2_answer, state],
        show_progress="full",
    )


if __name__ == "__main__":
    demo.queue()
    demo.launch(inbrowser=False)
