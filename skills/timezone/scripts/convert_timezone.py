"""Convert a wall-clock time in one IANA timezone to the corresponding time in another."""
import argparse
import json

from _common import date_time_or_time, describe, in_zone, zone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--time", type=date_time_or_time, required=True, help="ISO 8601 date-time or time of day without offset, e.g. 2026-03-12T14:00:00 or 14:00 (today in --from)")
    parser.add_argument("--from", dest="from_tz", type=zone, required=True, help="IANA timezone of --time, e.g. America/New_York")
    parser.add_argument("--to", dest="to_tz", type=zone, required=True, help="IANA timezone to convert to, e.g. Europe/London")
    parser.add_argument("--days", type=int, default=0, help="Days to add to the date of --time, e.g. 1 for tomorrow")
    args = parser.parse_args()

    source = in_zone(args.time, args.from_tz, args.days)
    print(json.dumps({"from": describe(source), "to": describe(source.astimezone(args.to_tz))}, indent=2))


if __name__ == "__main__":
    main()
