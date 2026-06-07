import gradio as gr

print("app.py is being executed")

from story_engine import (
    create_initial_state,
    generate_scene,
    format_scene_for_ui,
)


def start_story(premise: str):
    if not premise.strip():
        return "Please enter a premise first.", None

    state = create_initial_state(premise)
    state, scene_response = generate_scene(state)

    return format_scene_for_ui(scene_response), state


def choose_path(choice_id: str, state: dict):
    if state is None:
        return "Start a story first.", state

    branch = state["branches"][state["active_branch"]]
    choices = branch.get("last_choices", [])

    selected = next((choice for choice in choices if choice["id"] == choice_id), None)

    if selected is None:
        return "That choice does not exist for the current scene.", state

    selected_text = f'{selected["id"]}: {selected["label"]}'
    state, scene_response = generate_scene(state, selected_choice=selected_text)

    return format_scene_for_ui(scene_response), state


with gr.Blocks(title="Roads Untraveled") as demo:
    gr.Markdown("# Roads Untraveled")
    gr.Markdown("Choose one path. The others still echo.")

    state = gr.State(None)

    premise = gr.Textbox(
        label="Story premise",
        placeholder="A robotics engineer receives an offer that would change the rest of his life...",
        lines=3,
    )

    start_button = gr.Button("Begin story")

    output = gr.Markdown()

    with gr.Row():
        choice_a = gr.Button("Choose A")
        choice_b = gr.Button("Choose B")
        choice_c = gr.Button("Choose C")

    start_button.click(
        fn=start_story,
        inputs=[premise],
        outputs=[output, state],
    )

    choice_a.click(
        fn=lambda s: choose_path("A", s),
        inputs=[state],
        outputs=[output, state],
    )

    choice_b.click(
        fn=lambda s: choose_path("B", s),
        inputs=[state],
        outputs=[output, state],
    )

    choice_c.click(
        fn=lambda s: choose_path("C", s),
        inputs=[state],
        outputs=[output, state],
    )


if __name__ == "__main__":
    print("Starting Roads Untraveled Gradio app...")

    demo.queue()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,
        debug=True,
        show_error=True,
    )