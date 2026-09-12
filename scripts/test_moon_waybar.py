"""Exercise the real shell JSON path with an offline config."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

class MoonWaybarTest(unittest.TestCase):
    def test_emits_artwork_class_and_preserves_tooltip(self):
        with tempfile.TemporaryDirectory() as config:
            result = subprocess.run(['bash', str(Path(__file__).with_name('moon.sh')), 'waybar'],
                                    env={**os.environ, 'XDG_CONFIG_HOME': config},
                                    text=True, capture_output=True, check=True)
        data = json.loads(result.stdout)
        self.assertRegex(data.get('class', ''), r'^phase-\d{3}$')
        self.assertIn('illuminated', data['tooltip'])
        self.assertTrue(data['text'])
        self.assertLess(int(data['class'].split('-')[1]), 120)

if __name__ == '__main__':
    unittest.main()
