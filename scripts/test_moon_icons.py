"""Offline regression tests for the moon artwork generator."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).with_name('moon-icons.py')

class MoonIconsTest(unittest.TestCase):
    def test_generates_complete_portable_phase_set(self):
        self.assertTrue(SCRIPT.exists(), 'moon artwork generator is missing')
        spec = importlib.util.spec_from_file_location('moon_icons', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            module.generate(Path(tmp))
            files = sorted((Path(tmp) / 'moon').glob('*.svg'))
            self.assertEqual(len(files), 120)
            for file in files:
                root = ET.parse(file).getroot()
                self.assertEqual(root.attrib['viewBox'], '0 0 100 100')
            css = (Path(tmp) / 'moon.css').read_text()
            for i in range(120):
                self.assertIn(f'#custom-moon.phase-{i:03d}', css)
                self.assertIn(f'url("moon/phase-{i:03d}.svg")', css)
            self.assertIn('24px 24px', css)

if __name__ == '__main__':
    unittest.main()
