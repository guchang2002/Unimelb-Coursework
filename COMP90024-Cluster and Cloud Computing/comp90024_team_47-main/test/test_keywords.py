from shared.keywords import (
    BEVERAGE_KEYWORDS,
    WEATHER_KEYWORDS,
    extract_keywords,
)


def test_extract_weather_keywords():
    assert extract_keywords("Rain and wind in Sydney today", WEATHER_KEYWORDS) == ["rain", "wind"]


def test_extract_beverage_keywords():
    result = extract_keywords("I need a flat white and hot chocolate", BEVERAGE_KEYWORDS)
    assert "coffee" in result
    assert "hot_choc" in result


def test_extract_keywords_counts_each_category_once():
    assert extract_keywords("rain rain rainy drizzle", WEATHER_KEYWORDS) == ["rain"]


def test_extract_keywords_avoids_substring_false_positive():
    # "rain" should not be found inside "Ukraine".
    assert "rain" not in extract_keywords("News about Ukraine today", WEATHER_KEYWORDS)


def test_extract_keywords_empty_text():
    assert extract_keywords("", WEATHER_KEYWORDS) == []