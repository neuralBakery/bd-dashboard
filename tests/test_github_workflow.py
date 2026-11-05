"""Validate embedded workflow scripts and the two Melbourne DST schedule slots."""
import ast
import datetime
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

class ScheduleTests(unittest.TestCase):
    def test_monday_melbourne_slots_in_both_seasons(self):
        for month, expected in [(1,20),(6,21),(11,20)]:
            d=datetime.datetime(2027,month,8,7,tzinfo=ZoneInfo('Australia/Melbourne'))
            slot=(7-int(d.utcoffset().total_seconds()//3600))%24
            self.assertEqual(slot,expected)
            self.assertEqual(d.astimezone(datetime.timezone.utc).hour,expected)
    def test_daylight_saving_change_weekends(self):
        for local in ['2027-04-05T07:00:00','2027-10-04T07:00:00']:
            d=datetime.datetime.fromisoformat(local).replace(tzinfo=ZoneInfo('Australia/Melbourne'))
            utc=d.astimezone(datetime.timezone.utc)
            self.assertEqual(d.weekday(),0)
            self.assertEqual(utc.weekday(),6)
            self.assertIn(utc.hour,[20,21])
    def test_embedded_python_scripts_compile(self):
        lines=(Path(__file__).resolve().parents[1]/'.github/workflows/weekly-intelligence.yml').read_text().splitlines()
        blocks=[];current=None
        for line in lines:
            stripped=line.strip()
            if stripped=="python3 - <<'PY'":current=[]
            elif stripped=='PY' and current is not None:
                blocks.append('\n'.join(current));current=None
            elif current is not None:
                current.append(line[10:])
        self.assertEqual(len(blocks),2)
        for block in blocks:ast.parse(block)

if __name__=='__main__':unittest.main()
