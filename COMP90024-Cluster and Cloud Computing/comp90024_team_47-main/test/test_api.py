from fastapi.testclient import TestClient

from api import main as api_main


class FakeIndices:
    def exists(self, index):
        return index in {"posts_bluesky", "posts_mastodon", "weather"}


class FakeES:
    def __init__(self):
        self.indices = FakeIndices()

    def ping(self):
        return True

    def count(self, index):
        counts = {
            "posts_bluesky": 2,
            "posts_mastodon": 3,
            "weather": 4,
        }
        return {"count": counts[index]}

    def search(self, index, body):
        if body.get("size") == 0 and "aggs" in body:
            return {
                "hits": {"total": {"value": 0}},
                "aggregations": {
                    "items_over_time": {
                        "buckets": [
                            {"key_as_string": "2026-05-01T00:00:00.000Z", "doc_count": 5}
                        ]
                    },
                    "sentiment_distribution": {
                        "buckets": [
                            {"key": "positive", "doc_count": 2},
                            {"key": "negative", "doc_count": 1},
                        ]
                    },
                    "average_sentiment": {"value": 0.25},
                    "min_sentiment": {"value": -0.5},
                    "max_sentiment": {"value": 0.8},
                    "avg_temp_max": {"value": 22.0},
                    "avg_temp_mean": {"value": 18.0},
                    "avg_temp_min": {"value": 12.0},
                    "avg_apparent_temp_max": {"value": 23.0},
                    "avg_humidity": {"value": 65.0},
                    "avg_precipitation_mm": {"value": 1.5},
                    "avg_rain_mm": {"value": 1.0},
                    "avg_wind_speed_max": {"value": 20.0},
                    "rainy_days": {"doc_count": 3},
                    "heavy_rain_days": {"doc_count": 1},
                    "extreme_hot_days": {"doc_count": 0},
                    "extreme_cold_days": {"doc_count": 0},
                    "weather_conditions": {
                        "buckets": [
                            {"key": "rain", "doc_count": 2},
                            {"key": "clear", "doc_count": 5},
                        ]
                    },
                    "avg_engagement_score": {"value": 4.5},
                    "max_engagement_score": {"value": 10},
                },
            }

        source = {
            "id": "doc_1",
            "platform": "mastodon" if index == "posts_mastodon" else "bluesky",
            "content_clean": "Rain in Melbourne today",
            "city": "Melbourne",
            "created_at": "2026-05-01T10:00:00Z",
            "sentiment_label": "neutral",
            "sentiment_compound": 0.0,
        }

        if index == "weather":
            source = {
                "id": "weather_melbourne_2026-05-01",
                "city": "Melbourne",
                "date": "2026-05-01",
                "temp_max": 20.0,
                "precipitation_mm": 1.2,
                "is_rainy": True,
            }

        return {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": source["id"],
                        "_index": index,
                        "_score": 1.0,
                        "_source": source,
                    }
                ],
            }
        }


def get_client(monkeypatch):
    monkeypatch.setattr(api_main, "es", FakeES())
    return TestClient(api_main.app)


def test_root_endpoint(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "COMP90024 RESTful API is running"
    assert "/api/health" in data["endpoints"]


def test_health_endpoint(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["api_status"] == "ok"
    assert data["elasticsearch_status"] == "ok"
    assert data["indices"]["bluesky"]["exists"] is True
    assert data["indices"]["mastodon"]["exists"] is True
    assert data["indices"]["weather"]["exists"] is True


def test_summary_endpoint(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/api/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["total_documents"] == 9
    assert data["by_source"]["bluesky"]["count"] == 2
    assert data["by_source"]["mastodon"]["count"] == 3
    assert data["by_source"]["weather"]["count"] == 4


def test_get_posts_endpoint(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/api/posts?platform=mastodon&limit=10")

    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "mastodon"
    assert data["index"] == "posts_mastodon"
    assert data["total"] == 1
    assert data["items"][0]["city"] == "Melbourne"
    assert data["items"][0]["_index"] == "posts_mastodon"


def test_get_posts_rejects_weather_platform(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/api/posts?platform=weather")

    assert response.status_code == 400
    assert response.json()["detail"] == "platform must be bluesky or mastodon"


def test_search_endpoint(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/api/search?q=Melbourne&platform=bluesky")

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Melbourne"
    assert data["platform"] == "bluesky"
    assert data["searched_indices"] == ["posts_bluesky"]
    assert data["total"] == 1


def test_timeseries_endpoint(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/api/timeseries?platform=weather&interval=day")

    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "weather"
    assert data["index"] == "weather"
    assert data["time_field"] == "date"
    assert data["items"][0]["count"] == 5


def test_sentiment_endpoint(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/api/sentiment?platform=mastodon")

    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "mastodon"
    assert data["sentiment_distribution"]["positive"] == 2
    assert data["average_sentiment_compound"] == 0.25
    assert data["min_sentiment_compound"] == -0.5
    assert data["max_sentiment_compound"] == 0.8


def test_weather_endpoint(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/api/weather?limit=5")

    assert response.status_code == 200
    data = response.json()
    assert data["index"] == "weather"
    assert data["items"][0]["city"] == "Melbourne"
    assert data["items"][0]["is_rainy"] is True


def test_weather_summary_endpoint(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/api/weather/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["average_temp_max"] == 22.0
    assert data["rainy_days"] == 3
    assert data["weather_conditions"]["rain"] == 2


def test_compare_counts_endpoint(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/api/compare/counts")

    assert response.status_code == 200
    data = response.json()
    assert data["bluesky"]["count"] == 2
    assert data["mastodon"]["count"] == 3
    assert data["weather"]["count"] == 4
    assert data["total"] == 9


def test_sample_endpoint(monkeypatch):
    client = get_client(monkeypatch)

    response = client.get("/api/sample?limit=1")

    assert response.status_code == 200
    data = response.json()
    assert "bluesky" in data
    assert "mastodon" in data
    assert "weather" in data
    assert data["weather"]["time_field"] == "date"