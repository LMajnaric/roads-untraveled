import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app
from story_engine import EndingResponse, create_initial_state


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


class AppTests(unittest.TestCase):
    def test_start_story_empty_premise_matches_output_count(self):
        result = next(app.start_story("", "grounded", 6, "poetic"))

        self.assertEqual(len(app.outputs), len(result))

    def test_available_road_question_choices_use_titles_and_skip_used_roads(self):
        state = app_ended_state()

        self.assertEqual(
            app.get_available_road_question_choices(state),
            [
                "untaken_1: The Research Life",
                "untaken_2: The Near Life",
            ],
        )

        state["road_questions"]["untaken_1"]["used"] = True

        self.assertEqual(
            app.get_available_road_question_choices(state),
            ["untaken_2: The Near Life"],
        )

    def test_selected_untaken_road_question_can_answer_second_road(self):
        state = app_ended_state()

        def fake_answer(state, source, question):
            state["road_questions"][source]["used"] = True
            state["road_questions"][source]["question"] = question
            state["road_questions"][source]["answer"] = {
                "speaker": "The Near Life",
                "source": source,
                "answer": "I had closeness, and it cost me distance.",
            }
            return state, SimpleNamespace(speaker="The Near Life")

        with patch("app.answer_untaken_road_question", side_effect=fake_answer):
            updates = list(
                app.ask_selected_untaken_road(
                    "untaken_2: The Near Life",
                    "Were you happier than me?",
                    state,
                )
            )

        final_update = updates[-1]
        updated_state = final_update[-1]

        self.assertIn("untaken_1: The Research Life", final_update[0]["choices"])
        self.assertEqual(final_update[0]["value"], "untaken_1: The Research Life")
        self.assertEqual(final_update[3], "The Near Life has answered.")
        self.assertEqual(final_update[4], "")
        self.assertIn("I had closeness", final_update[5])
        self.assertTrue(updated_state["road_questions"]["untaken_2"]["used"])


if __name__ == "__main__":
    unittest.main()
