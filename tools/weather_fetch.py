#!/usr/bin/env python3
"""Fetch real-world weather and write weather.json for the AEE compat addon.

Run: python3 tools/weather_fetch.py --lat 51.5 --lon -0.12 [--name London]

The script uses the Open-Meteo API (https://open-meteo.com), which needs no
API key. It writes weather.json in the format that
addons/compat_realweather/functions/fnc_integrateRealWeather.sqf reads.

weather.json format (all values required):

    {
        "source": "open-meteo",
        "fetchedAt": "2026-09-11T12:00:00Z",
        "location": {"lat": 51.5, "lon": -0.12, "name": "London"},
        "temperatureC": 18.5,   // air temperature in Celsius
        "humidityPct": 72,      // relative humidity in percent (0..100)
        "pressureHpa": 1013.2,  // station pressure in hectopascals
        "overcast": 0.4         // cloud cover fraction (0..1)
    }

Place weather.json in the mission folder (or the server root) so the addon
can read it with loadFile.

The script is standard-library only. If the network is unreachable it prints
a clear error to stderr and exits with a non-zero status.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

API_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_weather(lat: float, lon: float, timeout: float) -> dict:
    """Fetch current weather from Open-Meteo. Raises on network failure."""
    params = (
        f"latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,surface_pressure,cloud_cover"
    )
    url = f"{API_URL}?{params}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lat", type=float, required=True, help="latitude")
    parser.add_argument("--lon", type=float, required=True, help="longitude")
    parser.add_argument("--name", default="", help="location name (optional)")
    parser.add_argument("--output", default="weather.json", help="output file")
    parser.add_argument(
        "--timeout", type=float, default=15.0, help="network timeout in seconds"
    )
    args = parser.parse_args()

    try:
        raw = fetch_weather(args.lat, args.lon, args.timeout)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
    ) as exc:
        print(f"error: could not fetch weather from {API_URL}: {exc}", file=sys.stderr)
        print(
            "error: no network or the API is unreachable; weather.json not written",
            file=sys.stderr,
        )
        return 1

    current = raw.get("current", {})
    try:
        temperature_c = float(current["temperature_2m"])
        humidity_pct = float(current["relative_humidity_2m"])
        pressure_hpa = float(current["surface_pressure"])
        cloud_cover = float(current["cloud_cover"])
    except (KeyError, TypeError, ValueError) as exc:
        print(f"error: unexpected API response: {exc}", file=sys.stderr)
        return 1

    doc = {
        "source": "open-meteo",
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "location": {"lat": args.lat, "lon": args.lon, "name": args.name},
        "temperatureC": temperature_c,
        "humidityPct": humidity_pct,
        "pressureHpa": pressure_hpa,
        "overcast": cloud_cover / 100.0,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"weather.json written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
