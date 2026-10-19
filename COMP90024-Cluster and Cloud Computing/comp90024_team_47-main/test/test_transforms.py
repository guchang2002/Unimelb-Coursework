import importlib.util
from pathlib import Path

from shared.transforms.bluesky import is_bot, transform as transform_bluesky, uri_to_web_url
from shared.transforms.mastodon import strip_html, transform as transform_mastodon

ROOT = Path(__file__).resolve().parents[1]
WEATHER_MAIN = ROOT / "backend" / "fission" / "weather_streaming" / "main.py"

spec = importlib.util.spec_from_file_location("weather_streaming_main", WEATHER_MAIN)
weather_streaming_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(weather_streaming_main)


def test_strip_html_removes_tags_and_normalises_spaces():
    assert strip_html("<p>Hello <b>Melbourne</b></p>") == "Hello Melbourne"


def test_mastodon_transform_returns_none_for_reblog():
    assert transform_mastodon({"reblog": {"id": "original"}}) is None


def test_mastodon_transform_builds_expected_document():
    raw_post = {
        "id": "123",
        "content": "<p>I love sunny Melbourne weather and coffee</p>",
        "created_at": "2026-05-01T10:00:00Z",
        "language": "en",
        "account": {
            "id": "a1",
            "acct": "user@mastodon.au",
            "display_name": "User",
            "bot": False,
            "followers_count": 10,
        },
        "tags": [{"name": "weather"}],
        "mentions": [{"acct": "someone"}],
        "url": "https://mastodon.au/@user/123",
        "favourites_count": 2,
        "reblogs_count": 3,
        "replies_count": 4,
    }

    doc = transform_mastodon(raw_post, harvest_strategy="local")

    assert doc["id"] == "mastodon_123"
    assert doc["platform"] == "mastodon"
    assert doc["content_clean"] == "I love sunny Melbourne weather and coffee"
    assert doc["city"] == "Melbourne"
    assert doc["city_inferred_from"] == "content_keyword"
    assert doc["date"] == "2026-05-01"
    assert "sunny" in doc["weather_keywords"]
    assert "weather" in doc["weather_keywords"]
    assert "coffee" in doc["beverage_keywords"]
    assert doc["engagement_score"] == 9
    assert doc["sentiment_label"] == "positive"


def test_bluesky_bot_detection_and_url_conversion():
    assert is_bot("theage.nzcow.com") is True
    assert is_bot("normal-user.bsky.social") is False
    assert (
        uri_to_web_url("at://did:plc:abc/app.bsky.feed.post/xyz")
        == "https://bsky.app/profile/did:plc:abc/post/xyz"
    )


def test_bluesky_transform_builds_expected_document():
    raw_post = {
        "uri": "at://did:plc:abc/app.bsky.feed.post/xyz",
        "cid": "cid123",
        "record": {
            "text": "Cold morning in Sydney, I need a flat white",
            "created_at": "2026-05-02T09:30:00Z",
            "langs": ["en"],
            "facets": [
                {
                    "features": [
                        {"py_type": "app.bsky.richtext.facet#tag", "tag": "Sydney"},
                        {"py_type": "app.bsky.richtext.facet#mention", "did": "did:plc:someone"},
                    ]
                }
            ],
        },
        "author": {
            "did": "did:plc:author",
            "handle": "normal-user.bsky.social",
            "display_name": "Normal User",
        },
        "like_count": 1,
        "repost_count": 2,
        "reply_count": 3,
    }

    doc = transform_bluesky(raw_post, harvest_strategy="search:Sydney")

    assert doc["id"] == "bluesky_cid123"
    assert doc["platform"] == "bluesky"
    assert doc["city"] == "Sydney"
    assert doc["city_inferred_from"] == "search_query"
    assert doc["date"] == "2026-05-02"
    assert doc["language"] == "en"
    assert doc["tags"] == ["sydney"]
    assert doc["mentions"] == ["did:plc:someone"]
    assert "cold" in doc["weather_keywords"]
    assert "coffee" in doc["beverage_keywords"]
    assert doc["engagement_score"] == 6
    assert doc["author_is_bot"] is False


def test_weather_transform_record_builds_expected_document():
    payload = {
        "daily": {
            "time": ["2026-05-03"],
            "temperature_2m_max": [36.5],
            "temperature_2m_min": [12.0],
            "temperature_2m_mean": [24.0],
            "apparent_temperature_max": [38.0],
            "precipitation_sum": [30.0],
            "rain_sum": [28.0],
            "relative_humidity_2m_mean": [70],
            "wind_speed_10m_max": [20.0],
            "weather_code": [61],
        }
    }

    doc = weather_streaming_main.transform_record("Melbourne", payload)

    assert doc["id"] == "weather_melbourne_2026-05-03"
    assert doc["city"] == "Melbourne"
    assert doc["date"] == "2026-05-03"
    assert doc["is_rainy"] is True
    assert doc["is_extreme_hot"] is True
    assert doc["is_heavy_rain"] is True
    assert doc["weather_condition"] == "rain"
    assert doc["location"] == {"lat": -37.8136, "lon": 144.9631}