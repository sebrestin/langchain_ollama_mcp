"""Compute how far apart two wall-clock times are, each given in its own IANA timezone."""
import argparse
import datetime
import json

from _common import date_time, zone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--time1", type=date_time, required=True, help="First ISO 8601 date-time without offset")
    parser.add_argument("--tz1", type=zone, required=True, help="IANA timezone of --time1")
    parser.add_argument("--time2", type=date_time, required=True, help="Second ISO 8601 date-time without offset")
    parser.add_argument("--tz2", type=zone, required=True, help="IANA timezone of --time2")
    args = parser.parse_args()

    # Compare in UTC: subtracting datetimes that share a tzinfo ignores DST changes between them
    first = args.time1.replace(tzinfo=args.tz1).astimezone(datetime.UTC)
    second = args.time2.replace(tzinfo=args.tz2).astimezone(datetime.UTC)
    delta = abs(first - second)

    print(json.dumps({
        "seconds": delta.total_seconds(),
        "hours": round(delta.total_seconds() / 3600, 4),
        "duration": str(delta),
        "earlier": "equal" if first == second else "time1" if first < second else "time2",
    }, indent=2))


if __name__ == "__main__":
    main()
