"""Tabular (arithmetic) Islamic calendar.

This is the civil tabular calendar: 30-year cycles with 11 leap years. It's
predictable and needs no data, but it can differ by a day or two from dates set
by moon sighting or the Umm al-Qura calendar. That's why output is labelled
"approx.", and why there's a ``--hijri-offset`` option to nudge it.
"""

import math
from datetime import date
from typing import NamedTuple

EPOCH = 1948439.5  # Julian Day of 1 Muharram 1 AH (civil epoch)

MONTHS = (
    "Muharram",
    "Safar",
    "Rabi al-Awwal",
    "Rabi al-Thani",
    "Jumada al-Awwal",
    "Jumada al-Thani",
    "Rajab",
    "Shaban",
    "Ramadan",
    "Shawwal",
    "Dhu al-Qadah",
    "Dhu al-Hijjah",
)


class HijriDate(NamedTuple):
    year: int
    month: int  # 1-12
    day: int

    @property
    def month_name(self) -> str:
        return MONTHS[self.month - 1]

    def __str__(self) -> str:
        return f"{self.day} {self.month_name} {self.year} AH"


def _islamic_to_jd(year: int, month: int, day: int) -> float:
    return (
        day
        + math.ceil(29.5 * (month - 1))
        + (year - 1) * 354
        + math.floor((3 + 11 * year) / 30)
        + EPOCH
        - 1
    )


def to_hijri(d: date, offset_days: int = 0) -> HijriDate:
    """Convert a Gregorian date to the tabular Hijri calendar."""
    jd = d.toordinal() + 1721424.5 + offset_days
    year = math.floor((30 * (jd - EPOCH) + 10646) / 10631)
    month = min(12, math.ceil((jd - (29 + _islamic_to_jd(year, 1, 1))) / 29.5) + 1)
    day = int(jd - _islamic_to_jd(year, month, 1) + 1)
    return HijriDate(year, month, day)
