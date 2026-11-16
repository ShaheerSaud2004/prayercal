# prayercal

**prayercal** calculates the five daily prayer times for any place on Earth and turns them into an **`.ics` calendar feed** you can subscribe to in Google Calendar, Apple Calendar or Outlook. It's a small command-line tool and Python library with no dependencies and no API calls: the sun's position is computed locally from your coordinates.

It's for:
- **People** who want prayer times next to their meetings, with reminders, without installing an app or sharing their location with one
- **Masjids and MSAs** that want a calendar link to publish, with a fixed Jumu'ah time and iqamah times in each event

```text
$ prayercal times --lat 40.7128 --lon -74.0060 --tz America/New_York --method ISNA --days 3
Islamic Society of North America · Asr standard · America/New_York
Date       Hijri (approx.)               Fajr     Sunrise  Dhuhr    Asr      Maghrib  Isha
2026-11-16 5 Jumada al-Thani 1448 AH     05:25 AM 06:44 AM 11:41 AM 02:17 PM 04:37 PM 05:56 PM
2026-11-17 6 Jumada al-Thani 1448 AH     05:26 AM 06:45 AM 11:41 AM 02:16 PM 04:36 PM 05:55 PM
2026-11-18 7 Jumada al-Thani 1448 AH     05:27 AM 06:46 AM 11:41 AM 02:15 PM 04:36 PM 05:55 PM
```

## Features

- **12 calculation methods:** MWL, ISNA, Egypt, Umm al-Qura (Makkah), Karachi, Tehran, Jafari, Gulf, Kuwait, Qatar, Singapore and France
- **Asr:** standard (Shafi'i, Maliki, Hanbali) or Hanafi
- **High latitudes:** angle-based, middle-of-the-night and one-seventh rules for places where twilight lasts all night, such as London or Oslo in summer
- **Per-prayer minute adjustments** to match a local masjid's timetable, plus elevation
- **Calendar feeds:**
  - Jumu'ah replaces Dhuhr on Fridays at a time you set
  - Iqamah times go in the event notes
  - Optional reminders
  - Ramadan suhoor and iftar labels
  - Stable event IDs, so re-importing updates events instead of duplicating them
- **Hijri dates** from the tabular Islamic calendar, with an offset option to match local moon sighting
- **DST-correct:** times are computed in UTC and converted with IANA time zones

### Accuracy

The tests compare 64 times (8 places and dates × 8 events) with an independent reference, the AlAdhan API. The places cover New York, Makkah, London in winter and summer, Karachi with Hanafi Asr, Oslo in midsummer, Toronto and Jakarta. 61 times match exactly and 3 differ by one minute because of rounding.

## Built with

- Python 3.9+ standard library only (`zoneinfo` for time zones)
- Solar position from the U.S. Naval Observatory's approximate solar-coordinate formulas, which are accurate to about one arcminute
- `unittest` tests, run in GitHub Actions on Python 3.9–3.13

## Install

```bash
git clone https://github.com/ShaheerSaud2004/prayercal
cd prayercal
python3 -m pip install .
```

Or run it without installing: `python3 -m prayercal --help`.

## Usage

Find your coordinates from any map; right-clicking a spot in Google Maps shows them.

**Print a timetable:**

```bash
prayercal times --lat 21.4225 --lon 39.8262 --tz Asia/Riyadh --method Makkah --days 7
```

**Make a year-long calendar:**

```bash
prayercal ics --lat 40.7128 --lon -74.0060 --tz America/New_York \
  --method ISNA --asr hanafi --days 365 \
  --jumuah 13:15 --iqamah fajr=20,dhuhr=10,asr=10,maghrib=5,isha=10 \
  --alarm 10 --name "Prayer times – New York" -o prayer-times.ics
```

Import `prayer-times.ics` into your calendar app. For a feed that keeps itself up to date, regenerate the file on a schedule (for example with a GitHub Actions cron job) and publish it at a URL, then subscribe to that URL. See the roadmap for a built-in way to do this.

**Other options:**

```bash
prayercal methods                         # list calculation methods and their angles
--prayers fajr,sunrise,dhuhr,asr,maghrib,isha,midnight   # choose which events to include
--adjust maghrib=3,isha=-2                # nudge times to match a masjid
--high-lat seventh                        # angle (default), middle, seventh or none
--elevation 300                           # metres; makes sunrise slightly earlier and sunset slightly later
--hijri-offset -1                         # shift Hijri dates to match local sighting
--start 2027-02-01 --days 30              # date range (default: today, 7 days for times, 365 for ics)
--24h                                     # 24-hour clock in the times table
```

### As a library

```python
from datetime import date
from zoneinfo import ZoneInfo
from prayercal import Settings, compute_day, get_method

day = compute_day(date(2026, 11, 16), 40.7128, -74.0060, ZoneInfo("America/New_York"),
                  Settings(method=get_method("ISNA"), asr="standard"))
print(day["fajr"], day["isha"])
```

## Project layout

```text
prayercal/
  astro.py     solar declination and equation of time
  methods.py   calculation methods (angles and intervals)
  times.py     prayer-time solver and high-latitude rules
  hijri.py     tabular Hijri calendar
  ics.py       iCalendar writer (RFC 5545 escaping, line folding, alarms)
  cli.py       `prayercal times | ics | methods`
tests/         reference-time, behaviour, calendar and CLI tests
```

## Development

```bash
python3 -m unittest discover -s tests -v
```

## Notes

- Hijri dates use the arithmetic (tabular) calendar and are labelled *approx.* They can differ from Umm al-Qura or local moon sighting by a day or two; use `--hijri-offset` to adjust.
- Umm al-Qura extends Isha to 120 minutes during Ramadan. prayercal doesn't do that yet (see the roadmap); use `--adjust isha=30` for that month.
- Always follow your local masjid's timetable where it differs.

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## License

[MIT](LICENSE)
