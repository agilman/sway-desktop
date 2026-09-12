"""Drive weather.sh over real cache files to verify class mapping."""
import json
import os
import subprocess
import unittest
from pathlib import Path

CACHE = Path(f"/tmp/wayland-plus-weather-{os.environ.get('USER','hermes')}.json")
CONFIG = Path(f"/tmp/weather-test-config-{os.environ.get('USER','user')}")

def run(code, wind=5):
    config_dir = CONFIG / 'wayland-plus'
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / 'config.env').write_text('LAT=48.76\nLON=-122.46\nUNITS=imperial\n')
    CACHE.write_text(json.dumps({'temp': 58.0, 'feels': 55.0, 'code': code, 'wind': wind,
        'prob_max': 10, 'rain_sum': 0.0, 'tmax': 60, 'tmin': 50, 'rain_3h': 0, 'asof': 'x'}))
    out = subprocess.run(['bash', str(Path(__file__).with_name('weather.sh')), 'waybar'],
                         env={**os.environ, 'XDG_CONFIG_HOME': str(CONFIG)},
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)

class WeatherClassTest(unittest.TestCase):
    def test_wmo_codes_map_to_artwork_classes(self):
        cases = [(0, 'clear'), (1, 'partly'), (2, 'partly'), (3, 'cloudy'),
                 (61, 'rain'), (80, 'rain'), (71, 'snow'), (85, 'snow'),
                 (95, 'storm'), (45, 'cloudy')]
        for code, expected in cases:
            with self.subTest(code=code):
                self.assertEqual(run(code)['class'], expected)

    def test_strong_wind_promotes_windy_when_dry(self):
        self.assertEqual(run(0, wind=22)['class'], 'windy')
        self.assertEqual(run(3, wind=25)['class'], 'windy')
        self.assertEqual(run(0, wind=5)['class'], 'clear')
        self.assertEqual(run(61, wind=30)['class'], 'rain', 'precip keeps priority')

    def test_text_has_icon_placeholder_and_temperature(self):
        data = run(0)
        self.assertTrue(data['text'])
        self.assertNotIn('󰖑', data['text'], 'font glyphs must be gone')
        self.assertIn('58', data['text'])
        self.assertIn('tooltip', data)

if __name__ == '__main__':
    unittest.main()