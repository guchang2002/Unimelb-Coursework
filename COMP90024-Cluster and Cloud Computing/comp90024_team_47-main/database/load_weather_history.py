#!/usr/bin/env python
"""
COMP90024 Team 47 — Weather history backfill (one-shot)

Fetches 1 year of daily weather data for 4 Australian cities from
Open-Meteo Archive API and bulk-indexes into ES `weather` index.

Usage:
    python database/load_weather_history.py

Requirements:
    pip install requests urllib3
    kubectl port-forward service/elasticsearch-es-http -n elastic 9200:9200
    
ES credentials and date range can be overridden via environment variables.
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =================== Configuration ===================

CITIES = {
    "Melbourne": {"lat": -37.8136, "lon": 144.9631, "state": "VIC"},
    "Sydney":    {"lat": -33.8688, "lon": 151.2093, "state": "NSW"},
    "Brisbane":  {"lat": -27.4698, "lon": 153.0251, "state": "QLD"},
    "Perth":     {"lat": -31.9505, "lon": 115.8605, "state": "WA"},
}

# Date range (inclusive). Override with env vars to re-run for different periods.
START_DATE = os.environ.get("WEATHER_START_DATE", "2025-05-01")
END_DATE   = os.environ.get("WEATHER_END_DATE",   "2026-04-30")

ES_URL  = os.environ.get("ES_URL", "https://localhost:9200")
ES_USER = os.environ.get("ES_USER", "elastic")
ES_PASS = os.environ.get("ES_PASSWORD", "elastic")

INDEX = "weather"


# =================== WMO weather code → readable label ===================
def code_to_condition(code):
    if code == 0:
        return "clear"
    if code in (1, 2, 3):
        return "partly_cloudy"
    if code in (45, 48):
        return "fog"
    if 51 <= code <= 67:
        return "rain"
    if 71 <= code <= 77:
        return "snow"
    if 80 <= code <= 82:
        return "rain_showers"
    if 95 <= code <= 99:
        return "thunderstorm"
    return "unknown"


# =================== Fetch one city ===================
def fetch_city(city_name, lat, lon):
    """Returns Open-Meteo daily payload for one city."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":    lat,
        "longitude":   lon,
        "start_date":  START_DATE,
        "end_date":    END_DATE,
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
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


# =================== Transform: one city's payload → list of ES docs ===================
def transform_city(city_name, payload):
    coords = CITIES[city_name]
    daily = payload.get("daily", {})
    dates = daily.get("time", [])
    docs = []

    for i, date in enumerate(dates):
        def g(key):
            arr = daily.get(key, [])
            return arr[i] if i < len(arr) else None

        temp_max = g("temperature_2m_max")
        temp_min = g("temperature_2m_min")
        rain_mm  = g("precipitation_sum") or 0.0
        code     = g("weather_code") or 0

        doc = {
            "id":              f"weather_{city_name.lower()}_{date}",
            "city":            city_name,
            "date":            date,

            "temp_max":        temp_max,
            "temp_min":        temp_min,
            "temp_mean":       g("temperature_2m_mean"),
            "apparent_temp_max": g("apparent_temperature_max"),

            "precipitation_mm": rain_mm,
            "rain_mm":         g("rain_sum"),
            "is_rainy":        rain_mm > 1.0,

            "humidity":        g("relative_humidity_2m_mean"),
            "wind_speed_max":  g("wind_speed_10m_max"),

            "weather_code":    int(code) if code is not None else 0,
            "weather_condition": code_to_condition(code or 0),

            "is_extreme_hot":  bool(temp_max is not None and temp_max > 35),
            "is_extreme_cold": bool(temp_min is not None and temp_min < 5),
            "is_heavy_rain":   rain_mm > 25,

            "lat":             coords["lat"],
            "lon":             coords["lon"],
            "location":        {"lat": coords["lat"], "lon": coords["lon"]},

            "source":          "open-meteo-archive",
            "fetched_at":      datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        docs.append(doc)

    return docs


# =================== Bulk index to ES ===================
def bulk_index(docs):
    if not docs:
        return 0, 0

    lines = []
    for doc in docs:
        lines.append(json.dumps({"index": {"_index": INDEX, "_id": doc["id"]}}))
        lines.append(json.dumps(doc, default=str))
    body = "\n".join(lines) + "\n"

    r = requests.post(
        f"{ES_URL}/_bulk",
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/x-ndjson"},
        auth=(ES_USER, ES_PASS),
        verify=False,
        timeout=120,
    )
    r.raise_for_status()
    result = r.json()
    
    indexed = sum(1 for it in result["items"] if "error" not in it.get("index", {}))
    failed  = len(result["items"]) - indexed
    
    if failed:
        # Show first error
        for it in result["items"]:
            if "error" in it.get("index", {}):
                print(f"  ❌ Sample error: {json.dumps(it['index']['error'], indent=2)[:300]}")
                break
    
    return indexed, failed


# =================== Main ===================
def main():
    print(f"=== Weather history backfill ===")
    print(f"  Date range: {START_DATE} → {END_DATE}")
    print(f"  Cities:     {', '.join(CITIES.keys())}")
    print(f"  ES:         {ES_URL}")
    print()

    total_indexed = 0
    total_failed  = 0

    for city, info in CITIES.items():
        print(f"📍 {city}...")
        try:
            payload = fetch_city(city, info["lat"], info["lon"])
            docs = transform_city(city, payload)
            print(f"   Fetched {len(docs)} daily records")
            
            indexed, failed = bulk_index(docs)
            total_indexed += indexed
            total_failed  += failed
            print(f"   ✅ Indexed {indexed} | failed {failed}")
        except Exception as e:
            print(f"   ❌ {e}")

    print()
    print(f"=== Done ===")
    print(f"   Total indexed: {total_indexed}")
    print(f"   Total failed:  {total_failed}")

    # Final count check
    r = requests.get(f"{ES_URL}/{INDEX}/_count", auth=(ES_USER, ES_PASS), verify=False)
    if r.status_code == 200:
        print(f"   ES {INDEX} doc count: {r.json()['count']}")


if __name__ == "__main__":
    main()
