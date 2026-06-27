import unittest
from pathlib import Path

from ai.ui_parser import parse_ui_dump, extract_visible_strings


SAMPLE_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" clickable="false" bounds="[0,0][1080,2340]">
    <node index="1" text="Kodak Step Touch" resource-id="" class="android.widget.TextView" clickable="true" bounds="[100,500][980,600]"/>
    <node index="2" text="Search again" resource-id="" class="android.widget.Button" clickable="true" bounds="[100,700][980,800]"/>
  </node>
</hierarchy>
"""


class TestUIParser(unittest.TestCase):
    def test_parse_and_find_labels(self):
        tmp = Path(__file__).parent / "_fixture_dump.xml"
        tmp.write_text(SAMPLE_XML, encoding="utf-8")
        try:
            tree = parse_ui_dump(tmp)
            self.assertIsNotNone(tree)
            labels = extract_visible_strings(tree)
            self.assertIn("Kodak Step Touch", labels)
            hits = tree.find_clickable_with_text("Search")
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].center, (540, 750))
        finally:
            tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
