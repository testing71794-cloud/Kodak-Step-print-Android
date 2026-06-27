"""Decide when app relaunch is required vs resume from checkpoint."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RelaunchDecision:
    should_relaunch: bool
    reason: str


CRASH_MARKERS = ("crash", "anr", "not responding", "process died", "force close")
NAV_FAILURE = ("cannot navigate", "navigation failed", "stuck", "unknown screen")


def evaluate_relaunch(
    *,
    failure_message: str,
    recovery_exhausted: bool,
    explicit_clean_state_required: bool = False,
) -> RelaunchDecision:
    msg = (failure_message or "").lower()
    if explicit_clean_state_required:
        return RelaunchDecision(True, "Test requires clean application state")
    if any(m in msg for m in CRASH_MARKERS):
        return RelaunchDecision(True, "Application crash or ANR detected")
    if recovery_exhausted and any(m in msg for m in NAV_FAILURE):
        return RelaunchDecision(True, "Navigation unrecoverable — relaunch faster than retry")
    if recovery_exhausted:
        return RelaunchDecision(True, "Recovery exhausted — controlled relaunch")
    return RelaunchDecision(False, "Resume from current session state")
