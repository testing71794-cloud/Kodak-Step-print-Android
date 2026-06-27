"""First-run project scanner — builds internal knowledge base automatically."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ScanResult:
    modules: list[dict[str, Any]] = field(default_factory=list)
    flows: list[dict[str, Any]] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)
    jenkins_stages: list[str] = field(default_factory=list)
    report_patterns: list[str] = field(default_factory=list)
    file_count: int = 0
    content_hash: str = ""

    def to_manifest(self) -> dict[str, Any]:
        return {
            "modules": self.modules,
            "flows": self.flows[:500],
            "flow_count": len(self.flows),
            "scripts": self.scripts[:200],
            "jenkins_stages": self.jenkins_stages,
            "report_patterns": self.report_patterns,
            "file_count": self.file_count,
            "content_hash": self.content_hash,
        }


class ProjectScanner:
    FLOW_ID_RE = re.compile(r"^([A-Z]{2}_[A-Z0-9]+)", re.MULTILINE)

    def __init__(self, repo_root: Path, scan_paths: list[str]) -> None:
        self.repo_root = repo_root
        self.scan_paths = scan_paths

    def scan(self) -> ScanResult:
        result = ScanResult()
        hasher = hashlib.sha256()
        atp_root = self.repo_root / "ATP TestCase Flows"
        if atp_root.is_dir():
            for mod_dir in sorted(atp_root.iterdir()):
                if not mod_dir.is_dir():
                    continue
                yamls = list(mod_dir.glob("*.yaml")) + list(mod_dir.glob("*.yml"))
                cases = [p.name for p in yamls if not p.name.startswith("subflow")]
                result.modules.append(
                    {
                        "name": mod_dir.name,
                        "folder": str(mod_dir.relative_to(self.repo_root)),
                        "case_count": len(cases),
                        "sample_cases": cases[:10],
                    }
                )
                for yf in yamls:
                    self._index_flow(yf, result, hasher)

        for rel in self.scan_paths:
            base = self.repo_root / rel
            if not base.exists():
                continue
            if base.is_file():
                self._hash_file(base, hasher)
                continue
            for p in base.rglob("*"):
                if p.is_file() and p.suffix.lower() in {".py", ".bat", ".ps1", ".sh", ".yaml", ".yml"}:
                    self._hash_file(p, hasher)
                    if p.suffix == ".py" and "scripts" in p.parts:
                        result.scripts.append(str(p.relative_to(self.repo_root)))

        jenkins = self.repo_root / "Jenkinsfile"
        if jenkins.is_file():
            text = jenkins.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r"stage\s*\(\s*['\"]([^'\"]+)['\"]", text):
                result.jenkins_stages.append(m.group(1))
            self._hash_file(jenkins, hasher)

        for pat in ("reports/**", "build-summary/**", "**/execution_logs.zip"):
            for p in self.repo_root.glob(pat):
                if p.is_file():
                    result.report_patterns.append(str(p.relative_to(self.repo_root)))

        result.file_count = len(result.flows) + len(result.scripts)
        result.content_hash = hasher.hexdigest()
        return result

    def _hash_file(self, path: Path, hasher: hashlib._Hash) -> None:
        try:
            hasher.update(str(path.relative_to(self.repo_root)).encode("utf-8"))
            hasher.update(path.read_bytes())
        except OSError:
            pass

    def _index_flow(self, path: Path, result: ScanResult, hasher: hashlib._Hash) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        self._hash_file(path, hasher)
        case_id = ""
        m = self.FLOW_ID_RE.search(path.stem)
        if m:
            case_id = m.group(1)
        taps = re.findall(r"tapOn:\s*[\"']?([^\"'\n]+)", text)
        asserts = re.findall(r"assertVisible:\s*[\"']?([^\"'\n]+)", text)
        result.flows.append(
            {
                "path": str(path.relative_to(self.repo_root)),
                "case_id": case_id,
                "module": path.parent.name,
                "tap_targets": taps[:20],
                "assertions": asserts[:20],
            }
        )


class KnowledgeBuilder:
    """Persist scan results into memory stores."""

    def __init__(self, sqlite_store, vector_store=None) -> None:
        self.sqlite = sqlite_store
        self.vector = vector_store

    def build_from_scan(self, scan: ScanResult) -> dict[str, Any]:
        from memory.sqlite_store import MemoryRecord

        manifest = scan.to_manifest()
        self.sqlite.save_scan_manifest(manifest)

        for mod in scan.modules:
            self.sqlite.upsert(
                MemoryRecord("module", mod["name"], mod, confidence=1.0)
            )
            if self.vector and self.vector.available:
                self.vector.upsert(
                    self.vector.doc_id("module", mod["name"]),
                    json.dumps(mod),
                    {"category": "module", "name": mod["name"]},
                )

        for flow in scan.flows[:300]:
            key = flow.get("case_id") or flow["path"]
            self.sqlite.upsert(MemoryRecord("flow", key, flow, confidence=0.9))
            if self.vector and self.vector.available:
                text = f"{flow.get('module')} {key} taps={flow.get('tap_targets')} asserts={flow.get('assertions')}"
                self.vector.upsert(
                    self.vector.doc_id("flow", key),
                    text,
                    {"category": "flow", "case_id": key},
                )

        for popup in (scan.to_manifest().get("modules") or []):
            pass  # app profile popups loaded separately

        return manifest
