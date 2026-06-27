"""Parse Android UIAutomator hierarchy dumps into structured elements."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class UIElement:
    text: str = ""
    content_desc: str = ""
    resource_id: str = ""
    class_name: str = ""
    package: str = ""
    clickable: bool = False
    enabled: bool = True
    bounds: tuple[int, int, int, int] | None = None  # left, top, right, bottom
    children: list["UIElement"] = field(default_factory=list)

    @property
    def label(self) -> str:
        return (self.text or self.content_desc or self.resource_id or "").strip()

    @property
    def center(self) -> tuple[int, int] | None:
        if not self.bounds:
            return None
        l, t, r, b = self.bounds
        return ((l + r) // 2, (t + b) // 2)

    def all_labels(self) -> list[str]:
        out: list[str] = []
        if self.label:
            out.append(self.label)
        for c in self.children:
            out.extend(c.all_labels())
        return out

    def find_clickable_with_text(self, pattern: str, flags: int = re.I) -> list["UIElement"]:
        rx = re.compile(pattern, flags)
        hits: list[UIElement] = []

        def walk(node: UIElement) -> None:
            if node.clickable and node.label and rx.search(node.label):
                hits.append(node)
            for ch in node.children:
                walk(ch)

        walk(self)
        return hits

    def flatten(self) -> list["UIElement"]:
        out = [self]
        for c in self.children:
            out.extend(c.flatten())
        return out


def _parse_bounds(raw: str) -> tuple[int, int, int, int] | None:
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", raw or "")
    if not m:
        return None
    return tuple(int(g) for g in m.groups())  # type: ignore[return-value]


def _node_from_xml(el: ET.Element) -> UIElement:
    attrs = el.attrib
    bounds = _parse_bounds(attrs.get("bounds", ""))
    return UIElement(
        text=attrs.get("text", ""),
        content_desc=attrs.get("content-desc", ""),
        resource_id=attrs.get("resource-id", ""),
        class_name=attrs.get("class", ""),
        package=attrs.get("package", ""),
        clickable=attrs.get("clickable", "false") == "true",
        enabled=attrs.get("enabled", "true") == "true",
        bounds=bounds,
        children=[_node_from_xml(c) for c in el],
    )


def parse_ui_dump(xml_path: Path | str) -> UIElement | None:
    path = Path(xml_path)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return None
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    return _node_from_xml(root)


def extract_visible_strings(tree: UIElement | None) -> list[str]:
    if tree is None:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for node in tree.flatten():
        for val in (node.text, node.content_desc):
            v = (val or "").strip()
            if v and v not in seen:
                seen.add(v)
                out.append(v)
    return out


def screen_context_summary(tree: UIElement | None, ocr_lines: list[str] | None = None) -> dict[str, Any]:
    ui_strings = extract_visible_strings(tree)
    merged = list(dict.fromkeys(ui_strings + (ocr_lines or [])))
    return {
        "ui_strings": ui_strings,
        "ocr_lines": ocr_lines or [],
        "all_visible_text": merged,
        "clickable_labels": [
            n.label for n in (tree.flatten() if tree else []) if n.clickable and n.label
        ],
    }
