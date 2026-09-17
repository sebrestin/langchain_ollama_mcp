---
name: timezone
description: Current time and weekday anywhere in the world, converting a time from one place or timezone to another, and how many hours apart two times in different places are. Use it for every question about times, timezones, time differences or daylight saving time instead of calculating them yourself.
---

# Timezone

Answer time and timezone questions only by running the scripts below. They are deterministic and
handle dates and daylight saving time correctly. Never work out times, dates, conversions or
differences yourself: run the matching script and answer from its JSON output.

## Preparing the arguments

- **Timezones** are IANA names. Translate places to their IANA timezone first: Paris → `Europe/Paris`,
  New York → `America/New_York`, San Francisco → `America/Los_Angeles`, Sydney → `Australia/Sydney`.
  Never pass abbreviations such as `EST` or `CET`.
- **Times** use the 24-hour clock and no UTC offset: 3pm → `15:00`, 9:30am → `09:30`,
  midnight → `00:00`, noon → `12:00`. A full date-time looks like `2026-07-04T15:00`.
- The commands below are examples. Replace every example value with the values from the user's request.

## Scripts

### Current time: `scripts/current_time.py`

Current date, time and weekday in a timezone, or in the local timezone if `--tz` is omitted.

```bash
python scripts/current_time.py --tz <ZONE>
```

Example: `python scripts/current_time.py --tz Asia/Kolkata` prints

```json
{
  "timezone": "Asia/Kolkata",
  "readable": "Tuesday 15 September 2026, 21:10 IST",
  "time": "2026-09-15T21:10:05+05:30",
  "weekday": "Tuesday",
  "utc_offset": "+05:30",
  "abbreviation": "IST"
}
```

### Convert a time: `scripts/convert_timezone.py`

The time in the `--to` timezone that corresponds to `--time` in the `--from` timezone.

```bash
python scripts/convert_timezone.py --time <TIME> --from <ZONE> --to <ZONE> [--days <N>]
```

- `--time` is a full date-time (`2026-07-04T15:00`) or only a time of day (`15:00`), which means
  today in the `--from` timezone.
- `--days` moves the date: `--days 1` for tomorrow, `--days -1` for yesterday.

Example, for "8pm tomorrow in Berlin, in Denver time":
`python scripts/convert_timezone.py --time 20:00 --days 1 --from Europe/Berlin --to America/Denver`.
It prints a `from` and a `to` object shaped like the `current_time.py` output; `to.readable` is
the answer.

### Time difference: `scripts/timezone_delta.py`

How far apart two date-times are, each given in its own timezone. Both times need a full date; if
the user did not give one, get today's date from `current_time.py` first.

```bash
python scripts/timezone_delta.py --time1 <DATE-TIME> --tz1 <ZONE> --time2 <DATE-TIME> --tz2 <ZONE>
```

Example: `python scripts/timezone_delta.py --time1 2026-07-04T09:15 --tz1 Europe/Madrid --time2 2026-07-04T18:45 --tz2 Asia/Singapore` prints

```json
{
  "seconds": 12600.0,
  "hours": 3.5,
  "duration": "3:30:00",
  "earlier": "time1"
}
```

`earlier` says which of the two times happens first: `time1`, `time2` or `equal`.

## Answering

Answer with the values from the script output, such as `readable`, `hours` or `duration`, copied
exactly. Do not add your own explanations of daylight saving time or UTC offsets: the scripts have
already applied the correct rules.

## Errors

A non-zero exit code means an input was rejected, for example an unknown timezone or a
malformed time. Read the error message, fix the arguments and run the script again.
