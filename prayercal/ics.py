"""iCalendar (RFC 5545) output.

Events are written in UTC (``...Z``) so every calendar app places them
correctly without needing VTIMEZONE blocks. The feed's display timezone is
advertised with ``X-WR-TIMEZONE`` for apps that use it.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone, tzinfo
from typing import Dict, Iterable, List, Optional, Sequence

from .hijri import to_hijri
from .times import DISPLAY_NAMES, DayTimes

DEFAULT_PRAYERS = ("fajr", "dhuhr", "asr", "maghrib", "isha")


@dataclass(frozen=True)
class CalendarOptions:
    name: str = "Prayer times"
    prayers: Sequence[str] = DEFAULT_PRAYERS
    duration_minutes: int = 15
    alarm_minutes: Optional[int] = None  # reminder before each event
    jumuah: Optional[time] = None  # replaces Dhuhr on Fridays at this local time
    iqamah: Dict[str, int] = field(default_factory=dict)  # minutes after adhan, shown in description
    hijri_offset: int = 0
    time_format: str = "%-I:%M %p"


def escape_text(value: str) -> str:
    """Escape a TEXT value (RFC 5545 §3.3.11)."""
    return (
        value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    )


def fold(line: str) -> str:
    """Fold a content line to 75 octets, never splitting a UTF-8 character."""
    out: List[str] = []
    current = ""
    size = 0
    limit = 75
    for ch in line:
        n = len(ch.encode("utf-8"))
        if size + n > limit:
            out.append(current)
            current, size, limit = " ", 1, 75
        current += ch
        size += n
    out.append(current)
    return "\r\n".join(out)


def _utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _uid(day: DayTimes, prayer: str, scope: str) -> str:
    digest = hashlib.sha1(f"{scope}|{day.date.isoformat()}|{prayer}".encode()).hexdigest()[:16]
    return f"{day.date:%Y%m%d}-{prayer}-{digest}@prayercal"


def _fmt(dt: datetime, fmt: str) -> str:
    try:
        return dt.strftime(fmt)
    except ValueError:  # "%-I" is not supported on Windows
        return dt.strftime(fmt.replace("%-", "%#"))


def build_calendar(
    days: Iterable[DayTimes],
    tz: tzinfo,
    options: CalendarOptions,
    scope: str,
    now: Optional[datetime] = None,
) -> str:
    """Render prayer times as an iCalendar document (CRLF line endings).

    ``scope`` should identify the location and method (for example
    ``"40.71,-74.01,ISNA"``) so event UIDs stay stable when the feed is
    regenerated and differ between feeds.
    """
    stamp = _utc(now or datetime.now(timezone.utc))
    tz_name = getattr(tz, "key", None) or str(tz)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//prayercal//prayercal//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(options.name)}",
        f"X-WR-TIMEZONE:{tz_name}",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:P1D",
    ]

    for day in days:
        hijri = to_hijri(day.date, options.hijri_offset)
        is_friday = day.date.weekday() == 4
        for prayer in options.prayers:
            start = day[prayer]
            summary = DISPLAY_NAMES[prayer]
            if prayer == "dhuhr" and is_friday and options.jumuah is not None:
                start = datetime.combine(day.date, options.jumuah, tzinfo=tz)
                summary = "Jumu'ah"
            if start is None:
                continue  # the event doesn't occur (polar day or night)

            details = [f"{summary} {_fmt(start, options.time_format)}"]
            if prayer in options.iqamah:
                iqamah = start + timedelta(minutes=options.iqamah[prayer])
                details.append(f"Iqamah {_fmt(iqamah, options.time_format)}")
            details.append(f"{hijri} (approx.)")
            if hijri.month == 9 and prayer == "fajr":
                details.append("Ramadan: suhoor ends")
            if hijri.month == 9 and prayer == "maghrib":
                details.append("Ramadan: iftar")

            lines += [
                "BEGIN:VEVENT",
                f"UID:{_uid(day, prayer, scope)}",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{_utc(start)}",
                f"DURATION:PT{options.duration_minutes}M",
                f"SUMMARY:{escape_text(summary)}",
                f"DESCRIPTION:{escape_text(chr(10).join(details))}",
                "TRANSP:TRANSPARENT",
                "CATEGORIES:Prayer",
            ]
            if options.alarm_minutes is not None:
                lines += [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:{escape_text(summary)}",
                    f"TRIGGER:-PT{options.alarm_minutes}M",
                    "END:VALARM",
                ]
            lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(line) for line in lines) + "\r\n"
