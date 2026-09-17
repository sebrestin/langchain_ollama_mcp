"""Helpers shared by the timezone scripts. Not meant to be run directly."""
import argparse
import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def zone(name):
    """argparse type for an IANA timezone name such as 'Europe/London'."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise argparse.ArgumentTypeError(
            f"unknown IANA timezone {name!r}, expected a name like 'Europe/London'"
        ) from None


def date_time(value):
    """argparse type for an ISO 8601 date-time without a UTC offset, such as '2026-03-12T14:00:00'."""
    try:
        moment = datetime.datetime.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid date-time {value!r}, expected ISO 8601 like '2026-03-12T14:00:00'"
        ) from None
    return _without_offset(moment, value)


def date_time_or_time(value):
    """argparse type for an ISO 8601 date-time or time of day without a UTC offset, such as '14:00'."""
    try:
        moment = datetime.datetime.fromisoformat(value)
    except ValueError:
        try:
            moment = datetime.time.fromisoformat(value)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"invalid time {value!r}, expected ISO 8601 like '2026-03-12T14:00:00' or '14:00'"
            ) from None
    return _without_offset(moment, value)


def _without_offset(moment, value):
    if moment.tzinfo is not None:
        raise argparse.ArgumentTypeError(f"{value!r} must not include a UTC offset, pass its timezone separately")
    return moment


def in_zone(moment, tz, days=0):
    """Place a wall-clock date-time in tz, shifted by a number of days.

    A time of day without a date is taken on today's date in tz.
    """
    if isinstance(moment, datetime.time):
        moment = datetime.datetime.combine(datetime.datetime.now(tz).date(), moment)
    return (moment + datetime.timedelta(days=days)).replace(tzinfo=tz)


def local_zone():
    """Return the local timezone as a ZoneInfo, or None if it is not a known IANA timezone."""
    # TZ overrides the system configuration, the same way it does for the C library
    if "TZ" in os.environ:
        name = os.environ["TZ"].removeprefix(":")
    elif Path("/etc/timezone").is_file():
        name = Path("/etc/timezone").read_text().strip()
    else:
        parts = Path("/etc/localtime").resolve().parts
        name = "/".join(parts[parts.index("zoneinfo") + 1:]) if "zoneinfo" in parts else ""

    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def describe(moment):
    """Describe a timezone-aware datetime as a JSON-serializable dict."""
    return {
        "timezone": getattr(moment.tzinfo, "key", None),
        "readable": moment.strftime("%A %d %B %Y, %H:%M %Z"),
        "time": moment.isoformat(timespec="seconds"),
        "weekday": moment.strftime("%A"),
        "utc_offset": moment.strftime("%:z"),
        "abbreviation": moment.tzname(),
    }
