"""Offline regression tests for the weather artwork generator."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

SCRIPT = Path(__file__).with_name('weather-icons.py')

class WeatherIconsTest(unittest.TestCase):
    def test_generates_all_condition_icons_and_css(self):
        self.assertTrue(SCRIPT.exists(), 'weather artwork generator is missing')
        spec = importlib.util.spec_from_file_location('weather_icons', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            module.generate(Path(tmp))
            for name in ['clear', 'partly', 'cloudy', 'rain', 'snow', 'storm', 'windy', 'nodata']:
                path = Path(tmp) / 'weather' / f'{name}.svg'
                self.assertTrue(path.exists(), f'missing {name}.svg')
                self.assertEqual(ET.parse(path).getroot().attrib['viewBox'], '0 0 100 100')
            css = (Path(tmp) / 'weather.css').read_text()
            for name in ['clear', 'partly', 'cloudy', 'rain', 'snow', 'storm', 'windy', 'nodata']:
                self.assertIn(f'#custom-weather.{name} {{', css)
                self.assertIn(f'url("weather/{name}.svg")', css)
            self.assertIn('24px 24px', css)

if __name__ == '__main__':
    unittest.main()