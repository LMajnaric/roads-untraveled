import json
import unittest
from unittest.mock import patch

import story_engine
from story_engine import (
    EndingResponse,
    SceneResponse,
    create_initial_state,
    extract_json,
    generate_scene,
    get_director_card,
    get_director_context,
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
                    "summary": "The PhD became a new country, a new language, and a narrower kind of freedom.",
                    "emotional_aftertaste": "proud ache",
                },
                {
                    "source_choice": "C: Stay Local - Keep old roots close.",
                    "title": "The Near Life",
                    "summary": "Staying made family ordinary and precious, while ambition learned a smaller room.",
                    "emotional_aftertaste": "warm regret",
                },
            ],
            "memory_update": "The chosen road ended.",
        }
    )


class StoryEngineTests(unittest.TestCase):
    def test_extract_json_from_wrapped_model_output(self):
        self.assertEqual(extract_json("Here:\n```json\n{\"a\": 1}\n```"), {"a": 1})

    def test_scene_and_ending_validation(self):
        scene = parse_scene_response(scene_payload(1))
        ending = parse_ending_response(ending_payload())

        self.assertIsInstance(scene, SceneResponse)
        self.assertEqual([choice.id for choice in scene.choices], ["A", "B", "C"])
        self.assertIsInstance(ending, EndingResponse)
        self.assertEqual(len(ending.alternate_lives), 2)

    def test_scene_validation_requires_ordered_abc_choices(self):
        broken = json.loads(scene_payload(1))
        broken["choices"][1]["id"] = "A"

        with self.assertRaisesRegex(ValueError, "choices must contain exactly"):
            SceneResponse.model_validate(broken)

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
        self.assertEqual(len(state["branches"]["main"]["chosen_decisions"]), 5)
        self.assertEqual(
            [choice["label"] for choice in state["initial_roads_not_taken"]],
            ["Move to USA", "Stay Local"],
        )


if __name__ == "__main__":
    unittest.main()
