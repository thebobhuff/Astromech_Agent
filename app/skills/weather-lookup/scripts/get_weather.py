import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Retrieve weather information for a specified location.")
    parser.add_argument("location", help="The city or location to get weather for.")
    parser.add_argument("--forecast", action="store_true", help="Get a weather forecast instead of current conditions.")
    parser.add_argument("--tomorrow", action="store_true", help="Get the weather forecast for tomorrow.")

    args = parser.parse_args()

    location = args.location

    if args.forecast:
        if args.tomorrow:
            print(f"Weather forecast for {location} tomorrow: Expect partly cloudy skies, high of 70F (21C), low of 55F (13C). (Placeholder forecast)")
        else:
            print(f"Weather forecast for {location}: Expect mostly sunny skies for the next few days. (Placeholder forecast)")
    else:
        print(f"Current weather for {location}: Currently sunny, 75F (24C) with a light breeze. (Placeholder information)")

if __name__ == "__main__":
    main()
