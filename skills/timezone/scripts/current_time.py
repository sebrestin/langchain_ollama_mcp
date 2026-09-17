"""Print the current time in the local timezone or in a given IANA timezone."""
import argparse
import datetime
import json

from _common import describe, local_zone, zone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tz", type=zone, help="IANA timezone, e.g. Asia/Tokyo (default: the local timezone)")
    args = parser.parse_args()

    tz = args.tz or local_zone()
    now = datetime.datetime.now(tz) if tz else datetime.datetime.now().astimezone()
    print(json.dumps(describe(now), indent=2))


if __name__ == "__main__":
    main()
