"""Drive aqi.sh over synthetic cache to verify text/class output."""
import json
import os
import subprocess
import unittest
from pathlib import Path

TEST_USER = f"widgettest-{os.environ.get('USER','user')}"  # per-user: /tmp is shared
CACHE = Path(f'/tmp/wayland-plus-aqi-{TEST_USER}.json')  # isolated: never the live cache
CONFIG = Path(f"/tmp/aqi-test-config-{os.environ.get('USER','user')}")

def run(aqi):
    d = CONFIG / 'wayland-plus'; d.mkdir(parents=True, exist_ok=True)
    (d / 'config.env').write_text('LAT=48.76\nLON=-122.46\n')
    CACHE.write_text(json.dumps({'source': 'test', 'aqi': aqi, 'category': 'x',
                                 'parameter': 'PM2.5', 'asof': 'now'}))
    out = subprocess.run(['bash', str(Path(__file__).with_name('aqi.sh')), 'waybar'],
                         env={**os.environ, 'XDG_CONFIG_HOME': str(CONFIG), 'USER': TEST_USER},
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)

class AqiShTest(unittest.TestCase):
    def test_classes_follow_epa_breakpoints(self):
        for aqi, cls in [(20,'good'),(52,'moderate'),(120,'usg'),(180,'unhealthy'),(250,'veryunhealthy'),(400,'hazardous')]:
            with self.subTest(aqi=aqi):
                self.assertEqual(run(aqi)['class'], cls)

    def test_text_is_number_with_icon_slot_no_glyph(self):
        data = run(52)
        self.assertNotIn('󰢬', data['text'])
        self.assertIn('52', data['text'])
        self.assertTrue(data['text'].startswith('\u00a0'), 'NBSP icon slot expected')
        self.assertIn('tooltip', data)

if __name__ == '__main__':
    unittest.main()