import pandas as pd
import openmeteo_requests

import requests_cache
from retry_requests import retry


url = "https://archive-api.open-meteo.com/v1/archive"


def get_weather(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """ Get the weather for a location. Can only get weather at most current date.
    
        :param lat: Latitude of the location
        :type lat: float
        :param lon: Longitude of the location
        :type lon: float
        :param start_date: Start date of the weather data, format YYYY-MM-DD
        :type start_date: str
        :param end_date: End date of the weather data, format YYYY-MM-DD
        :type end_date: str

        :return: DataFrame containing the weather data
    """

    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
    retry_session = retry(cache_session, retries = 0, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ["sunrise", "sunset", "rain_sum", "snowfall_sum", "precipitation_sum", "weather_code", "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean", "apparent_temperature_mean", "apparent_temperature_max", "apparent_temperature_min", "wind_speed_10m_max", "wind_gusts_10m_max", "wind_direction_10m_dominant", "shortwave_radiation_sum", "et0_fao_evapotranspiration", "sunshine_duration", "daylight_duration", "precipitation_hours"],
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]

    # Process daily data. The order of variables needs to be the same as requested.
    daily = response.Daily()
    daily_sunrise = daily.Variables(0).ValuesInt64AsNumpy()
    daily_sunset = daily.Variables(1).ValuesInt64AsNumpy()
    daily_rain_sum = daily.Variables(2).ValuesAsNumpy()
    daily_snowfall_sum = daily.Variables(3).ValuesAsNumpy()
    daily_precipitation_sum = daily.Variables(4).ValuesAsNumpy()
    daily_weather_code = daily.Variables(5).ValuesAsNumpy()
    daily_temperature_2m_max = daily.Variables(6).ValuesAsNumpy()
    daily_temperature_2m_min = daily.Variables(7).ValuesAsNumpy()
    daily_temperature_2m_mean = daily.Variables(8).ValuesAsNumpy()
    daily_apparent_temperature_mean = daily.Variables(9).ValuesAsNumpy()
    daily_apparent_temperature_max = daily.Variables(10).ValuesAsNumpy()
    daily_apparent_temperature_min = daily.Variables(11).ValuesAsNumpy()
    daily_wind_speed_10m_max = daily.Variables(12).ValuesAsNumpy()
    daily_wind_gusts_10m_max = daily.Variables(13).ValuesAsNumpy()
    daily_wind_direction_10m_dominant = daily.Variables(14).ValuesAsNumpy()
    daily_shortwave_radiation_sum = daily.Variables(15).ValuesAsNumpy()
    daily_et0_fao_evapotranspiration = daily.Variables(16).ValuesAsNumpy()
    daily_sunshine_duration = daily.Variables(17).ValuesAsNumpy()
    daily_daylight_duration = daily.Variables(18).ValuesAsNumpy()
    daily_precipitation_hours = daily.Variables(19).ValuesAsNumpy()

    daily_data = {"date": pd.date_range(
        start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
        end =  pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
        freq = pd.Timedelta(seconds = daily.Interval()),
        inclusive = "left"
    )}

    daily_data["sunrise"] = daily_sunrise
    daily_data["sunset"] = daily_sunset
    daily_data["rain_sum"] = daily_rain_sum
    daily_data["snowfall_sum"] = daily_snowfall_sum
    daily_data["precipitation_sum"] = daily_precipitation_sum
    daily_data["weather_code"] = daily_weather_code
    daily_data["temperature_2m_max"] = daily_temperature_2m_max
    daily_data["temperature_2m_min"] = daily_temperature_2m_min
    daily_data["temperature_2m_mean"] = daily_temperature_2m_mean
    daily_data["apparent_temperature_mean"] = daily_apparent_temperature_mean
    daily_data["apparent_temperature_max"] = daily_apparent_temperature_max
    daily_data["apparent_temperature_min"] = daily_apparent_temperature_min
    daily_data["wind_speed_10m_max"] = daily_wind_speed_10m_max
    daily_data["wind_gusts_10m_max"] = daily_wind_gusts_10m_max
    daily_data["wind_direction_10m_dominant"] = daily_wind_direction_10m_dominant
    daily_data["shortwave_radiation_sum"] = daily_shortwave_radiation_sum
    daily_data["et0_fao_evapotranspiration"] = daily_et0_fao_evapotranspiration
    daily_data["sunshine_duration"] = daily_sunshine_duration
    daily_data["daylight_duration"] = daily_daylight_duration
    daily_data["precipitation_hours"] = daily_precipitation_hours

    daily_dataframe = pd.DataFrame(data = daily_data).to_json()

    print(daily_dataframe)
    return daily_dataframe


def current_date() -> str:
    """Get the current date.

        :return: Current date in YYYY-MM-DD format
    """
    return pd.Timestamp.now().strftime("%Y-%m-%d")


if __name__ == "__main__":
    print(get_weather(46.770, 23.591, "2026-01-28", "2026-01-28")) 
    print(current_date())