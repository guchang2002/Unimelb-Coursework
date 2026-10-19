import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import Elasticsearch


# ============================================================
# Elasticsearch config
# ============================================================

ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_USERNAME = os.getenv("ES_USERNAME", "")
ES_PASSWORD = os.getenv("ES_PASSWORD", "")
ES_VERIFY_CERTS = os.getenv("ES_VERIFY_CERTS", "false").lower() in ["true", "1", "yes"]

BLUESKY_INDEX = os.getenv("BLUESKY_INDEX", "posts_bluesky")
MASTODON_INDEX = os.getenv("MASTODON_INDEX", "posts_mastodon")
WEATHER_INDEX = os.getenv("WEATHER_INDEX", "weather")

INDEX_MAP = {
    "bluesky": BLUESKY_INDEX,
    "mastodon": MASTODON_INDEX,
    "weather": WEATHER_INDEX,
}


def create_es_client() -> Elasticsearch:
    if ES_USERNAME and ES_PASSWORD:
        return Elasticsearch(
            ES_HOST,
            basic_auth=(ES_USERNAME, ES_PASSWORD),
            verify_certs=ES_VERIFY_CERTS,
            request_timeout=30,
        )

    return Elasticsearch(
        ES_HOST,
        verify_certs=ES_VERIFY_CERTS,
        request_timeout=30,
    )


es = create_es_client()


# ============================================================
# FastAPI app
# ============================================================

app = FastAPI(
    title="COMP90024 RESTful API",
    description="RESTful API layer for BlueSky, Mastodon, and Weather data stored in Elasticsearch.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Helper functions
# ============================================================

def get_index_by_platform(platform: str) -> str:
    platform = platform.lower().strip()

    if platform not in INDEX_MAP:
        raise HTTPException(
            status_code=400,
            detail="platform must be one of: bluesky, mastodon, weather",
        )

    return INDEX_MAP[platform]


def get_post_index(platform: str) -> str:
    platform = platform.lower().strip()

    if platform not in ["bluesky", "mastodon"]:
        raise HTTPException(
            status_code=400,
            detail="platform must be bluesky or mastodon",
        )

    return INDEX_MAP[platform]


def get_time_field(index_name: str) -> str:
    if index_name in [BLUESKY_INDEX, MASTODON_INDEX]:
        return "created_at"

    if index_name == WEATHER_INDEX:
        return "date"

    return "created_at"


def get_sort_clause(index_name: str):
    time_field = get_time_field(index_name)

    return [
        {
            time_field: {
                "order": "desc",
                "unmapped_type": "date",
            }
        }
    ]


def get_total_value(total_obj) -> int:
    if isinstance(total_obj, dict):
        return int(total_obj.get("value", 0))
    return int(total_obj)


def es_count(index_name: str) -> int:
    try:
        return int(es.count(index=index_name)["count"])
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to count documents in index {index_name}: {str(exc)}",
        )


def es_search(index_name: str, body: dict):
    try:
        return es.search(index=index_name, body=body)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to search index {index_name}: {str(exc)}",
        )


# ============================================================
# Basic endpoints
# ============================================================

@app.get("/")
def root():
    return {
        "message": "COMP90024 RESTful API is running",
        "docs": "/docs",
        "endpoints": [
            "/api/health",
            "/api/summary",
            "/api/posts?platform=mastodon",
            "/api/posts?platform=bluesky",
            "/api/weather",
            "/api/timeseries?platform=mastodon",
            "/api/timeseries?platform=bluesky",
            "/api/timeseries?platform=weather",
            "/api/search?q=melbourne",
            "/api/sentiment?platform=mastodon",
            "/api/sentiment?platform=bluesky",
            "/api/weather/summary",
            "/api/compare/counts",
            "/api/sample",
        ],
    }


@app.get("/api/health")
def health():
    try:
        elasticsearch_ok = es.ping()

        indices = {}
        for platform, index_name in INDEX_MAP.items():
            indices[platform] = {
                "index": index_name,
                "exists": bool(es.indices.exists(index=index_name)),
            }

        return {
            "api_status": "ok",
            "elasticsearch_status": "ok" if elasticsearch_ok else "unreachable",
            "es_host": ES_HOST,
            "indices": indices,
        }

    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/summary")
def summary():
    result = {}
    total_documents = 0

    for platform, index_name in INDEX_MAP.items():
        count = es_count(index_name)
        result[platform] = {
            "index": index_name,
            "count": count,
        }
        total_documents += count

    return {
        "total_documents": total_documents,
        "by_source": result,
    }


