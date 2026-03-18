import datetime
from zoneinfo import ZoneInfo


def current_time():
    """Return the current local time as an ISO 8601 formatted string.

    :return: Current local datetime in ISO 8601 format (e.g. '2026-03-12T14:30:00')
    :rtype: str
    """
    return datetime.datetime.now().isoformat()


def current_timezone():
    """Return the IANA timezone name of the system's current local timezone.

    :return: IANA timezone name (e.g. 'Europe/Athens', 'America/New_York', 'UTC')
    :rtype: str
    """
    return str(datetime.datetime.now().astimezone().tzinfo)


def convert_timezone(time_str, from_tz, to_tz):
    """Convert a datetime string from one timezone to another.

    :param time_str: Datetime string in ISO 8601 format without offset (e.g. '2026-03-12T14:00:00')
    :type time_str: str
    :param from_tz: Source IANA timezone name (e.g. 'America/New_York')
    :type from_tz: str
    :param to_tz: Target IANA timezone name (e.g. 'Europe/London')
    :type to_tz: str

    :return: Converted datetime as an ISO 8601 string with UTC offset
    :rtype: str
    """
    dt = datetime.datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S')
    dt = dt.replace(tzinfo=ZoneInfo(from_tz))
    converted_time = dt.astimezone(ZoneInfo(to_tz))

    return converted_time.isoformat()


def timezone_delta(time_str1, tz1, time_str2, tz2):
    """Calculate the absolute difference in seconds between two datetimes in different timezones.

    :param time_str1: First datetime string in ISO 8601 format without offset (e.g. '2026-03-12T14:00:00')
    :type time_str1: str
    :param tz1: IANA timezone name for the first datetime (e.g. 'America/Chicago')
    :type tz1: str
    :param time_str2: Second datetime string in ISO 8601 format without offset (e.g. '2026-03-12T20:00:00')
    :type time_str2: str
    :param tz2: IANA timezone name for the second datetime (e.g. 'Asia/Tokyo')
    :type tz2: str

    :return: Absolute difference between the two datetimes in seconds
    :rtype: float
    """
    time1 = datetime.datetime.strptime(time_str1, '%Y-%m-%dT%H:%M:%S')
    time2 = datetime.datetime.strptime(time_str2, '%Y-%m-%dT%H:%M:%S')

    time1 = time1.replace(tzinfo=ZoneInfo(tz1))
    time2 = time2.replace(tzinfo=ZoneInfo(tz2))

    delta = abs((time1 - time2).total_seconds())
    return delta