"""Low-precision solar position, good to well under a minute of time.

Uses the U.S. Naval Observatory "Approximate Solar Coordinates" formulas,
which are accurate to about 1 arcminute between 1800 and 2200. That is far
better than the minute-level rounding prayer times are published at.
"""

import math
from datetime import date
from typing import NamedTuple

J2000 = 2451545.0


class SunPosition(NamedTuple):
    declination: float  # degrees
    equation_of_time: float  # hours (apparent minus mean solar time)


def dsin(d: float) -> float:
    return math.sin(math.radians(d))


def dcos(d: float) -> float:
    return math.cos(math.radians(d))


def dtan(d: float) -> float:
    return math.tan(math.radians(d))


def darcsin(x: float) -> float:
    return math.degrees(math.asin(x))


def darccos(x: float) -> float:
    return math.degrees(math.acos(x))


def darctan2(y: float, x: float) -> float:
    return math.degrees(math.atan2(y, x))


def fix_angle(a: float) -> float:
    return a % 360.0


def fix_hour(h: float) -> float:
    return h % 24.0


def julian_day(d: date) -> float:
    """Julian Day at 00:00 UTC of the given calendar date."""
    return d.toordinal() + 1721424.5


def sun_position(jd: float) -> SunPosition:
    """Sun declination and equation of time at Julian Day ``jd``."""
    n = jd - J2000
    g = fix_angle(357.529 + 0.98560028 * n)  # mean anomaly
    q = fix_angle(280.459 + 0.98564736 * n)  # mean longitude
    lam = fix_angle(q + 1.915 * dsin(g) + 0.020 * dsin(2 * g))  # ecliptic longitude
    e = 23.439 - 0.00000036 * n  # obliquity of the ecliptic

    ra = darctan2(dcos(e) * dsin(lam), dcos(lam)) / 15.0
    eqt = q / 15.0 - fix_hour(ra)
    # Keep EqT in (-12, 12] so wrap-around at 0h/24h doesn't produce ±24h jumps.
    if eqt > 12:
        eqt -= 24
    elif eqt <= -12:
        eqt += 24
    return SunPosition(darcsin(dsin(e) * dsin(lam)), eqt)
