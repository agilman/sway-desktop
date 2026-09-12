"""Offline regression tests for the moon notify-popup artwork."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('moon-notify-icons.py')

class MoonNotifyIconsTest(unittest.TestCase):
    def test_renders_16_phases_with_expected_metadata(self):
        self.assertTrue(SCRIPT.exists(), 'notify artwork generator is missing')
        spec = importlib.util.spec_from_file_location('moon_notify_icons', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            out = module.render_all(Path(tmp), 'stub')
            self.assertEqual(len(out), 16)
            for i, p in enumerate(out):
                self.assertTrue(p.exists(), f'phase {i} missing')
                self.assertEqual(p.name, f'phase-{i:02d}.png')
                self.assertGreater(p.stat().st_size, 500, f'phase {i} looks empty')

if __name__ == '__main__':
    unittest.main()