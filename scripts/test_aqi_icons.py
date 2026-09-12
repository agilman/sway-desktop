"""Offline regression tests for the AQI artwork generator."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).with_name('aqi-icons.py')
CLASSES = ['good', 'moderate', 'usg', 'unhealthy', 'veryunhealthy', 'hazardous', 'nodata']

class AqiIconsTest(unittest.TestCase):
    def test_generates_one_icon_per_epa_class(self):
        self.assertTrue(SCRIPT.exists(), 'aqi artwork generator is missing')
        spec = importlib.util.spec_from_file_location('aqi_icons', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            module.generate(Path(tmp))
            css = (Path(tmp) / 'aqi.css').read_text()
            for name in CLASSES:
                path = Path(tmp) / 'aqi' / f'{name}.svg'
                self.assertTrue(path.exists(), f'missing {name}.svg')
                self.assertEqual(ET.parse(path).getroot().attrib['viewBox'], '0 0 100 100')
                self.assertIn(f'#custom-aqi.{name} {{', css)
                self.assertIn(f'url("aqi/{name}.svg")', css)
            self.assertIn('24px 24px', css)
            # Particle count must rise monotonically with severity.
            counts = [ (Path(tmp)/'aqi'/f'{n}.svg').read_text().count('<circle class="p"')
                       for n in CLASSES[:6] ]
            self.assertEqual(counts, sorted(counts))
            self.assertLess(counts[0], counts[-1])

if __name__ == '__main__':
    unittest.main()