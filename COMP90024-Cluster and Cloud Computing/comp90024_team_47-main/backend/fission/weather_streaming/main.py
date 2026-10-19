"""Fission function: weather_streaming
Triggered by daily cron, fetches yesterday's weather for 4 AU cities,
indexes into ES `weather` index.

Idempotent: re-runs overwrite by deterministic _id (weather_<city>_<date>).
"""

import os
import sys
from datetime import datetime, timedelta, timezone

# Make ./shared importable (shared/ is bundled into this function's zip)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from shared.cities import CITIES
from shared.weather_codes import code_to_condition
from shared.es_client import bulk_index, count


def fetch_one(city, lat, lon, date_str):
    """Fetch one day of weather for one city from Open-Meteo Archive API."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": date_str,
        "end_date":   date_str,
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "apparent_temperature_max",
            "precipitation_sum",
            "rain_sum",
            "weather_code",
            "wind_speed_10m_max",
            "relative_humidity_2m_mean",
        ]),
        "timezone": "Australia/Sydney",
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def transform_record(city, payload):
    """Open-Meteo daily payload -> ES weather doc (1 day, 1 city)."""
    coords = CITIES[city]
    daily = payload.get("daily", {})
    dates = daily.get("time", [])

    if not dates:
        return None

    i = 0  # We only fetch 1 day
    date = dates[i]

    def g(key):
        arr = daily.get(key, [])
        return arr[i] if i < len(arr) else None

    temp_max = g("temperature_2m_max")
    temp_min = g("temperature_2m_min")
    rain_mm  = g("precipitation_sum") or 0.0
    code     = g("weather_code") or 0

    return {
        "id":               f"weather_{city.lower()}_{date}",
        "city":             city,
        "date":             date,

        "temp_max":         temp_max,
        "temp_min":         temp_min,
        "temp_mean":        g("temperature_2m_mean"),
        "apparent_temp_max": g("apparent_temperature_max"),

        "precipitation_mm": rain_mm,
        "rain_mm":          g("rain_sum"),
        "is_rainy":         rain_mm > 1.0,

        "humidity":         g("relative_humidity_2m_mean"),
        "wind_speed_max":   g("wind_speed_10m_max"),

        "weather_code":     int(code) if code is not None else 0,
        "weather_condition": code_to_condition(code or 0),

        "is_extreme_hot":   bool(temp_max is not None and temp_max > 35),
        "is_extreme_cold":  bool(temp_min is not None and temp_min < 5),
        "is_heavy_rain":    rain_mm > 25,

        "lat":              coords["lat"],
        "lon":              coords["lon"],
        "location":         {"lat": coords["lat"], "lon": coords["lon"]},

        "source":           "open-meteo-archive-streaming",
        "fetched_at":       datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main():
    """Fission entry point. Returns dict (auto-serialized to JSON response)."""
    # Yesterday in Sydney TZ (Open-Meteo uses Australia/Sydney)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    results = {
        "date":          yesterday,
        "cities":        {},
        "indexed_total": 0,
        "failed_total":  0,
        "started_at":    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    docs = []
    for city, info in CITIES.items():
        try:
            payload = fetch_one(city, info["lat"], info["lon"], yesterday)
            doc = transform_record(city, payload)
            if doc is None:
                results["cities"][city] = "no_data"
                continue
            docs.append(doc)
            results["cities"][city] = "ok"
        except Exception as e:
            results["cities"][city] = f"error: {str(e)[:200]}"

    if docs:
        try:
            indexed, failed = bulk_index("weather", docs)
            results["indexed_total"] = indexed
            results["failed_total"]  = failed
        except Exception as e:
            results["bulk_error"] = str(e)[:300]

    results["weather_index_count"] = count("weather")
    results["finished_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return results
