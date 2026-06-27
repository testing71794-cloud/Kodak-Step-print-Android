"""Vision + OCR + Screen classification agents."""

from __future__ import annotations

from agents.base import AgentState
from integrations.adb_client import ADBClient
from ocr.ocr_engine import extract_text
from ui_parser.hierarchy_parser import parse_ui_dump
from vision.screen_capture import VisionEngine


class VisionAgent:
    def __init__(self, vision: VisionEngine) -> None:
        self.vision = vision

    def run(self, state: AgentState) -> AgentState:
        cap = self.vision.capture(f"step_{state.steps}")
        state.screenshot = cap.screenshot_path
        state.ui_dump = cap.ui_dump_path
        state.decision["focus"] = cap.focus_line
        state.log(f"Vision: screenshot={cap.screenshot_path}")
        return state


class OCRAgent:
    def run(self, state: AgentState) -> AgentState:
        text = extract_text(state.screenshot) if state.screenshot else ""
        state.decision["ocr_text"] = text[:2000]
        state.log(f"OCR: chars={len(text)}")
        return state


class ScreenClassifierAgent:
    def run(self, state: AgentState) -> AgentState:
        elements = parse_ui_dump(state.ui_dump) if state.ui_dump else []
        labels = [e.text for e in elements if e.text][:15]
        state.decision["ui_labels"] = labels
        state.decision["ui_element_count"] = len(elements)
        state.log(f"ScreenClassifier: elements={len(elements)}")
        return state
