"""Camera view + capture analysis using UI hierarchy, OCR, and optional LLM."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from integrations.llm_client import LLMClient
from ocr.ocr_engine import extract_text
from ui_parser.hierarchy_parser import find_by_resource_id, find_by_text, parse_ui_dump


@dataclass
class CameraPhaseResult:
    phase: str
    status: str
    confidence: float
    summary: str
    missing_signals: list[str] = field(default_factory=list)
    found_signals: list[str] = field(default_factory=list)
    screenshot: str = ""
    ui_dump: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ImportError:
        return json.loads(text) if text.strip().startswith("{") else {}


class CameraAnalyzer:
    """Rule-first camera view/capture analysis; LLM only when rules are inconclusive."""

    def __init__(
        self,
        repo_root: Path,
        *,
        llm: LLMClient | None = None,
        config_path: Path | None = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        cfg_path = config_path or (self.repo_root / "ai-agent" / "config" / "camera_analysis.yaml")
        raw = _load_yaml(cfg_path)
        self.cfg = raw.get("camera") or {}
        self.llm = llm
        llm_cfg = self.cfg.get("llm") or {}
        self.llm_enabled = bool(llm_cfg.get("enabled", True))
        self.min_rule_confidence = float(llm_cfg.get("min_rule_confidence", 0.65))

    @staticmethod
    def is_camera_flow(flow_name: str) -> bool:
        name = (flow_name or "").strip()
        if not name:
            return False
        if name.upper().startswith("CA_"):
            return True
        return "camera" in name.lower()

    @staticmethod
    def is_capture_flow(flow_name: str) -> bool:
        low = (flow_name or "").lower()
        if "capture" in low:
            return True
        m = re.search(r"\bCA_(0[3-9]|10|E0?2)\b", flow_name or "", re.I)
        return bool(m)

    def analyze_view(
        self,
        *,
        screenshot: Path | None,
        ui_dump: Path | None,
        flow_name: str = "",
    ) -> CameraPhaseResult:
        elements = parse_ui_dump(ui_dump) if ui_dump else []
        ocr = extract_text(screenshot) if screenshot and screenshot.is_file() else ""
        view_cfg = self.cfg.get("view") or {}
        required = [str(x) for x in (view_cfg.get("required_resource_ids") or [])]
        optional = [str(x) for x in (view_cfg.get("optional_resource_ids") or [])]
        text_signals = [str(x) for x in (view_cfg.get("text_signals") or [])]
        min_hits = int(view_cfg.get("min_required_hits", 2))

        found: list[str] = []
        missing: list[str] = []
        for rid in required:
            hits = find_by_resource_id(elements, rid)
            if hits:
                found.append(rid)
            else:
                missing.append(rid)
        for rid in optional:
            if find_by_resource_id(elements, rid):
                found.append(rid)

        hay = " ".join(
            filter(
                None,
                [ocr, " ".join(e.text for e in elements if e.text), flow_name],
            )
        ).lower()
        for sig in text_signals:
            if sig.lower() in hay:
                found.append(f"text:{sig}")

        required_hits = len([rid for rid in required if rid in found])
        confidence = min(0.98, 0.35 + (required_hits / max(len(required), 1)) * 0.45 + len(found) * 0.03)
        if required_hits >= min_hits or (required_hits >= 1 and len(found) >= min_hits + 1):
            status = "pass"
            summary = f"Camera view detected ({required_hits}/{len(required)} required controls)."
        elif required_hits == 0 and not elements and not ocr:
            status = "unknown"
            confidence = 0.2
            summary = "No UI dump or OCR available to verify camera view."
        else:
            status = "fail"
            confidence = max(0.4, confidence)
            summary = f"Camera view incomplete — missing {', '.join(missing[:4]) or 'controls'}."

        result = CameraPhaseResult(
            phase="view",
            status=status,
            confidence=round(confidence, 3),
            summary=summary,
            missing_signals=missing,
            found_signals=found,
            screenshot=str(screenshot) if screenshot else "",
            ui_dump=str(ui_dump) if ui_dump else "",
        )
        return self._maybe_llm_refine(result, flow_name, hay, phase="view")

    def analyze_capture(
        self,
        *,
        screenshot: Path | None,
        ui_dump: Path | None,
        flow_name: str = "",
        before_screenshot: Path | None = None,
    ) -> CameraPhaseResult:
        if not self.is_capture_flow(flow_name):
            return CameraPhaseResult(
                phase="capture",
                status="skipped",
                confidence=1.0,
                summary="Flow is not a capture scenario — capture analysis skipped.",
                screenshot=str(screenshot) if screenshot else "",
                ui_dump=str(ui_dump) if ui_dump else "",
            )

        elements = parse_ui_dump(ui_dump) if ui_dump else []
        ocr = extract_text(screenshot) if screenshot and screenshot.is_file() else ""
        cap_cfg = self.cfg.get("capture") or {}
        success_ids = [str(x) for x in (cap_cfg.get("success_resource_ids") or [])]
        gallery_signals = [str(x) for x in (cap_cfg.get("gallery_text_signals") or [])]

        found: list[str] = []
        missing: list[str] = []
        for rid in success_ids:
            if find_by_resource_id(elements, rid):
                found.append(rid)
            else:
                missing.append(rid)

        hay = " ".join(filter(None, [ocr, " ".join(e.text for e in elements if e.text)])).lower()
        for sig in gallery_signals:
            if sig.lower() in hay:
                found.append(f"gallery:{sig}")

        brightness_delta = 0.0
        if before_screenshot and screenshot and before_screenshot.is_file() and screenshot.is_file():
            brightness_delta = self._brightness_delta(before_screenshot, screenshot)
            if brightness_delta >= float(cap_cfg.get("preview_change_min_brightness_delta", 8.0)):
                found.append(f"preview_delta:{brightness_delta:.1f}")

        capture_ok = bool(found) and (len([x for x in found if not x.startswith("gallery:")]) > 0 or brightness_delta > 0)
        if capture_ok:
            status = "pass"
            confidence = min(0.95, 0.55 + len(found) * 0.12)
            summary = f"Capture indicators present ({', '.join(found[:5])})."
        elif not screenshot and not ui_dump:
            status = "unknown"
            confidence = 0.25
            summary = "No post-capture artifacts to verify capture."
        else:
            status = "fail"
            confidence = 0.62
            summary = "Capture not verified — thumbnail/preview change/gallery return not detected."

        result = CameraPhaseResult(
            phase="capture",
            status=status,
            confidence=round(confidence, 3),
            summary=summary,
            missing_signals=missing,
            found_signals=found,
            screenshot=str(screenshot) if screenshot else "",
            ui_dump=str(ui_dump) if ui_dump else "",
            metadata={"brightness_delta": brightness_delta},
        )
        return self._maybe_llm_refine(result, flow_name, hay, phase="capture")

    def _brightness_delta(self, before: Path, after: Path) -> float:
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore

            b = cv2.imread(str(before))
            a = cv2.imread(str(after))
            if b is None or a is None:
                return 0.0
            bg = float(np.mean(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)))
            ag = float(np.mean(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)))
            return abs(ag - bg)
        except Exception:
            return 0.0

    def _maybe_llm_refine(
        self,
        result: CameraPhaseResult,
        flow_name: str,
        visible_text: str,
        *,
        phase: str,
    ) -> CameraPhaseResult:
        if not self.llm_enabled or not self.llm or not self.llm.available:
            return result
        if result.status == "skipped":
            return result
        if result.confidence >= self.min_rule_confidence and result.status in ("pass", "fail"):
            return result

        system = (
            "You analyze Kodak Step Print camera automation screenshots (text summary only). "
            "Return JSON: status (pass|fail|unknown), confidence (0-1), summary (one sentence)."
        )
        user = (
            f"Phase: {phase}\nFlow: {flow_name}\n"
            f"Rule status: {result.status} conf={result.confidence}\n"
            f"Found: {result.found_signals}\nMissing: {result.missing_signals}\n"
            f"Visible text sample:\n{visible_text[:2500]}"
        )
        resp = self.llm.chat(system, user)
        content = resp.get("content", "")
        if not content:
            return result
        try:
            m = re.search(r"\{.*\}", content, re.S)
            data = json.loads(m.group(0)) if m else {}
            result.status = str(data.get("status", result.status))
            result.confidence = float(data.get("confidence", result.confidence))
            result.summary = str(data.get("summary", result.summary))
            result.metadata["llm_refined"] = True
        except Exception:
            pass
        return result


def _safe_flow_slug(flow_name: str) -> str:
    return flow_name.replace(" ", "_")


def artifact_roots(repo: Path, suite_id: str, flow_name: str, device_id: str) -> list[Path]:
    slug = f"{flow_name}__{device_id.replace(' ', '_')}"
    safe = _safe_flow_slug(flow_name)
    roots = [
        repo / "reports" / suite_id / "maestro-debug" / slug,
        repo / "reports" / suite_id / "maestro-debug" / f"{safe}__{device_id.replace(' ', '_')}",
        repo / "build-summary" / "failed-artifacts" / f"{safe}__{device_id.replace(' ', '_')}",
        repo / "build-summary" / "failed-artifacts" / slug,
    ]
    return [p for p in roots if p.is_dir()]


def newest_artifacts(folder: Path) -> tuple[Path | None, Path | None, list[Path]]:
    pngs = sorted(folder.rglob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    xmls = sorted(folder.rglob("*.xml"), key=lambda p: p.stat().st_mtime, reverse=True)
    shot = pngs[0] if pngs else None
    dump = xmls[0] if xmls else None
    return shot, dump, pngs


def analyze_flow_from_workspace(
    analyzer: CameraAnalyzer,
    repo: Path,
    *,
    suite_id: str,
    flow_name: str,
    device_id: str,
) -> tuple[CameraPhaseResult, CameraPhaseResult]:
    """Load Maestro debug artifacts for a flow and run view + capture analysis."""
    shot = dump = None
    before_shot = None
    pngs: list[Path] = []

    for root in artifact_roots(repo, suite_id, flow_name, device_id):
        shot, dump, pngs = newest_artifacts(root)
        if shot or dump:
            if len(pngs) >= 2:
                before_shot = pngs[-1]
            break

    view = analyzer.analyze_view(screenshot=shot, ui_dump=dump, flow_name=flow_name)
    capture = analyzer.analyze_capture(
        screenshot=shot,
        ui_dump=dump,
        flow_name=flow_name,
        before_screenshot=before_shot,
    )
    return view, capture
