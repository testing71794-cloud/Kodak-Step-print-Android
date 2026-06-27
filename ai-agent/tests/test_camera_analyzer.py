"""Unit tests for camera view/capture analyzer (rule-based)."""

from __future__ import annotations

import sys
import textwrap
import unittest
from pathlib import Path

AGENT = Path(__file__).resolve().parents[1]
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

from analysis.camera_analyzer import CameraAnalyzer  # noqa: E402


def _write_ui_dump(path: Path, resource_ids: list[str]) -> None:
    nodes = []
    for rid in resource_ids:
        nodes.append(
            f'<node resource-id="com.kodak.steptouch:id/{rid}" class="android.widget.ImageView" clickable="true"/>'
        )
    body = textwrap.dedent(
        f"""<?xml version="1.0" encoding="UTF-8"?>
        <hierarchy>
          {''.join(nodes)}
        </hierarchy>"""
    )
    path.write_text(body.strip(), encoding="utf-8")


class CameraAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = AGENT.parent
        self.analyzer = CameraAnalyzer(self.repo, llm=None)

    def test_is_camera_flow(self) -> None:
        self.assertTrue(CameraAnalyzer.is_camera_flow("CA_01 - Enter camera mode"))
        self.assertFalse(CameraAnalyzer.is_camera_flow("ED_03 - Edit photo"))

    def test_analyze_view_pass(self) -> None:
        dump = self.repo / "ai-agent" / "tests" / "_tmp_camera_view.xml"
        _write_ui_dump(
            dump,
            ["capture_img", "imgFlipCamera", "img_camera_menu", "back_button"],
        )
        result = self.analyzer.analyze_view(ui_dump=dump, screenshot=None, flow_name="CA_01")
        self.assertEqual(result.status, "pass")
        self.assertGreaterEqual(result.confidence, 0.6)
        dump.unlink(missing_ok=True)

    def test_analyze_view_fail(self) -> None:
        dump = self.repo / "ai-agent" / "tests" / "_tmp_camera_view_fail.xml"
        _write_ui_dump(dump, ["back_button"])
        result = self.analyzer.analyze_view(ui_dump=dump, screenshot=None, flow_name="CA_01")
        self.assertEqual(result.status, "fail")
        dump.unlink(missing_ok=True)

    def test_capture_skipped_for_non_capture_flow(self) -> None:
        result = self.analyzer.analyze_capture(
            ui_dump=None,
            screenshot=None,
            flow_name="CA_01 - Enter camera mode",
        )
        self.assertEqual(result.status, "skipped")

    def test_capture_pass_with_thumbnail_id(self) -> None:
        dump = self.repo / "ai-agent" / "tests" / "_tmp_capture.xml"
        _write_ui_dump(dump, ["camera_image", "img_camera_menu"])
        result = self.analyzer.analyze_capture(
            ui_dump=dump,
            screenshot=None,
            flow_name="CA_03 - Capture with no flash",
        )
        self.assertEqual(result.status, "pass")
        dump.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
