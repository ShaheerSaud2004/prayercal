import unittest
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from prayercal import CalendarOptions, build_calendar, compute_range, to_hijri
from prayercal.ics import escape_text, fold

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
NYC = (40.7128, -74.0060, ZoneInfo("America/New_York"))


class HijriTest(unittest.TestCase):
    def test_known_dates(self):
        # Well-known dates where the tabular calendar agrees with the announced date.
        self.assertEqual(to_hijri(date(2000, 1, 1)), (1420, 9, 24))
        self.assertEqual(to_hijri(date(2025, 3, 1)), (1446, 9, 1))
        self.assertEqual(to_hijri(date(2026, 2, 18)), (1447, 9, 1))

    def test_offset(self):
        # Sha'ban (an even month) always has 29 days in the tabular calendar.
        self.assertEqual(to_hijri(date(2025, 3, 1), offset_days=-1), (1446, 8, 29))

    def test_month_name(self):
        self.assertEqual(str(to_hijri(date(2025, 3, 1))), "1 Ramadan 1446 AH")

    def test_days_are_consecutive(self):
        prev = to_hijri(date(2020, 1, 1))
        for i in range(1, 800):
            cur = to_hijri(date.fromordinal(date(2020, 1, 1).toordinal() + i))
            if cur.day != 1:
                self.assertEqual(cur.day, prev.day + 1)
            else:
                self.assertIn(prev.day, (29, 30))
            prev = cur


def unfold(text: str):
    return text.replace("\r\n ", "").split("\r\n")


class IcsTest(unittest.TestCase):
    def build(self, start=date(2026, 11, 16), days=7, **opts):
        lat, lon, tz = NYC
        return build_calendar(
            compute_range(start, days, lat, lon, tz), tz, CalendarOptions(**opts), scope="test", now=NOW
        )

    def test_structure(self):
        text = self.build()
        self.assertTrue(text.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(text.endswith("END:VCALENDAR\r\n"))
        self.assertEqual(text.count("BEGIN:VEVENT"), 7 * 5)
        self.assertNotIn("\n", text.replace("\r\n", ""))

    def test_lines_are_folded_to_75_octets(self):
        text = self.build(name="Masjid " + "ü" * 80)
        for line in text.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)
        self.assertIn("X-WR-CALNAME:Masjid " + "ü" * 80, unfold(text))

    def test_uids_are_stable_and_unique(self):
        a, b = self.build(), self.build()
        uids = [l for l in unfold(a) if l.startswith("UID:")]
        self.assertEqual(len(uids), len(set(uids)))
        self.assertEqual(a, b)

    def test_jumuah_replaces_dhuhr_on_friday(self):
        text = self.build(start=date(2026, 11, 20), days=1, jumuah=time(13, 15))
        lines = unfold(text)
        self.assertIn("SUMMARY:Jumu'ah", lines)
        self.assertNotIn("SUMMARY:Dhuhr", lines)
        self.assertIn("DTSTART:20261120T181500Z", lines)  # 13:15 EST

    def test_iqamah_and_alarm(self):
        text = self.build(days=1, iqamah={"fajr": 20}, alarm_minutes=10, prayers=["fajr"])
        lines = unfold(text)
        desc = next(l for l in lines if l.startswith("DESCRIPTION:Fajr"))
        self.assertIn("Fajr 5:09 AM", desc)  # default method is MWL
        self.assertIn("Iqamah 5:29 AM", desc)
        self.assertIn("TRIGGER:-PT10M", lines)

    def test_ramadan_notes(self):
        text = self.build(start=date(2026, 2, 20), days=1, prayers=["fajr", "maghrib"])
        joined = "\n".join(unfold(text))
        self.assertIn("suhoor ends", joined)
        self.assertIn("iftar", joined)

    def test_escaping(self):
        self.assertEqual(escape_text("a,b;c\\d\ne"), "a\\,b\\;c\\\\d\\ne")

    def test_fold_short_line_untouched(self):
        self.assertEqual(fold("SUMMARY:Fajr"), "SUMMARY:Fajr")


if __name__ == "__main__":
    unittest.main()
