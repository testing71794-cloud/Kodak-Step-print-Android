"""Unit tests for AI visual validation JSON parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_AI_DIR = Path(__file__).resolve().parents[1]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from compare import extract_json_object, parse_validation_response  # noqa: E402
from models import ValidationMode, VisualValidationResult  # noqa: E402


class TestCompareParsing(unittest.TestCase):
    def test_extract_json_from_markdown_fence(self) -> None:
        raw = 'Here is output:\n```json\n{"screen":"Home","screenMatched":true,"confidence":95}\n```'
        data = extract_json_object(raw)
        self.assertEqual(data["screen"], "Home")
        self.assertTrue(data["screenMatched"])

    def test_parse_single_response(self) -> None:
        raw = (
            '{"screen":"Edit","screenMatched":true,"confidence":88,'
            '"missingElements":[],"unexpectedElements":[],"ocrIssues":["clipped label"],'
            '"layoutIssues":[],"popupDetected":false,"recommendation":"ok"}'
        )
        result = parse_validation_response(raw, mode=ValidationMode.SINGLE)
        self.assertEqual(result.screen, "Edit")
        self.assertEqual(result.confidence, 88)
        self.assertEqual(result.ocr_issues, ["clipped label"])
        self.assertFalse(result.popup_detected)

    def test_parse_compare_response(self) -> None:
        raw = (
            '{"screen":"Gallery","screenMatched":false,"confidence":70,"similarityScore":62,'
            '"differences":["toolbar icon missing"],"missingElements":["Print"],'
            '"unexpectedElements":[],"ocrIssues":[],"layoutIssues":[],"popupDetected":false,'
            '"recommendation":"check toolbar"}'
        )
        result = parse_validation_response(raw, mode=ValidationMode.COMPARE)
        self.assertEqual(result.similarity_score, 62)
        self.assertEqual(result.differences, ["toolbar icon missing"])

    def test_skipped_json_contract(self) -> None:
        skipped = VisualValidationResult(status="AI_SKIPPED", error="timeout")
        self.assertEqual(skipped.to_json_dict(), {"status": "AI_SKIPPED", "error": "timeout"})


if __name__ == "__main__":
    unittest.main()
