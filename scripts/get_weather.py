import requests
import json

def get_weather(city):
    url = f"https://api.open-meteo.com/v1/forecast?latitude=29.76&longitude=-95.37&current=temperature_2m,weather_code&hourly=temperature_2m,relative_humidity_2m,weather_code&timezone=America%2FChicago"
    response = requests.get(url)
    weather_data = response.json()
    
    current_temp = weather_data['current']['temperature_2m']
    weather_code = weather_data['current']['weather_code']
    
    weather_meanings = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Drizzle: Light intensity",
        53: "Drizzle: Moderate intensity",
        55: "Drizzle: Dense intensity",
        56: "Freezing Drizzle: Light intensity",
        57: "Freezing Drizzle: Dense intensity",
        61: "Rain: Slight intensity",
        63: "Rain: Moderate intensity",
        65: "Rain: Heavy intensity",
        66: "Freezing Rain: Light intensity",
        67: "Freezing Rain: Heavy intensity",
        71: "Snow fall: Slight intensity",
        73: "Snow fall: Moderate intensity",
        75: "Snow fall: Heavy intensity",
        77: "Snow grains",
        80: "Rain showers: Slight intensity",
        81: "Rain showers: Moderate intensity",
        82: "Rain showers: Violent intensity",
        85: "Snow showers: Slight intensity",
        86: "Snow showers: Heavy intensity",
        95: "Thunderstorm: Slight or moderate",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }
    
    weather_description = weather_meanings.get(weather_code, "Unknown")
    
    print(f"Current temperature in {city}: {current_temp}°C")
    print(f"Weather condition: {weather_description}")

if __name__ == "__main__":
    get_weather("Houston")