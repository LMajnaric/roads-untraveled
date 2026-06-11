import json
import unittest
from unittest.mock import patch

import story_engine
from story_engine import (
    EndingResponse,
    RoadQuestionResponse,
    SceneResponse,
    answer_untaken_road_question,
    create_initial_state,
    extract_json,
    generate_scene,
    get_director_card,
    get_director_context,
    get_ending_markdown,
    get_shadow_simulation_log,
    parse_ending_response,
    parse_scene_response,
)


def scene_payload(index: int, labels: tuple[str, str, str] | None = None) -> str:
    labels = labels or (
        f"Road {index}A",
        f"Road {index}B",
        f"Road {index}C",
    )
    return json.dumps(
        {
            "time_jump": f"{index} years later",
            "scene": f"Scene {index}",
            "choices": [
                {
                    "id": "A",
                    "label": labels[0],
                    "tone": "hopeful",
                    "preview": f"Preview {index}A.",
                },
                {
                    "id": "B",
                    "label": labels[1],
                    "tone": "uneasy",
                    "preview": f"Preview {index}B.",
                },
                {
                    "id": "C",
                    "label": labels[2],
                    "tone": "tender",
                    "preview": f"Preview {index}C.",
                },
            ],
            "memory_update": f"Memory {index}",
        }
    )


def ending_payload() -> str:
    return json.dumps(
        {
            "time_jump": "Twenty years later",
            "final_scene": "The chosen road reaches its quiet ending.",
            "chosen_life_summary": "A life shaped by the selected road.",
            "alternate_lives": [
                {
                    "source_choice": "A: Move to USA - Build a research life.",
                    "title": "The Research Life",
                    "turning_points": [
                        "Won a fellowship in Boston.",
                        "Chose tenure over coming home.",
                        "Ended a marriage beside packed boxes.",
                    ],
                    "summary": "The PhD became a new country, a new language, and a narrower kind of freedom.",
                    "emotional_aftertaste": "proud ache",
                },
                {
                    "source_choice": "C: Stay Local - Keep old roots close.",
                    "title": "The Near Life",
                    "turning_points": [
                        "Refused a job across the sea.",
                        "Nursed his father through winter.",
                        "Inherited the apartment and its silence.",
                    ],
                    "summary": "Staying made family ordinary and precious, while ambition learned a smaller room.",
                    "emotional_aftertaste": "warm regret",
                },
            ],
            "road_conversation": [
                {
                    "speaker": "The lived road",
                    "source": "chosen",
                    "line": "I kept the door I could bear to close.",
                },
                {
                    "speaker": "The research life",
                    "source": "untaken_1",
                    "line": "I became distance, but distance became a language.",
                },
                {
                    "speaker": "The near life",
                    "source": "untaken_2",
                    "line": "I stayed close enough to lose different things.",
                },
            ],
            "memory_update": "The chosen road ended.",
        }
    )


def road_question_payload(source: str = "untaken_1") -> str:
    return json.dumps(
        {
            "speaker": "The Research Life",
            "source": source,
            "answer": "I had the clean terror of distance, and it taught me what ambition could not hold.",
        }
    )


def ended_state() -> dict:
    state = create_initial_state(
        "Move to the USA for a PhD or build a family in Europe.",
        mode="strange",
        max_steps=5,
        ending_tone="direct",
    )
    state["ending"] = EndingResponse.model_validate(
        json.loads(ending_payload())
    ).model_dump()
    state["branches"]["main"]["chosen_decisions"] = [
        "B: Have Children - Stay near family.",
        "A: Accept the cost - Leave the old home.",
    ]
    return state


