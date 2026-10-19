from shared.weather_codes import code_to_condition


def test_known_weather_codes():
    assert code_to_condition(0) == "clear"
    assert code_to_condition(2) == "partly_cloudy"
    assert code_to_condition(61) == "rain"
    assert code_to_condition(73) == "snow"
    assert code_to_condition(95) == "thunderstorm"


def test_unknown_weather_code():
    assert code_to_condition(None) == "unknown"
    assert code_to_condition(999) == "unknown"