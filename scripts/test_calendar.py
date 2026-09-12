"""calendar.sh: text mode prints the month with today bracketed."""
import datetime
import subprocess
import unittest
from pathlib import Path

class CalendarTest(unittest.TestCase):
    def test_marks_today_and_has_month_grid(self):
        out = subprocess.run(['bash', str(Path(__file__).with_name('calendar.sh')), 'text'],
                             capture_output=True, text=True, check=True).stdout
        today = datetime.date.today()
        lines = out.splitlines()
        self.assertIn(today.strftime('%B'), lines[0])
        self.assertIn(str(today.year), lines[0])
        self.assertEqual(out.count(f'[{today.day}]'), 1, out)
        self.assertRegex(out, r'Su Mo Tu We Th Fr Sa')
        self.assertNotIn('\x1b', out, 'ANSI escapes must be stripped')

if __name__ == '__main__':
    unittest.main()