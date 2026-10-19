"""WMO weather code -> human-readable condition."""


def code_to_condition(code):
    """Map Open-Meteo's WMO weather_code to a keyword string."""
    if code is None:
        return "unknown"
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
