import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app
from story_engine import EndingResponse, SceneResponse, create_initial_state


def app_ending_payload() -> dict:
    return {
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
                "summary": "The PhD became a new country and a narrower freedom.",
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
                "summary": "Staying made family ordinary and precious.",
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


def app_ended_state() -> dict:
    state = create_initial_state(
        "Move to the USA for a PhD or build a family in Europe.",
        mode="strange",
        max_steps=5,
        ending_tone="direct",
    )
    state["ending"] = EndingResponse.model_validate(app_ending_payload()).model_dump()
    return state


def active_custom_state(enabled: bool = True) -> dict:
    state = create_initial_state(
        "Move to the USA for a PhD or build a family in Europe.",
        custom_choices_enabled=enabled,
    )
    branch = state["branches"]["main"]
    branch["chosen_decisions"] = ["A: Move to USA - Build a research life."]
    branch["last_choices"] = [
        {
            "id": "A",
            "label": "Stay in academia",
            "tone": "ambitious",
            "preview": "Double down on research.",
        },
        {
            "id": "B",
            "label": "Move back home",
            "tone": "tender",
            "preview": "Return to family.",
        },
        {
            "id": "C",
            "label": "Start over elsewhere",
            "tone": "risky",
            "preview": "Choose a third country.",
        },
    ]
    return state


class AppTests(unittest.TestCase):
    def test_start_story_empty_premise_matches_output_count(self):
        result = next(app.start_story("", "grounded", 6, False, "poetic"))

        self.assertEqual(len(app.outputs), len(result))

    def test_custom_choice_toggle_default_is_off(self):
        self.assertFalse(app.custom_choices_enabled.value)
        self.assertFalse(
            create_initial_state("A premise.")["custom_choices_enabled"]
        )

    def test_custom_controls_hidden_until_enabled_after_initial_choice(self):
        self.assertFalse(app.should_show_custom_choice(None))
        self.assertFalse(app.should_show_custom_choice(active_custom_state(False)))
        self.assertTrue(app.should_show_custom_choice(active_custom_state(True)))

    def test_custom_choice_validation_bounds(self):
        empty_error, _ = app.validate_custom_choice_text(" ")
        short_error, _ = app.validate_custom_choice_text("Too short")
        long_error, _ = app.validate_custom_choice_text("x" * 181)
        valid_error, valid_text = app.validate_custom_choice_text(
            "Move home and rebuild trust with my sister."
        )

        self.assertIn("Write a custom road", empty_error)
        self.assertIn("at least 20", short_error)
        self.assertIn("180 characters or fewer", long_error)
        self.assertIsNone(valid_error)
        self.assertEqual(valid_text, "Move home and rebuild trust with my sister.")

    def test_valid_custom_choice_advances_with_internal_d_choice(self):
        state = active_custom_state(True)
        captured = {}

        def fake_generate_scene(state, selected_choice=None):
            captured["selected_choice"] = selected_choice
            return (
                state,
                SceneResponse.model_validate(
                    {
                        "time_jump": "One year later",
                        "scene": "The custom road has consequences.",
                        "choices": [
                            {
                                "id": "A",
                                "label": "Repair",
                                "tone": "tender",
                                "preview": "Try to mend what broke.",
                            },
                            {
                                "id": "B",
                                "label": "Leave",
                                "tone": "uneasy",
                                "preview": "Accept the distance.",
                            },
                            {
                                "id": "C",
                                "label": "Confess",
                                "tone": "costly",
                                "preview": "Tell the difficult truth.",
                            },
                        ],
                        "memory_update": "The custom road changed the branch.",
                    }
                ),
            )

        with patch("app.generate_scene", side_effect=fake_generate_scene):
            updates = list(
                app.choose_custom_path(
                    "Move home and rebuild trust with my sister.",
                    "Current story",
                    "A card",
                    "B card",
                    "C card",
                    state,
                )
            )

        final_update = updates[-1]
        self.assertEqual(captured["selected_choice"]["id"], "D")
        self.assertEqual(captured["selected_choice"]["tone"], "self-authored")
        self.assertIn("The custom road has consequences.", final_update[0])
        self.assertTrue(final_update[10]["visible"])

    def test_invalid_custom_choice_preserves_current_scene(self):
        state = active_custom_state(True)

        result = next(
            app.choose_custom_path(
                "Too short",
                "Current story",
                "A card",
                "B card",
                "C card",
                state,
            )
        )

        self.assertEqual(result[0], "Current story")
        self.assertEqual(result[1], "A card")
        self.assertIn("at least 20", result[4])
        self.assertEqual(result[10]["value"], "Too short")

    def test_ask_second_untaken_road_uses_second_source(self):
        state = app_ended_state()

        def fake_answer(state, source, question):
            return (
                state,
                SimpleNamespace(
                    speaker="The Near Life",
                    source=source,
                    answer="I had closeness, and it cost me distance.",
                ),
            )

        with patch("app.answer_untaken_road_question", side_effect=fake_answer):
            updates = list(app.ask_untaken_2("Were you happier than me?", state))

        final_update = updates[-1]
        self.assertFalse(final_update[0]["interactive"])
        self.assertFalse(final_update[1]["interactive"])
        self.assertIn("The Near Life", final_update[2])
        self.assertIn("I had closeness", final_update[2])


if __name__ == "__main__":
    unittest.main()
