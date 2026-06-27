import unittest
from pathlib import Path

from ai.printer_selector import PrinterRules, PrinterSelector
from ai.ui_parser import parse_ui_dump

SAMPLE_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" class="android.widget.FrameLayout" clickable="false" bounds="[0,0][1080,2340]">
    <node text="Printer B Demo" clickable="true" bounds="[0,100][1080,200]"/>
    <node text="Kodak Step Touch" clickable="true" bounds="[0,300][1080,400]"/>
    <node text="Random Device" clickable="true" bounds="[0,500][1080,600]"/>
  </node>
</hierarchy>
"""


class TestPrinterSelector(unittest.TestCase):
    def test_priority_selection(self):
        rules = PrinterRules(
            preferred_names=["Kodak Step Touch"],
            preferred_serials=[],
            priority_list=["Kodak Step Touch"],
            name_patterns=[r"(?i)kodak"],
            exclude_patterns=[r"(?i)demo"],
        )
        tmp = Path(__file__).parent / "_fixture_printers.xml"
        tmp.write_text(SAMPLE_XML, encoding="utf-8")
        try:
            tree = parse_ui_dump(tmp)
            sel = PrinterSelector(rules)
            best = sel.select_best(tree)
            self.assertIsNotNone(best)
            assert best is not None
            self.assertEqual(best.label, "Kodak Step Touch")
            self.assertGreater(best.score, 0.8)
        finally:
            tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
