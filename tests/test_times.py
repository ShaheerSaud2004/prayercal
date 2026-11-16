"""Prayer times checked against independently published reference values.

Reference times were taken from the AlAdhan API (api.aladhan.com) for the
same coordinates, method and Asr school, using the angle-based high-latitude
rule. Published times are rounded to the minute, so a 1-minute difference
is allowed.
"""

import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from prayercal import Settings, compute_day, compute_range, get_method

NAMES = ("fajr", "sunrise", "dhuhr", "asr", "sunset", "maghrib", "isha", "midnight")

# (label, lat, lon, tz, method, asr, date, [fajr, sunrise, dhuhr, asr, sunset, maghrib, isha, midnight])
REFERENCE = [
    ("New York, ISNA", 40.7128, -74.0060, "America/New_York", "ISNA", "standard", date(2026, 11, 16),
     ["05:25", "06:44", "11:41", "14:17", "16:37", "16:37", "17:56", "23:41"]),
    ("Makkah, Umm al-Qura", 21.4225, 39.8262, "Asia/Riyadh", "Makkah", "standard", date(2026, 11, 16),
     ["05:13", "06:32", "12:05", "15:16", "17:39", "17:39", "19:09", "00:05"]),
    ("London, MWL (winter)", 51.5074, -0.1278, "Europe/London", "MWL", "standard", date(2026, 11, 16),
     ["05:23", "07:20", "11:45", "13:49", "16:10", "16:10", "18:01", "23:45"]),
    ("Karachi, Hanafi Asr", 24.8607, 67.0011, "Asia/Karachi", "Karachi", "hanafi", date(2026, 11, 16),
     ["05:30", "06:49", "12:17", "16:09", "17:44", "17:44", "19:03", "00:17"]),
    ("London, MWL (summer solstice)", 51.5074, -0.1278, "Europe/London", "MWL", "standard", date(2026, 6, 21),
     ["02:31", "04:43", "13:02", "17:25", "21:22", "21:22", "23:27", "01:02"]),
    ("Oslo, MWL (twilight all night)", 59.9139, 10.7522, "Europe/Oslo", "MWL", "standard", date(2026, 6, 21),
     ["02:21", "03:54", "13:19", "18:00", "22:44", "22:44", "00:12", "01:19"]),
    ("Toronto, ISNA (summer)", 43.6532, -79.3832, "America/Toronto", "ISNA", "standard", date(2026, 6, 21),
     ["03:46", "05:36", "13:19", "17:26", "21:03", "21:03", "22:53", "01:19"]),
    ("Jakarta, MWL (southern hemisphere)", -6.2088, 106.8456, "Asia/Jakarta", "MWL", "standard", date(2026, 6, 21),
     ["04:46", "06:01", "11:54", "15:16", "17:47", "17:47", "18:58", "23:54"]),
]


def minutes_apart(actual: datetime, expected: str) -> int:
    h, m = map(int, expected.split(":"))
    a = actual.hour * 60 + actual.minute
    diff = abs(a - (h * 60 + m))
    return min(diff, 1440 - diff)  # times like Isha can wrap past midnight


class ReferenceTimesTest(unittest.TestCase):
    def test_against_published_reference(self):
        for label, lat, lon, tz, method, asr, d, expected in REFERENCE:
            settings = Settings(method=get_method(method), asr=asr)
            day = compute_day(d, lat, lon, ZoneInfo(tz), settings)
            for name, want in zip(NAMES, expected):
                with self.subTest(city=label, prayer=name):
                    got = day[name]
                    self.assertIsNotNone(got)
                    self.assertLessEqual(
                        minutes_apart(got, want), 1, f"{label} {name}: got {got:%H:%M}, want {want}"
                    )


class BehaviourTest(unittest.TestCase):
    NYC = (40.7128, -74.0060, ZoneInfo("America/New_York"))

    def test_order_of_prayers(self):
        lat, lon, tz = self.NYC
        day = compute_day(date(2026, 3, 1), lat, lon, tz)
        order = [day[p] for p in ("fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha")]
        self.assertEqual(order, sorted(order))

    def test_hanafi_asr_is_later(self):
        lat, lon, tz = self.NYC
        std = compute_day(date(2026, 3, 1), lat, lon, tz, Settings(asr="standard"))
        han = compute_day(date(2026, 3, 1), lat, lon, tz, Settings(asr="hanafi"))
        self.assertGreater(han["asr"], std["asr"])

    def test_fixed_interval_isha(self):
        lat, lon, tz = self.NYC
        day = compute_day(date(2026, 3, 1), lat, lon, tz, Settings(method=get_method("Makkah")))
        self.assertEqual((day["isha"] - day["maghrib"]).total_seconds(), 90 * 60)

    def test_adjustments_shift_minutes(self):
        lat, lon, tz = self.NYC
        base = compute_day(date(2026, 3, 1), lat, lon, tz)
        moved = compute_day(date(2026, 3, 1), lat, lon, tz, Settings(adjustments={"maghrib": 3}))
        self.assertEqual((moved["maghrib"] - base["maghrib"]).total_seconds(), 180)
        self.assertEqual(moved["fajr"], base["fajr"])

    def test_dst_is_respected(self):
        lat, lon, tz = self.NYC
        before = compute_day(date(2026, 3, 7), lat, lon, tz)  # EST
        after = compute_day(date(2026, 3, 9), lat, lon, tz)  # EDT
        self.assertEqual(before["dhuhr"].utcoffset().total_seconds(), -5 * 3600)
        self.assertEqual(after["dhuhr"].utcoffset().total_seconds(), -4 * 3600)
        # Solar noon barely moves, so local Dhuhr jumps by about an hour.
        self.assertEqual(after["dhuhr"].hour - before["dhuhr"].hour, 1)

    def test_times_are_whole_minutes(self):
        lat, lon, tz = self.NYC
        for day in compute_range(date(2026, 1, 1), 5, lat, lon, tz):
            for name in NAMES:
                self.assertEqual(day[name].second, 0)

    def test_polar_night_without_rule_returns_none(self):
        tromso = (69.6492, 18.9553, ZoneInfo("Europe/Oslo"))
        day = compute_day(date(2026, 12, 21), *tromso, Settings(high_lat="none"))
        self.assertIsNone(day["sunrise"])
        self.assertIsNone(day["sunset"])
        self.assertIsNotNone(day["dhuhr"])

    def test_high_latitude_rule_fills_missing_isha(self):
        oslo = (59.9139, 10.7522, ZoneInfo("Europe/Oslo"))
        raw = compute_day(date(2026, 6, 21), *oslo, Settings(high_lat="none"))
        ruled = compute_day(date(2026, 6, 21), *oslo, Settings(high_lat="seventh"))
        self.assertIsNone(raw["isha"])  # the sun never reaches 17° below the horizon
        self.assertIsNotNone(ruled["isha"])

    def test_invalid_inputs(self):
        tz = ZoneInfo("UTC")
        with self.assertRaises(ValueError):
            compute_day(date(2026, 1, 1), 95, 0, tz)
        with self.assertRaises(ValueError):
            Settings(asr="maliki")
        with self.assertRaises(ValueError):
            Settings(adjustments={"tahajjud": 1})
        with self.assertRaises(ValueError):
            get_method("nope")


if __name__ == "__main__":
    unittest.main()
