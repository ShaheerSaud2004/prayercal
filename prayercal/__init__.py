"""prayercal: prayer times and subscribable .ics calendars from coordinates."""

from .hijri import HijriDate, to_hijri
from .ics import CalendarOptions, build_calendar
from .methods import METHODS, Method, get_method
from .times import PRAYERS, DayTimes, Settings, compute_day, compute_range

__version__ = "0.1.0"

__all__ = [
    "METHODS",
    "PRAYERS",
    "CalendarOptions",
    "DayTimes",
    "HijriDate",
    "Method",
    "Settings",
    "__version__",
    "build_calendar",
    "compute_day",
    "compute_range",
    "get_method",
    "to_hijri",
]
