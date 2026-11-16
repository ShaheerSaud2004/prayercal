# Roadmap

Planned work for prayercal, roughly in priority order.

## 0.2: feeds that update themselves

- [ ] `prayercal serve`: a tiny HTTP server that generates `.ics` on request from query parameters, so calendar apps can subscribe to a URL
- [ ] A GitHub Actions template that regenerates a feed on a schedule and publishes it with GitHub Pages
- [ ] A config file (`prayercal.toml`) so a masjid's settings live in one place instead of long command lines
- [ ] Iqamah as its own event (not just a note), with fixed-time iqamah rules such as "Isha at 8:00 PM, or 10 minutes after adhan if later"

## 0.3: matching real timetables

- [ ] Umm al-Qura's 120-minute Ramadan Isha
- [ ] The Moonsighting Committee's seasonal Fajr and Isha formulas
- [ ] Turkey's Diyanet method with its per-prayer offsets
- [ ] A `compare` command that diffs computed times against a masjid's published CSV and suggests `--adjust` values
- [ ] A city lookup from a bundled list, so `--city "Toronto"` fills in coordinates and time zone

## 0.4: calendar and output formats

- [ ] Umm al-Qura Hijri calendar data, alongside the tabular calendar
- [ ] CSV, JSON and printable HTML/PDF monthly timetables
- [ ] Localised event names (Arabic, Urdu, French, Turkish, Malay)
- [ ] Optional events for Islamic dates: Ramadan start, Eid, Day of Arafah, Ashura

## Quality

- [ ] More reference cities and dates, including the southern hemisphere in winter and points above the Arctic Circle
- [ ] Property tests: prayer order stays correct and times change smoothly from day to day
- [ ] Publish to PyPI
- [ ] Windows CI job
