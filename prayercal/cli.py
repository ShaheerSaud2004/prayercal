"""Command-line interface.

    prayercal times --lat 40.71 --lon -74.01 --tz America/New_York --method ISNA
    prayercal ics   --lat 40.71 --lon -74.01 --tz America/New_York --days 365 -o prayer.ics
    prayercal methods
"""

import argparse
import sys
from datetime import date, datetime, time
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import __version__
from .hijri import to_hijri
from .ics import DEFAULT_PRAYERS, CalendarOptions, build_calendar
from .methods import ASR_FACTORS, HIGH_LAT_RULES, METHODS, get_method
from .times import DISPLAY_NAMES, PRAYERS, Settings, compute_range


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date {value!r}; use YYYY-MM-DD") from None


def _parse_time(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid time {value!r}; use HH:MM (24-hour)") from None


def _parse_minutes_map(value: str) -> Dict[str, float]:
    """Parse ``fajr=2,isha=-3`` into {"fajr": 2.0, "isha": -3.0}."""
    out: Dict[str, float] = {}
    for part in filter(None, (p.strip() for p in value.split(","))):
        name, sep, minutes = part.partition("=")
        name = name.strip().lower()
        if not sep or name not in PRAYERS:
            raise argparse.ArgumentTypeError(
                f"invalid entry {part!r}; use prayer=minutes with prayers from: {', '.join(PRAYERS)}"
            )
        try:
            out[name] = float(minutes)
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid minutes in {part!r}") from None
    return out


def _parse_prayers(value: str) -> List[str]:
    names = [p.strip().lower() for p in value.split(",") if p.strip()]
    bad = [p for p in names if p not in PRAYERS]
    if bad or not names:
        raise argparse.ArgumentTypeError(f"choose prayers from: {', '.join(PRAYERS)}")
    return names


def _add_location_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("location")
    g.add_argument("--lat", type=float, required=True, help="latitude in degrees (north positive)")
    g.add_argument("--lon", type=float, required=True, help="longitude in degrees (east positive)")
    g.add_argument("--tz", required=True, help="IANA timezone, e.g. America/New_York")
    g.add_argument("--elevation", type=float, default=0.0, help="metres above the horizon (default 0)")

    c = p.add_argument_group("calculation")
    c.add_argument("--method", default="MWL", help="calculation method (see `prayercal methods`)")
    c.add_argument("--asr", choices=sorted(ASR_FACTORS), default="standard",
                   help="standard (Shafi'i, Maliki, Hanbali) or hanafi")
    c.add_argument("--high-lat", choices=HIGH_LAT_RULES, default="angle",
                   help="rule for Fajr/Isha when twilight persists (default angle)")
    c.add_argument("--adjust", type=_parse_minutes_map, default={},
                   help="minute tweaks per prayer, e.g. maghrib=3,isha=-2")
    c.add_argument("--start", type=_parse_date, default=None, help="first date (default today)")
    c.add_argument("--days", type=int, default=None, help="number of days")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prayercal",
        description="Prayer times and subscribable .ics calendars from coordinates.",
    )
    parser.add_argument("--version", action="version", version=f"prayercal {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("times", help="print a table of prayer times")
    _add_location_args(t)
    t.add_argument("--24h", dest="h24", action="store_true", help="24-hour clock")

    i = sub.add_parser("ics", help="write an iCalendar feed")
    _add_location_args(i)
    i.add_argument("-o", "--output", default="-", help="output file (default stdout)")
    i.add_argument("--name", default=None, help="calendar name shown in calendar apps")
    i.add_argument("--prayers", type=_parse_prayers, default=list(DEFAULT_PRAYERS),
                   help=f"comma-separated events (default {','.join(DEFAULT_PRAYERS)})")
    i.add_argument("--duration", type=int, default=15, help="event length in minutes (default 15)")
    i.add_argument("--alarm", type=int, default=None, help="reminder N minutes before each event")
    i.add_argument("--jumuah", type=_parse_time, default=None,
                   help="replace Dhuhr on Fridays with Jumu'ah at this local time, e.g. 13:30")
    i.add_argument("--iqamah", type=_parse_minutes_map, default={},
                   help="iqamah offsets in minutes, e.g. fajr=20,isha=10 (shown in event notes)")
    i.add_argument("--hijri-offset", type=int, default=0, help="shift Hijri dates by N days")

    sub.add_parser("methods", help="list calculation methods")
    return parser


def _settings(args: argparse.Namespace) -> Settings:
    return Settings(
        method=get_method(args.method),
        asr=args.asr,
        high_lat=args.high_lat,
        elevation=args.elevation,
        adjustments=args.adjust,
    )


def _cmd_methods() -> int:
    for m in METHODS.values():
        isha = f"{m.isha_angle}°" if m.isha_angle is not None else f"{m.isha_minutes:g} min"
        maghrib = f"{m.maghrib_angle}°" if m.maghrib_angle is not None else "sunset"
        print(f"{m.key:<10} fajr {m.fajr_angle:>4}°  isha {isha:<7} maghrib {maghrib:<7} {m.name}")
    return 0


def _cmd_times(args: argparse.Namespace, tz: ZoneInfo, settings: Settings) -> int:
    fmt = "%H:%M" if args.h24 else "%I:%M %p"
    cols = ["fajr", "sunrise", "dhuhr", "asr", "maghrib", "isha"]
    width = 8 if args.h24 else 9
    print(f"{settings.method.name} · Asr {args.asr} · {tz.key}")
    print(f"{'Date':<11}{'Hijri (approx.)':<30}" + "".join(f"{DISPLAY_NAMES[c]:<{width}}" for c in cols))
    for day in compute_range(args.start, args.days, args.lat, args.lon, tz, settings):
        cells = []
        for c in cols:
            v = day[c]
            cells.append(f"{(v.strftime(fmt) if v else '--'):<{width}}")
        print(f"{day.date.isoformat():<11}{str(to_hijri(day.date)):<30}" + "".join(cells))
    return 0


def _cmd_ics(args: argparse.Namespace, tz: ZoneInfo, settings: Settings) -> int:
    name = args.name or f"Prayer times ({settings.method.key})"
    options = CalendarOptions(
        name=name,
        prayers=args.prayers,
        duration_minutes=args.duration,
        alarm_minutes=args.alarm,
        jumuah=args.jumuah,
        iqamah={k: int(v) for k, v in args.iqamah.items()},
        hijri_offset=args.hijri_offset,
    )
    scope = f"{args.lat:.4f},{args.lon:.4f},{settings.method.key},{args.asr}"
    days = compute_range(args.start, args.days, args.lat, args.lon, tz, settings)
    text = build_calendar(days, tz, options, scope)
    if args.output == "-":
        sys.stdout.write(text)
    else:
        with open(args.output, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        print(f"wrote {args.days} days to {args.output}", file=sys.stderr)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "methods":
        return _cmd_methods()

    try:
        tz = ZoneInfo(args.tz)
    except (ZoneInfoNotFoundError, ValueError):
        parser.error(f"unknown timezone {args.tz!r}")
    try:
        settings = _settings(args)
    except ValueError as exc:
        parser.error(str(exc))
    if not -90 <= args.lat <= 90 or not -180 <= args.lon <= 180:
        parser.error("latitude must be in [-90, 90] and longitude in [-180, 180]")

    if args.start is None:
        args.start = datetime.now(tz).date()
    if args.days is None:
        args.days = 7 if args.command == "times" else 365
    if args.days < 1 or args.days > 3660:
        parser.error("--days must be between 1 and 3660")

    if args.command == "times":
        return _cmd_times(args, tz, settings)
    return _cmd_ics(args, tz, settings)


if __name__ == "__main__":
    sys.exit(main())
