---
name: weather-lookup
description: Retrieves current weather conditions and forecasts for a specified location. Use when you need to know the weather for a city or region.
---

# Weather Lookup

# Weather Lookup Skill

## Usage

This skill allows you to retrieve current weather conditions and a short forecast for a specified location.

To use this skill, you would typically run a script with the desired location as an argument.

Example:
```bash
python scripts/get_weather.py "London"
```

## Expected Output

The script would provide information such as:
- Current temperature
- Weather conditions (e.g., "Sunny", "Cloudy", "Rain")
- Humidity
- Wind speed

## Implementation Details (Hypothetical)

This skill assumes the presence of a `scripts/get_weather.py` script that interfaces with a weather API (e.g., OpenWeatherMap, AccuWeather) to fetch the weather data. The script would parse the location and return the relevant weather information.
