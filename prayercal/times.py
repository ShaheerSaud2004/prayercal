"""Prayer-time calculation.

All intermediate times are hours after 00:00 UTC on the requested date. Each
event is refined twice: the sun's position is recomputed at the previous
estimate, which matters most for Fajr and Isha at higher latitudes.
"""

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone, tzinfo
from typing import Dict, Iterator, Mapping, Optional

from .astro import darccos, darctan2, dcos, dsin, dtan, julian_day, sun_position
from .methods import ASR_FACTORS, HIGH_LAT_RULES, Method, get_method

PRAYERS = ("fajr", "sunrise", "dhuhr", "asr", "sunset", "maghrib", "isha", "midnight")
DISPLAY_NAMES = {
    "fajr": "Fajr",
    "sunrise": "Sunrise",
    "dhuhr": "Dhuhr",
    "asr": "Asr",
    "sunset": "Sunset",
    "maghrib": "Maghrib",
    "isha": "Isha",
    "midnight": "Midnight",
}

# Rough local solar times used as the first guess for each event.
_GUESS = {"fajr": 5, "sunrise": 6, "dhuhr": 12, "asr": 13, "sunset": 18, "maghrib": 18, "isha": 18}


@dataclass(frozen=True)
class Settings:
    method: Method = field(default_factory=lambda: get_method("MWL"))
    asr: str = "standard"
    high_lat: str = "angle"
    elevation: float = 0.0  # metres above the surrounding horizon
    adjustments: Mapping[str, float] = field(default_factory=dict)  # minutes per prayer

    def __post_init__(self) -> None:
        if self.asr not in ASR_FACTORS:
            raise ValueError(f"asr must be one of {', '.join(ASR_FACTORS)}")
        if self.high_lat not in HIGH_LAT_RULES:
            raise ValueError(f"high_lat must be one of {', '.join(HIGH_LAT_RULES)}")
        unknown = set(self.adjustments) - set(PRAYERS)
        if unknown:
            raise ValueError(f"unknown prayer(s) in adjustments: {', '.join(sorted(unknown))}")


@dataclass(frozen=True)
class DayTimes:
    date: date
    times: Dict[str, Optional[datetime]]

    def __getitem__(self, prayer: str) -> Optional[datetime]:
        return self.times[prayer]


class _Solver:
    def __init__(self, d: date, lat: float, lon: float):
        self.jd0 = julian_day(d)
        self.lat = lat
        self.lon = lon

    def _sun(self, t: float):
        return sun_position(self.jd0 + t / 24.0)

    def noon(self, t: float) -> float:
        return 12.0 - self.lon / 15.0 - self._sun(t).equation_of_time

    def _hour_angle(self, altitude: float, decl: float) -> Optional[float]:
        cos_h = (dsin(altitude) - dsin(self.lat) * dsin(decl)) / (dcos(self.lat) * dcos(decl))
        if cos_h < -1 or cos_h > 1:
            return None  # the sun never reaches this altitude today
        return darccos(cos_h) / 15.0

    def at_altitude(self, altitude: float, guess: float, ccw: bool) -> Optional[float]:
        """Time the sun crosses ``altitude`` before (ccw) or after solar noon."""
        t: Optional[float] = guess
        for _ in range(2):
            assert t is not None
            h = self._hour_angle(altitude, self._sun(t).declination)
            if h is None:
                return None
            t = self.noon(t) + (-h if ccw else h)
        return t

    def asr(self, factor: int, guess: float) -> Optional[float]:
        t: Optional[float] = guess
        for _ in range(2):
            assert t is not None
            decl = self._sun(t).declination
            altitude = darctan2(1.0, factor + dtan(abs(self.lat - decl)))
            h = self._hour_angle(altitude, decl)
            if h is None:
                return None
            t = self.noon(t) + h
        return t


