import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import llm_client
from llm_backends.message_format import (
    extract_generated_text,
    messages_to_prompt,
    normalize_messages,
)


class LlmBackendTests(unittest.TestCase):
    def tearDown(self):
        llm_client._load_backend.cache_clear()

    def test_backend_selection_uses_explicit_env(self):
        self.assertEqual(llm_client.resolve_backend_name("llamacpp"), "llamacpp")
        self.assertEqual(llm_client.resolve_backend_name("openai"), "openai")
        self.assertEqual(llm_client.resolve_backend_name("zerogpu"), "zerogpu")

    def test_backend_selection_defaults_to_llamacpp_locally(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(llm_client.resolve_backend_name(), "llamacpp")

    def test_backend_selection_defaults_to_zerogpu_on_hf_space(self):
        with patch.dict(os.environ, {"SPACE_ID": "user/roads-untraveled"}, clear=True):
            self.assertEqual(llm_client.resolve_backend_name(), "zerogpu")

    def test_generate_chat_response_loads_selected_backend(self):
        fake_backend = SimpleNamespace(
            generate_chat_response=lambda messages, temperature, max_tokens: "ok"
        )

        with patch.dict(os.environ, {"LLM_BACKEND": "llamacpp"}, clear=True):
            with patch("llm_client.importlib.import_module", return_value=fake_backend) as import_module:
                self.assertEqual(
                    llm_client.generate_chat_response(
                        [{"role": "user", "content": "Hello"}],
                        temperature=0.1,
                        max_tokens=8,
                    ),
                    "ok",
                )

        import_module.assert_called_once_with("llm_backends.openai_compatible")

    def test_normalize_messages_handles_plain_and_multimodal_content(self):
        messages = normalize_messages(
            [
                {"role": "system", "content": "Rules"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this"},
                        {"type": "image_url", "image_url": {"url": "ignored"}},
                    ],
                },
            ]
        )

        self.assertEqual(
            messages,
            [
                {"role": "system", "content": "Rules"},
                {"role": "user", "content": "Describe this"},
            ],
        )

    def test_messages_to_prompt_uses_tokenizer_chat_template_when_available(self):
        tokenizer = SimpleNamespace(
            apply_chat_template=lambda messages, tokenize, add_generation_prompt: "templated"
        )

        self.assertEqual(
            messages_to_prompt(
                [{"role": "user", "content": "Begin"}],
                tokenizer=tokenizer,
            ),
            "templated",
        )

    def test_messages_to_prompt_falls_back_to_text_prompt(self):
        prompt = messages_to_prompt(
            [
                {"role": "system", "content": "Rules"},
                {"role": "user", "content": "Begin"},
            ]
        )

        self.assertIn("System: Rules", prompt)
        self.assertIn("User: Begin", prompt)
        self.assertTrue(prompt.endswith("Assistant:"))

    def test_extract_generated_text_handles_common_pipeline_shapes(self):
        self.assertEqual(
            extract_generated_text([{"generated_text": "  story  "}]),
            "story",
        )
        self.assertEqual(
            extract_generated_text(
                [
                    {
                        "generated_text": [
                            {"role": "user", "content": "Question"},
                            {"role": "assistant", "content": "Answer"},
                        ]
                    }
                ]
            ),
            "Answer",
        )
        self.assertEqual(extract_generated_text({"text": "Fallback"}), "Fallback")


if __name__ == "__main__":
    unittest.main()
