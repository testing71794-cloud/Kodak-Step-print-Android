"""Multi-source decision engine with confidence scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from integrations.llm_client import LLMClient
from ocr.ocr_engine import extract_text
from ui_parser.hierarchy_parser import UIElement, find_by_text, parse_ui_dump


@dataclass
class Decision:
    screen: str
    reason: str
    options: list[str]
    chosen_action: str
    confidence: float
    root_cause: str = ""
    suggested_fix: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class DecisionEngine:
    POPUP_PATTERNS = [
        (r"allow|while using|only this time", "tap_allow", 0.85),
        (r"deny|don't allow", "tap_deny", 0.8),
        (r"ok|got it|dismiss|close", "dismiss_popup", 0.82),
        (r"bluetooth|pair|connect", "handle_bluetooth", 0.75),
        (r"printer|scan|searching", "rescan_printers", 0.7),
        (r"paper out|out of paper", "inform_paper_out", 0.9),
        (r"battery.*low", "inform_battery_low", 0.88),
        (r"firmware", "handle_firmware_popup", 0.8),
    ]

    def __init__(
        self,
        llm: LLMClient,
        app_profile: dict[str, Any],
        min_confidence_for_llm: float = 0.55,
    ) -> None:
        self.llm = llm
        self.app_profile = app_profile
        self.min_confidence_for_llm = min_confidence_for_llm

    def classify_screen(
        self,
        *,
        ui_dump: Path | None,
        screenshot: Path | None,
        maestro_error: str = "",
        historical: list[dict[str, Any]] | None = None,
    ) -> Decision:
        elements = parse_ui_dump(ui_dump) if ui_dump else []
        ocr_text = extract_text(screenshot) if screenshot else ""
        visible_text = " ".join(
            filter(None, [el.text for el in elements if el.text] + [ocr_text, maestro_error])
        )
        screen = self._infer_screen(visible_text, elements)
        options: list[str] = []
        best_action = "wait_and_retry"
        best_conf = 0.35
        root_cause = maestro_error or "Unknown UI state"
        suggested_fix = "Capture fresh UI dump and retry."

        for pattern, action, conf in self.POPUP_PATTERNS:
            if re.search(pattern, visible_text, re.I):
                options.append(action)
                if conf > best_conf:
                    best_action = action
                    best_conf = conf
                    root_cause = f"Matched pattern: {pattern}"
                    suggested_fix = self._fix_for_action(action)

        for popup in self.app_profile.get("known_popups") or []:
            pat = popup.get("pattern", "")
            if pat and re.search(pat, visible_text, re.I):
                action = f"app_rule:{popup.get('action', 'dismiss')}"
                options.append(action)
                best_action = action
                best_conf = max(best_conf, 0.8)
                root_cause = f"Known popup: {pat}"
                suggested_fix = popup.get("recommendation", "Follow app-specific popup rule.")

        tap_target = self._find_recovery_tap(best_action, elements)
        if tap_target:
            best_action = f"tap:{tap_target.text or tap_target.content_desc}"
            best_conf = min(0.95, best_conf + 0.05)

        if best_conf < self.min_confidence_for_llm and self.llm.available and best_action == "wait_and_retry":
            llm_dec = self._llm_advise(visible_text, maestro_error, historical or [])
            if llm_dec:
                return llm_dec

        reason = (
            f"Screen={screen!r}; signals=ui({len(elements)}) ocr({len(ocr_text)}) "
            f"error={maestro_error[:120]!r}"
        )
        return Decision(
            screen=screen,
            reason=reason,
            options=options or ["wait_and_retry"],
            chosen_action=best_action,
            confidence=best_conf,
            root_cause=root_cause,
            suggested_fix=suggested_fix,
            metadata={"visible_text_sample": visible_text[:500]},
        )

    def _infer_screen(self, text: str, elements: list[UIElement]) -> str:
        workflows = (self.app_profile.get("workflows") or {}).items()
        for name, wf in workflows:
            for scr in wf.get("entry_screens") or []:
                if scr.lower() in text.lower():
                    return f"{name}:{scr}"
        if "gallery" in text.lower():
            return "gallery"
        if elements and not text.strip():
            return "unknown_graphical"
        return "unknown"

    def _find_recovery_tap(self, action: str, elements: list[UIElement]) -> UIElement | None:
        if action.startswith("tap:"):
            return None
        if "allow" in action:
            hits = find_by_text(elements, r"allow|while using|ok", regex=True)
            return hits[0] if hits else None
        if "dismiss" in action or action == "wait_and_retry":
            hits = find_by_text(elements, r"ok|got it|close|dismiss|cancel", regex=True)
            return hits[0] if hits else None
        return None

    def _fix_for_action(self, action: str) -> str:
        fixes = {
            "tap_allow": "Grant permission when prompted; verify system dialog.",
            "dismiss_popup": "Dismiss blocking dialog and resume flow.",
            "rescan_printers": "Ensure printer powered on, Bluetooth enabled, retry scan.",
            "handle_bluetooth": "Toggle Bluetooth or move closer to printer.",
            "inform_paper_out": "Reload paper in printer tray.",
            "inform_battery_low": "Charge printer before pairing/printing.",
            "handle_firmware_popup": "Complete or defer firmware update per test policy.",
        }
        return fixes.get(action, "Review screenshot and UI hierarchy.")

    def _llm_advise(
        self, visible_text: str, maestro_error: str, historical: list[dict[str, Any]]
    ) -> Decision | None:
        system = (
            "You are a senior mobile QA engineer for Kodak Step Print. "
            "Respond in JSON with keys: screen, root_cause, suggested_fix, chosen_action, confidence (0-1)."
        )
        user = (
            f"Visible UI text:\n{visible_text[:3000]}\n\n"
            f"Maestro error:\n{maestro_error}\n\n"
            f"Historical hints:\n{historical[:3]}"
        )
        resp = self.llm.chat(system, user)
        content = resp.get("content", "")
        if not content:
            return None
        try:
            import json

            m = re.search(r"\{.*\}", content, re.S)
            data = json.loads(m.group(0)) if m else {}
            return Decision(
                screen=str(data.get("screen", "llm_inferred")),
                reason="LLM advisory (low rule confidence)",
                options=[str(data.get("chosen_action", "wait_and_retry"))],
                chosen_action=str(data.get("chosen_action", "wait_and_retry")),
                confidence=float(data.get("confidence", 0.5)),
                root_cause=str(data.get("root_cause", maestro_error)),
                suggested_fix=str(data.get("suggested_fix", "")),
                metadata={"llm": True},
            )
        except Exception:
            return None
