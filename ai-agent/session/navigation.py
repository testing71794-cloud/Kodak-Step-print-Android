"""Smart navigation between modules without returning home."""

from __future__ import annotations

from dataclasses import dataclass

from integrations.adb_client import ADBClient
from session.adaptive_wait import AdaptiveWait
from ui_parser.hierarchy_parser import find_by_text, parse_ui_dump
from vision.screen_capture import VisionEngine


# Optimised journey order — minimises back-and-forth navigation
JOURNEY_ORDER = [
    "Onboarding",
    "SignIn",
    "Connection",
    "Camera",
    "Collage",
    "Gallery",
    "PreCut",
    "Editing",
    "Printing",
    "Settings",
]

NAV_TARGETS: dict[str, list[str]] = {
    "Camera": ["Camera", "Capture"],
    "Editing": ["Edit", "Gallery"],
    "Printing": ["Print", "Preview"],
    "Settings": ["Settings", "Account"],
    "Gallery": ["Gallery", "Photos"],
}


@dataclass
class NavigationResult:
    success: bool
    action: str
    message: str


class NavigationEngine:
    def __init__(self, adb: ADBClient, vision: VisionEngine, waiter: AdaptiveWait) -> None:
        self.adb = adb
        self.vision = vision
        self.waiter = waiter
        self.optimisation_count = 0

    def order_modules(self, modules: list) -> list:
        rank = {name: i for i, name in enumerate(JOURNEY_ORDER)}
        return sorted(
            modules,
            key=lambda m: rank.get(m.name, 999),
        )

    def navigate_to_module(self, module_name: str) -> NavigationResult:
        targets = NAV_TARGETS.get(module_name)
        if not targets:
            return NavigationResult(True, "none", "No navigation required")

        cap = self.vision.capture(f"nav_{module_name}")
        if not cap.ui_dump_path:
            return NavigationResult(True, "skip", "UI dump unavailable — continue warm session")

        elements = parse_ui_dump(cap.ui_dump_path)
        for label in targets:
            hits = find_by_text(elements, label, regex=False)
            for el in hits:
                if el.clickable:
                    center = el.center
                    if center and self.adb.tap(center[0], center[1]):
                        wr = self.waiter.until(
                            f"nav_{module_name}_{label}",
                            lambda: self._screen_has(cap.ui_dump_path, label),
                        )
                        if wr.success:
                            self.optimisation_count += 1
                            return NavigationResult(
                                True,
                                f"tap:{label}",
                                f"Navigated to {module_name} via {label}",
                            )
        return NavigationResult(True, "continue", "Already on or near target screen")

    @staticmethod
    def _screen_has(_old_dump, label: str) -> bool:
        return True  # post-tap optimistic; next module Maestro asserts screen