# ============================================================
# Posts endpoints
# ============================================================

@app.get("/api/posts")
def get_posts(
    platform: str = Query(..., description="bluesky or mastodon"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    index_name = get_post_index(platform)

    body = {
        "from": offset,
        "size": limit,
        "track_total_hits": True,
        "query": {
            "match_all": {}
        },
        "sort": get_sort_clause(index_name),
    }

    response = es_search(index_name, body)

    items = []
    for hit in response["hits"]["hits"]:
        source = hit.get("_source", {})
        source["_id"] = hit.get("_id")
        source["_index"] = hit.get("_index")
        items.append(source)

    return {
        "platform": platform,
        "index": index_name,
        "offset": offset,
        "limit": limit,
        "total": get_total_value(response["hits"]["total"]),
        "items": items,
    }


@app.get("/api/search")
def search_posts(
    q: str = Query(..., min_length=1, description="keyword to search"),
    platform: Optional[str] = Query(None, description="optional: bluesky or mastodon"),
    limit: int = Query(100, ge=1, le=500),
):
    if platform:
        indices = [get_post_index(platform)]
    else:
        indices = [BLUESKY_INDEX, MASTODON_INDEX]

    all_items = []
    total = 0

    for index_name in indices:
        body = {
            "size": limit,
            "track_total_hits": True,
            "query": {
                "multi_match": {
                    "query": q,
                    "fields": [
                        "content_clean",
                        "author_display_name",
                        "author_handle",
                        "author_acct",
                        "raw_payload.record.text",
                        "raw_payload.content",
                        "raw_payload.card.title",
                        "raw_payload.embed.external.title",
                        "raw_payload.embed.external.description",
                    ],
                    "lenient": True,
                }
            },
            "sort": get_sort_clause(index_name),
        }

        response = es_search(index_name, body)
        total += get_total_value(response["hits"]["total"])

        for hit in response["hits"]["hits"]:
            source = hit.get("_source", {})
            source["_id"] = hit.get("_id")
            source["_index"] = hit.get("_index")
            source["_score"] = hit.get("_score")
            all_items.append(source)

    return {
        "query": q,
        "platform": platform,
        "searched_indices": indices,
        "total": total,
        "items": all_items[:limit],
    }


@app.get("/api/timeseries")
def timeseries(
    platform: str = Query(..., description="bluesky, mastodon, or weather"),
    interval: str = Query("day", pattern="^(hour|day|week|month)$"),
):
    index_name = get_index_by_platform(platform)
    time_field = get_time_field(index_name)

    body = {
        "size": 0,
        "query": {
            "match_all": {}
        },
        "aggs": {
            "items_over_time": {
                "date_histogram": {
                    "field": time_field,
                    "calendar_interval": interval,
                    "min_doc_count": 0,
                }
            }
        },
    }

    response = es_search(index_name, body)
    buckets = response.get("aggregations", {}).get("items_over_time", {}).get("buckets", [])

    return {
        "platform": platform,
        "index": index_name,
        "time_field": time_field,
        "interval": interval,
        "items": [
            {
                "time": bucket.get("key_as_string"),
                "count": bucket.get("doc_count"),
            }
            for bucket in buckets
        ],
    }


@app.get("/api/sentiment")
def sentiment_summary(
    platform: str = Query(..., description="bluesky or mastodon"),
):
    index_name = get_post_index(platform)

    body = {
        "size": 0,
        "query": {
            "match_all": {}
        },
        "aggs": {
            "sentiment_distribution": {
                "terms": {
                    "field": "sentiment_label",
                    "size": 10,
                }
            },
            "average_sentiment": {
                "avg": {
                    "field": "sentiment_compound"
                }
            },
            "min_sentiment": {
                "min": {
                    "field": "sentiment_compound"
                }
            },
            "max_sentiment": {
                "max": {
                    "field": "sentiment_compound"
                }
            },
        },
    }

    response = es_search(index_name, body)
    aggs = response.get("aggregations", {})

    buckets = aggs.get("sentiment_distribution", {}).get("buckets", [])

    return {
        "platform": platform,
        "index": index_name,
        "sentiment_distribution": {
            bucket["key"]: bucket["doc_count"]
            for bucket in buckets
        },
        "average_sentiment_compound": aggs.get("average_sentiment", {}).get("value"),
        "min_sentiment_compound": aggs.get("min_sentiment", {}).get("value"),
        "max_sentiment_compound": aggs.get("max_sentiment", {}).get("value"),
    }


@app.get("/api/engagement")
def engagement_summary(
    platform: str = Query(..., description="bluesky or mastodon"),
):
    index_name = get_post_index(platform)

    if platform == "bluesky":
        aggs = {
            "avg_like_count": {"avg": {"field": "like_count"}},
            "avg_reply_count": {"avg": {"field": "reply_count"}},
            "avg_repost_count": {"avg": {"field": "repost_count"}},
            "avg_engagement_score": {"avg": {"field": "engagement_score"}},
            "max_engagement_score": {"max": {"field": "engagement_score"}},
        }
    else:
        aggs = {
            "avg_favourites_count": {"avg": {"field": "favourites_count"}},
            "avg_replies_count": {"avg": {"field": "replies_count"}},
            "avg_reblogs_count": {"avg": {"field": "reblogs_count"}},
            "avg_engagement_score": {"avg": {"field": "engagement_score"}},
            "max_engagement_score": {"max": {"field": "engagement_score"}},
        }

    body = {
        "size": 0,
        "query": {
            "match_all": {}
        },
        "aggs": aggs,
    }

    response = es_search(index_name, body)

    return {
        "platform": platform,
        "index": index_name,
        "engagement_summary": response.get("aggregations", {}),
    }


@app.get("/api/top-posts")
def top_posts(
    platform: str = Query(..., description="bluesky or mastodon"),
    limit: int = Query(10, ge=1, le=100),
):
    index_name = get_post_index(platform)

    body = {
        "size": limit,
        "track_total_hits": True,
        "query": {
            "match_all": {}
        },
        "sort": [
            {
                "engagement_score": {
                    "order": "desc",
                    "unmapped_type": "long",
                }
            }
        ],
    }

    response = es_search(index_name, body)

    items = []
    for hit in response["hits"]["hits"]:
        source = hit.get("_source", {})
        source["_id"] = hit.get("_id")
        source["_index"] = hit.get("_index")
        items.append(source)

    return {
        "platform": platform,
        "index": index_name,
        "limit": limit,
        "total": get_total_value(response["hits"]["total"]),
        "items": items,
    }


# ============================================================
# Weather endpoints
# ============================================================

@app.get("/api/weather")
def get_weather(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    index_name = WEATHER_INDEX

    body = {
        "from": offset,
        "size": limit,
        "track_total_hits": True,
        "query": {
            "match_all": {}
        },
        "sort": get_sort_clause(index_name),
    }

    response = es_search(index_name, body)

    items = []
    for hit in response["hits"]["hits"]:
        source = hit.get("_source", {})
        source["_id"] = hit.get("_id")
        source["_index"] = hit.get("_index")
        items.append(source)

    return {
        "index": index_name,
        "offset": offset,
        "limit": limit,
        "total": get_total_value(response["hits"]["total"]),
        "items": items,
    }


@app.get("/api/weather/summary")
def weather_summary():
    index_name = WEATHER_INDEX

    body = {
        "size": 0,
        "query": {
            "match_all": {}
        },
        "aggs": {
            "avg_temp_max": {"avg": {"field": "temp_max"}},
            "avg_temp_mean": {"avg": {"field": "temp_mean"}},
            "avg_temp_min": {"avg": {"field": "temp_min"}},
            "avg_apparent_temp_max": {"avg": {"field": "apparent_temp_max"}},
            "avg_humidity": {"avg": {"field": "humidity"}},
            "avg_precipitation_mm": {"avg": {"field": "precipitation_mm"}},
            "avg_rain_mm": {"avg": {"field": "rain_mm"}},
            "avg_wind_speed_max": {"avg": {"field": "wind_speed_max"}},
            "rainy_days": {
                "filter": {
                    "term": {
                        "is_rainy": True
                    }
                }
            },
            "heavy_rain_days": {
                "filter": {
                    "term": {
                        "is_heavy_rain": True
                    }
                }
            },
            "extreme_hot_days": {
                "filter": {
                    "term": {
                        "is_extreme_hot": True
                    }
                }
            },
            "extreme_cold_days": {
                "filter": {
                    "term": {
                        "is_extreme_cold": True
                    }
                }
            },
            "weather_conditions": {
                "terms": {
                    "field": "weather_condition",
                    "size": 20,
                }
            },
        },
    }

    response = es_search(index_name, body)
    aggs = response.get("aggregations", {})

    return {
        "index": index_name,
        "average_temp_max": aggs.get("avg_temp_max", {}).get("value"),
        "average_temp_mean": aggs.get("avg_temp_mean", {}).get("value"),
        "average_temp_min": aggs.get("avg_temp_min", {}).get("value"),
        "average_apparent_temp_max": aggs.get("avg_apparent_temp_max", {}).get("value"),
        "average_humidity": aggs.get("avg_humidity", {}).get("value"),
        "average_precipitation_mm": aggs.get("avg_precipitation_mm", {}).get("value"),
        "average_rain_mm": aggs.get("avg_rain_mm", {}).get("value"),
        "average_wind_speed_max": aggs.get("avg_wind_speed_max", {}).get("value"),
        "rainy_days": aggs.get("rainy_days", {}).get("doc_count"),
        "heavy_rain_days": aggs.get("heavy_rain_days", {}).get("doc_count"),
        "extreme_hot_days": aggs.get("extreme_hot_days", {}).get("doc_count"),
        "extreme_cold_days": aggs.get("extreme_cold_days", {}).get("doc_count"),
        "weather_conditions": {
            bucket["key"]: bucket["doc_count"]
            for bucket in aggs.get("weather_conditions", {}).get("buckets", [])
        },
    }


# ============================================================
# Compare endpoints
# ============================================================

@app.get("/api/compare/counts")
def compare_counts():
    bluesky_count = es_count(BLUESKY_INDEX)
    mastodon_count = es_count(MASTODON_INDEX)
    weather_count = es_count(WEATHER_INDEX)

    return {
        "bluesky": {
            "index": BLUESKY_INDEX,
            "count": bluesky_count,
        },
        "mastodon": {
            "index": MASTODON_INDEX,
            "count": mastodon_count,
        },
        "weather": {
            "index": WEATHER_INDEX,
            "count": weather_count,
        },
        "total": bluesky_count + mastodon_count + weather_count,
    }


@app.get("/api/compare/sentiment")
def compare_sentiment():
    result = {}

    for platform, index_name in {
        "bluesky": BLUESKY_INDEX,
        "mastodon": MASTODON_INDEX,
    }.items():
        body = {
            "size": 0,
            "query": {
                "match_all": {}
            },
            "aggs": {
                "sentiment_distribution": {
                    "terms": {
                        "field": "sentiment_label",
                        "size": 10,
                    }
                },
                "average_sentiment": {
                    "avg": {
                        "field": "sentiment_compound"
                    }
                },
            },
        }

        response = es_search(index_name, body)
        aggs = response.get("aggregations", {})

        result[platform] = {
            "index": index_name,
            "sentiment_distribution": {
                bucket["key"]: bucket["doc_count"]
                for bucket in aggs.get("sentiment_distribution", {}).get("buckets", [])
            },
            "average_sentiment_compound": aggs.get("average_sentiment", {}).get("value"),
        }

    return result


@app.get("/api/compare/volume")
def compare_volume(
    interval: str = Query("day", pattern="^(hour|day|week|month)$"),
):
    result = {}

    for platform, index_name in {
        "bluesky": BLUESKY_INDEX,
        "mastodon": MASTODON_INDEX,
    }.items():
        time_field = get_time_field(index_name)

        body = {
            "size": 0,
            "query": {
                "match_all": {}
            },
            "aggs": {
                "items_over_time": {
                    "date_histogram": {
                        "field": time_field,
                        "calendar_interval": interval,
                        "min_doc_count": 0,
                    }
                }
            },
        }

        response = es_search(index_name, body)
        buckets = response.get("aggregations", {}).get("items_over_time", {}).get("buckets", [])

        result[platform] = {
            "index": index_name,
            "time_field": time_field,
            "items": [
                {
                    "time": bucket.get("key_as_string"),
                    "count": bucket.get("doc_count"),
                }
                for bucket in buckets
            ],
        }

    return {
        "interval": interval,
        "platforms": result,
    }


@app.get("/api/sample")
def sample_all(
    limit: int = Query(5, ge=1, le=50),
):
    result = {}

    for platform, index_name in INDEX_MAP.items():
        body = {
            "size": limit,
            "query": {
                "match_all": {}
            },
            "sort": get_sort_clause(index_name),
        }

        response = es_search(index_name, body)

        result[platform] = {
            "index": index_name,
            "time_field": get_time_field(index_name),
            "items": [
                {
                    "_id": hit.get("_id"),
                    "_source": hit.get("_source", {}),
                }
                for hit in response["hits"]["hits"]
            ],
        }

    return result