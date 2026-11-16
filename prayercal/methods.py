"""Calculation methods used by major Islamic authorities.

Fajr and Isha are defined by the sun's depression angle below the horizon,
except where an authority uses a fixed interval after Maghrib instead
(``isha_minutes``). Some Shia methods also define Maghrib by an angle.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class Method:
    key: str
    name: str
    fajr_angle: float
    isha_angle: Optional[float] = None
    isha_minutes: Optional[float] = None
    maghrib_angle: Optional[float] = None
    midnight: str = "standard"  # "standard" (sunset→sunrise) or "jafari" (sunset→fajr)

    def __post_init__(self) -> None:
        if (self.isha_angle is None) == (self.isha_minutes is None):
            raise ValueError(f"{self.key}: set exactly one of isha_angle or isha_minutes")


METHODS: Dict[str, Method] = {
    m.key: m
    for m in (
        Method("MWL", "Muslim World League", 18, isha_angle=17),
        Method("ISNA", "Islamic Society of North America", 15, isha_angle=15),
        Method("Egypt", "Egyptian General Authority of Survey", 19.5, isha_angle=17.5),
        Method("Makkah", "Umm al-Qura University, Makkah", 18.5, isha_minutes=90),
        Method("Karachi", "University of Islamic Sciences, Karachi", 18, isha_angle=18),
        Method("Tehran", "Institute of Geophysics, University of Tehran", 17.7, isha_angle=14,
               maghrib_angle=4.5, midnight="jafari"),
        Method("Jafari", "Shia Ithna-Ashari, Leva Institute, Qum", 16, isha_angle=14,
               maghrib_angle=4, midnight="jafari"),
        Method("Gulf", "Gulf Region", 19.5, isha_minutes=90),
        Method("Kuwait", "Kuwait", 18, isha_angle=17.5),
        Method("Qatar", "Qatar", 18, isha_minutes=90),
        Method("Singapore", "Majlis Ugama Islam Singapura", 20, isha_angle=18),
        Method("France", "Union des Organisations Islamiques de France", 12, isha_angle=12),
    )
}

ASR_FACTORS = {"standard": 1, "hanafi": 2}
HIGH_LAT_RULES = ("angle", "middle", "seventh", "none")


def get_method(key: str) -> Method:
    for k, m in METHODS.items():
        if k.lower() == key.lower():
            return m
    raise ValueError(f"unknown method {key!r}; choose from: {', '.join(METHODS)}")
