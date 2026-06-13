import os
import unittest
from unittest.mock import Mock, patch

from llm_backends import quantization


class QuantizationTests(unittest.TestCase):
    def test_resolve_quantization_defaults_to_bnb_4bit(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(quantization.resolve_quantization(), "bnb_4bit")

    def test_none_quantization_returns_no_config(self):
        self.assertIsNone(quantization.build_quantization_config("none"))

    def test_bnb_4bit_uses_nf4_bfloat16_and_double_quant(self):
        fake_config = Mock(return_value="config")

        with patch.object(quantization, "_bitsandbytes_config", fake_config):
            with patch.object(quantization, "_bfloat16", return_value="bf16"):
                self.assertEqual(
                    quantization.build_quantization_config("bnb_4bit"),
                    "config",
                )

        fake_config.assert_called_once_with(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype="bf16",
            bnb_4bit_use_double_quant=True,
        )

    def test_bnb_8bit_uses_8bit_loading(self):
        fake_config = Mock(return_value="config")

        with patch.object(quantization, "_bitsandbytes_config", fake_config):
            self.assertEqual(quantization.build_quantization_config("bnb_8bit"), "config")

        fake_config.assert_called_once_with(load_in_8bit=True)

    def test_invalid_quantization_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Unsupported ZERO_GPU_QUANTIZATION"):
            quantization.resolve_quantization("fp8")


if __name__ == "__main__":
    unittest.main()