def _night_portion(rule: str, angle: float, night: float) -> float:
    if rule == "middle":
        return night / 2
    if rule == "seventh":
        return night / 7
    return angle / 60.0 * night  # "angle"


def compute_utc_hours(d: date, lat: float, lon: float, settings: Settings) -> Dict[str, Optional[float]]:
    """Return each event as hours after 00:00 UTC on ``d`` (None if it doesn't occur)."""
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("latitude must be in [-90, 90] and longitude in [-180, 180]")
    m = settings.method
    s = _Solver(d, lat, lon)
    shift = -lon / 15.0
    horizon = -(0.833 + 0.0347 * math.sqrt(max(0.0, settings.elevation)))

    t: Dict[str, Optional[float]] = {}
    t["fajr"] = s.at_altitude(-m.fajr_angle, _GUESS["fajr"] + shift, ccw=True)
    t["sunrise"] = s.at_altitude(horizon, _GUESS["sunrise"] + shift, ccw=True)
    t["dhuhr"] = s.noon(s.noon(_GUESS["dhuhr"] + shift))
    t["asr"] = s.asr(ASR_FACTORS[settings.asr], _GUESS["asr"] + shift)
    t["sunset"] = s.at_altitude(horizon, _GUESS["sunset"] + shift, ccw=False)
    if m.maghrib_angle is not None:
        t["maghrib"] = s.at_altitude(-m.maghrib_angle, _GUESS["maghrib"] + shift, ccw=False)
    else:
        t["maghrib"] = t["sunset"]
    if m.isha_angle is not None:
        t["isha"] = s.at_altitude(-m.isha_angle, _GUESS["isha"] + shift, ccw=False)
    else:
        t["isha"] = None if t["maghrib"] is None else t["maghrib"] + (m.isha_minutes or 0) / 60.0

    sunrise, sunset = t["sunrise"], t["sunset"]
    if settings.high_lat != "none" and sunrise is not None and sunset is not None:
        night = sunrise + 24.0 - sunset
        p = _night_portion(settings.high_lat, m.fajr_angle, night)
        if t["fajr"] is None or sunrise - t["fajr"] > p:
            t["fajr"] = sunrise - p
        if m.isha_angle is not None:
            p = _night_portion(settings.high_lat, m.isha_angle, night)
            if t["isha"] is None or t["isha"] - sunset > p:
                t["isha"] = sunset + p
        if m.maghrib_angle is not None:
            p = _night_portion(settings.high_lat, m.maghrib_angle, night)
            if t["maghrib"] is None or t["maghrib"] - sunset > p:
                t["maghrib"] = sunset + p

    t["midnight"] = None
    if sunset is not None:
        end = t["fajr"] if m.midnight == "jafari" else sunrise
        if end is not None:
            t["midnight"] = sunset + (end + 24.0 - sunset) / 2.0

    for prayer, minutes in settings.adjustments.items():
        if t.get(prayer) is not None:
            t[prayer] = t[prayer] + minutes / 60.0  # type: ignore[operator]
    return t


def _to_datetime(d: date, hours: float, tz: tzinfo) -> datetime:
    base = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    exact = base + timedelta(hours=hours)
    rounded = (exact + timedelta(seconds=30)).replace(second=0, microsecond=0)
    return rounded.astimezone(tz)


def compute_day(d: date, lat: float, lon: float, tz: tzinfo, settings: Optional[Settings] = None) -> DayTimes:
    """Prayer times for one date, as timezone-aware datetimes rounded to the minute."""
    hours = compute_utc_hours(d, lat, lon, settings or Settings())
    return DayTimes(d, {p: None if h is None else _to_datetime(d, h, tz) for p, h in hours.items()})


def compute_range(
    start: date, days: int, lat: float, lon: float, tz: tzinfo, settings: Optional[Settings] = None
) -> Iterator[DayTimes]:
    settings = settings or Settings()
    for i in range(days):
        yield compute_day(start + timedelta(days=i), lat, lon, tz, settings)
