import requests

city = "Auburn, Alabama"

latitude = 32.6099
longitude = -85.4808

weather_url = "https://api.open-meteo.com/v1/forecast"

weather_params = {
    "latitude": latitude,
    "longitude": longitude,
    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,apparent_temperature",
    "temperature_unit": "fahrenheit",
    "wind_speed_unit": "mph",
    "timezone": "America/Chicago",
    "forecast_days": 1
}

weather_response = requests.get(weather_url, params=weather_params)
weather_data = weather_response.json()

current_weather = weather_data["current"]

print(f"Weather for {city}")
print(f"Temperature: {current_weather['temperature_2m']} °F")
print(f"Feels Like: {current_weather['apparent_temperature']} °F")
print(f"Humidity: {current_weather['relative_humidity_2m']}%")
print(f"Wind Speed: {current_weather['wind_speed_10m']} mph")