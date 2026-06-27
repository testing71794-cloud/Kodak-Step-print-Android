"""Parse Android UIAutomator XML dumps."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UIElement:
    text: str
    resource_id: str
    class_name: str
    bounds: str
    clickable: bool
    enabled: bool
    content_desc: str = ""

    @property
    def center(self) -> tuple[int, int] | None:
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", self.bounds or "")
        if not m:
            return None
        x1, y1, x2, y2 = map(int, m.groups())
        return (x1 + x2) // 2, (y1 + y2) // 2


def parse_ui_dump(path: Path) -> list[UIElement]:
    if not path.is_file():
        return []
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return []
    elements: list[UIElement] = []
    for node in tree.iter("node"):
        elements.append(
            UIElement(
                text=(node.get("text") or "").strip(),
                resource_id=(node.get("resource-id") or "").strip(),
                class_name=(node.get("class") or "").strip(),
                bounds=(node.get("bounds") or "").strip(),
                clickable=node.get("clickable") == "true",
                enabled=node.get("enabled") != "false",
                content_desc=(node.get("content-desc") or "").strip(),
            )
        )
    return elements


def find_by_text(elements: list[UIElement], pattern: str, *, regex: bool = False) -> list[UIElement]:
    out: list[UIElement] = []
    for el in elements:
        hay = " ".join(filter(None, [el.text, el.content_desc]))
        if not hay:
            continue
        if regex:
            if re.search(pattern, hay, re.I):
                out.append(el)
        elif pattern.lower() in hay.lower():
            out.append(el)
    return out


def find_by_resource_id(elements: list[UIElement], resource_id: str) -> list[UIElement]:
    needle = resource_id.strip().lower()
    if not needle:
        return []
    out: list[UIElement] = []
    for el in elements:
        rid = el.resource_id.lower()
        if not rid:
            continue
        if rid == needle or rid.endswith(f"/{needle}") or needle in rid:
            out.append(el)
    return out