class StoryEngineTests(unittest.TestCase):
    def test_extract_json_from_wrapped_model_output(self):
        self.assertEqual(extract_json("Here:\n```json\n{\"a\": 1}\n```"), {"a": 1})

    def test_scene_and_ending_validation(self):
        scene = parse_scene_response(scene_payload(1))
        ending = parse_ending_response(ending_payload())
        road_answer = RoadQuestionResponse.model_validate(
            json.loads(road_question_payload())
        )

        self.assertIsInstance(scene, SceneResponse)
        self.assertEqual([choice.id for choice in scene.choices], ["A", "B", "C"])
        self.assertIsInstance(ending, EndingResponse)
        self.assertEqual(len(ending.alternate_lives), 2)
        self.assertEqual(len(ending.alternate_lives[0].turning_points), 3)
        self.assertEqual(len(ending.road_conversation), 3)
        self.assertEqual(road_answer.source, "untaken_1")

    def test_ending_validation_requires_three_turning_points(self):
        missing = json.loads(ending_payload())
        del missing["alternate_lives"][0]["turning_points"]

        with self.assertRaises(ValueError):
            EndingResponse.model_validate(missing)

        too_few = json.loads(ending_payload())
        too_few["alternate_lives"][0]["turning_points"] = [
            "Won a fellowship in Boston.",
            "Chose tenure over coming home.",
        ]

        with self.assertRaises(ValueError):
            EndingResponse.model_validate(too_few)

    def test_ending_markdown_hides_turning_points(self):
        ending = parse_ending_response(ending_payload())
        markdown = get_ending_markdown(ending)

        self.assertIn("The Research Life", markdown)
        self.assertIn("The PhD became a new country", markdown)
        self.assertNotIn("Won a fellowship in Boston", markdown)
        self.assertNotIn("Nursed his father through winter", markdown)

    def test_shadow_simulation_log_shows_hidden_turning_points(self):
        ending = parse_ending_response(ending_payload())
        log_text = get_shadow_simulation_log(ending)

        self.assertIn("--- SHADOW SIMULATION ---", log_text)
        self.assertIn("Untaken road 1: The Research Life", log_text)
        self.assertIn("Began from: A: Move to USA", log_text)
        self.assertIn("1. Won a fellowship in Boston.", log_text)
        self.assertIn("2. Nursed his father through winter.", log_text)
        self.assertIn("--- END SHADOW SIMULATION ---", log_text)

    def test_create_initial_state_stores_ending_tone(self):
        state = create_initial_state(
            "A life begins.",
            mode="cinematic",
            max_steps=6,
            ending_tone="direct",
        )

        self.assertEqual(state["ending_tone"], "direct")

    def test_unknown_ending_tone_defaults_to_poetic(self):
        state = create_initial_state(
            "A life begins.",
            mode="grounded",
            max_steps=6,
            ending_tone="loud",
        )

        self.assertEqual(state["ending_tone"], "poetic")

    def test_create_initial_state_stores_custom_choice_toggle(self):
        default_state = create_initial_state("A life begins.")
        enabled_state = create_initial_state(
            "A life begins.",
            custom_choices_enabled=True,
        )

        self.assertFalse(default_state["custom_choices_enabled"])
        self.assertTrue(enabled_state["custom_choices_enabled"])

    def test_custom_choice_prompt_guidance_is_included(self):
        captured = {}

        def fake_generate_chat_response(messages, **kwargs):
            captured["prompt"] = messages[-1]["content"]
            return scene_payload(1)

        state = create_initial_state(
            "Move to the USA for a PhD or build a family in Europe.",
            custom_choices_enabled=True,
        )
        state["branches"]["main"]["chosen_decisions"] = [
            "A: Move to USA - Build a research life."
        ]

        with patch.object(
            story_engine,
            "generate_chat_response",
            fake_generate_chat_response,
        ):
            generate_scene(
                state,
                selected_choice={
                    "id": "D",
                    "label": "Move home and rebuild trust with my sister.",
                    "tone": "self-authored",
                    "preview": "A user-authored road.",
                },
            )

        self.assertIn("The selected choice was written by the user", captured["prompt"])
        self.assertIn("consequence-free escape hatch", captured["prompt"])
        self.assertIn("Move home and rebuild trust", captured["prompt"])

    def test_scene_validation_requires_ordered_abc_choices(self):
        broken = json.loads(scene_payload(1))
        broken["choices"][1]["id"] = "A"

        with self.assertRaisesRegex(ValueError, "choices must contain exactly"):
            SceneResponse.model_validate(broken)

    def test_ending_validation_requires_ordered_road_conversation(self):
        broken = json.loads(ending_payload())
        broken["road_conversation"][1]["source"] = "chosen"

        with self.assertRaisesRegex(ValueError, "road_conversation must contain"):
            EndingResponse.model_validate(broken)

    def test_director_context_contains_mode_specific_external_events(self):
        grounded = get_director_context(2, "grounded", 6)
        strange = get_director_context(2, "strange", 6)
        cinematic = get_director_context(2, "cinematic", 6)

        self.assertIn("Required external event", grounded)
        self.assertIn("parent or older relative's health declines", grounded)
        self.assertIn("impossible pressure", strange)
        self.assertIn("paths the protagonist did not choose", strange)
        self.assertIn("public failure, investigation, accident, or betrayal", cinematic)
        self.assertIn("Verticality rule", cinematic)

    def test_generate_scene_prompt_includes_director_card(self):
        captured_prompt = ""

        def fake_generate_chat_response(messages, *args, **kwargs):
            nonlocal captured_prompt
            captured_prompt = messages[-1]["content"]
            return scene_payload(0)

        with patch.object(
            story_engine,
            "generate_chat_response",
            fake_generate_chat_response,
        ):
            state = create_initial_state(
                "A software engineer considers nuclear work in Stockholm.",
                mode="strange",
                max_steps=6,
            )
            generate_scene(state)

        self.assertIn("Required external event", captured_prompt)
        self.assertIn(get_director_card(0, "strange"), captured_prompt)
        self.assertIn("At least one choice must risk permanent loss", captured_prompt)

    def test_generate_ending_prompt_includes_ending_tone(self):
        captured_prompt = ""

        def fake_generate_chat_response(messages, *args, **kwargs):
            nonlocal captured_prompt
            captured_prompt = messages[-1]["content"]
            return ending_payload()

        state = create_initial_state(
            "A software engineer considers nuclear work in Stockholm.",
            mode="strange",
            max_steps=5,
            ending_tone="weird",
        )
        state["initial_chosen_choice"] = "B: Have Children - Stay near family."
        state["initial_roads_not_taken"] = [
            {
                "id": "A",
                "label": "Move to USA",
                "tone": "ambitious",
                "preview": "Build a research life.",
            },
            {
                "id": "C",
                "label": "Stay Local",
                "tone": "rooted",
                "preview": "Keep old roots close.",
            },
        ]
        branch = state["branches"]["main"]
        branch["chosen_decisions"] = ["B: Have Children - Stay near family."]

        with patch.object(
            story_engine,
            "generate_chat_response",
            fake_generate_chat_response,
        ):
            story_engine.generate_ending(
                state,
                branch,
                "A: Final Choice - Accept the cost.",
            )

        self.assertIn("Ending conversation tone:\nweird", captured_prompt)
        self.assertIn("chosen, untaken_1, untaken_2", captured_prompt)
        self.assertIn("weird is uncanny and playful", captured_prompt)
        self.assertIn("exactly 3 hidden turning points", captured_prompt)
        self.assertIn("maximum 12 words", captured_prompt)
        self.assertIn("Do not write full scenes for untaken roads", captured_prompt)

    def test_answer_untaken_road_question_rejects_invalid_state(self):
        with self.assertRaisesRegex(ValueError, "No ending"):
            answer_untaken_road_question(
                create_initial_state("A life begins."),
                "untaken_1",
                "Were you happier?",
            )

        with self.assertRaisesRegex(ValueError, "Question cannot be empty"):
            answer_untaken_road_question(ended_state(), "untaken_1", "   ")

        with self.assertRaisesRegex(ValueError, "source must be"):
            answer_untaken_road_question(
                ended_state(),
                "chosen",
                "Were you happier?",
            )

        state = ended_state()
        state["road_questions"]["untaken_1"]["used"] = True
        with self.assertRaisesRegex(ValueError, "already answered"):
            answer_untaken_road_question(
                state,
                "untaken_1",
                "Were you happier?",
            )

    def test_answer_untaken_road_question_prompt_and_state_update(self):
        captured_prompt = ""

        def fake_generate_chat_response(messages, *args, **kwargs):
            nonlocal captured_prompt
            captured_prompt = messages[-1]["content"]
            return road_question_payload("untaken_1")

        state = ended_state()

        with patch.object(
            story_engine,
            "generate_chat_response",
            fake_generate_chat_response,
        ):
            state, answer = answer_untaken_road_question(
                state,
                "untaken_1",
                "Were you happier than me?",
            )

        self.assertIsInstance(answer, RoadQuestionResponse)
        self.assertEqual(answer.source, "untaken_1")
        self.assertTrue(state["road_questions"]["untaken_1"]["used"])
        self.assertEqual(
            state["road_questions"]["untaken_1"]["question"],
            "Were you happier than me?",
        )
        self.assertEqual(
            state["road_questions"]["untaken_1"]["answer"]["speaker"],
            "The Research Life",
        )
        self.assertIn("title: The Research Life", captured_prompt)
        self.assertIn("source: untaken_1", captured_prompt)
        self.assertIn("Were you happier than me?", captured_prompt)
        self.assertIn("The Near Life", captured_prompt)
        self.assertIn("Won a fellowship in Boston", captured_prompt)
        self.assertIn("I kept the door I could bear to close.", captured_prompt)
        self.assertIn("Ending tone:\ndirect", captured_prompt)

    def test_initial_roads_not_taken_seed_the_ending(self):
        responses = iter(
            [
                scene_payload(0, ("Move to USA", "Have Children", "Stay Local")),
                scene_payload(1, ("Big Internship", "New Mentor", "Change Cities")),
                scene_payload(2, ("Corporate Offer", "Publish Book", "Caregiving")),
                scene_payload(3, ("Buy Apartment", "Start Company", "Leave Again")),
                scene_payload(4, ("Public Success", "Private Repair", "Begin Over")),
                ending_payload(),
            ]
        )

        def fake_generate_chat_response(*args, **kwargs):
            return next(responses)

        with patch.object(
            story_engine,
            "generate_chat_response",
            fake_generate_chat_response,
        ):
            state = create_initial_state(
                "Move to the USA for a PhD or build a family in Europe.",
                mode="grounded",
                max_steps=5,
            )

            state, first_scene = generate_scene(state)
            self.assertIsInstance(first_scene, SceneResponse)

            state, second_scene = generate_scene(
                state,
                selected_choice=first_scene.choices[1].model_dump(),
            )
            self.assertIsInstance(second_scene, SceneResponse)
            self.assertEqual(
                [choice["label"] for choice in state["initial_roads_not_taken"]],
                ["Move to USA", "Stay Local"],
            )

            state, third_scene = generate_scene(
                state,
                selected_choice=second_scene.choices[0].model_dump(),
            )
            state, fourth_scene = generate_scene(
                state,
                selected_choice=third_scene.choices[1].model_dump(),
            )
            state, fifth_scene = generate_scene(
                state,
                selected_choice=fourth_scene.choices[2].model_dump(),
            )
            state, ending = generate_scene(
                state,
                selected_choice=fifth_scene.choices[0].model_dump(),
            )

        self.assertIsInstance(ending, EndingResponse)
        self.assertTrue(state["branches"]["main"]["ended"])
        self.assertEqual(state["branches"]["main"]["last_choices"], [])
        self.assertIsNotNone(state["ending"])
        self.assertFalse(state["road_questions"]["untaken_1"]["used"])
        self.assertEqual(len(state["branches"]["main"]["chosen_decisions"]), 5)
        self.assertEqual(
            [choice["label"] for choice in state["initial_roads_not_taken"]],
            ["Move to USA", "Stay Local"],
        )


if __name__ == "__main__":
    unittest.main()
