"""data_loader.py — Centralized data access for Team 47 analytics.

Provides clean, cached functions for loading data from Elasticsearch.
Used by all analytics notebooks (RQ1, RQ2, integrated analysis).

Prerequisites:
    pip install elasticsearch pandas
    kubectl port-forward service/elasticsearch-es-http -n elastic 9200:9200

Usage in a notebook:
    import sys
    sys.path.insert(0, '.')   # if notebook is in frontend/
    from data_loader import load_posts, load_weather, daily_sentiment, get_overview

    mastodon = load_posts("mastodon", cities_only=True)
    bluesky  = load_posts("bluesky",  cities_only=True)
    weather  = load_weather()
"""

import warnings
from typing import List, Optional, Dict

import pandas as pd
from elasticsearch import Elasticsearch

warnings.filterwarnings("ignore")


# ============================================================
# Configuration
# ============================================================

ES_HOST = "https://localhost:9200"
ES_USER = "elastic"
ES_PASS = "elastic"

IDX_MASTODON = "posts_mastodon"
IDX_BLUESKY  = "posts_bluesky"
IDX_WEATHER  = "weather"

CITIES = ["Melbourne", "Sydney", "Brisbane", "Perth"]

# Color palette (consistent across all figures)
COLORS = {
    "Mastodon":   "#1f77b4",
    "BlueSky":    "#ff7f0e",
    "Melbourne":  "#e74c3c",
    "Sydney":     "#3498db",
    "Brisbane":   "#f39c12",
    "Perth":      "#27ae60",
}

# Bot/news accounts — excluded for some analyses (word clouds especially)
BOT_ACCOUNTS_MASTODON = {
    "au@newsbeep.org",
    "australia@masto.ai",
}
BOT_ACCOUNTS_BLUESKY = {
    "toptags.bsky.social",
    "world-info.bsky.social",
    "rankednews.bsky.social",
}

# BlueSky selection-bias filter (weather-keyword historical posts)
CLEAN_BLUESKY_FILTER = {
    "bool": {
        "must_not": [
            {"wildcard": {"harvest_strategy": "*weather*"}},
            {"term":     {"harvest_strategy": "search:heatwave"}},
            {"term":     {"harvest_strategy": "search:polar blast"}},
            {"term":     {"harvest_strategy": "search:auswx"}},
        ]
    }
}


# ============================================================
# ES Connection (singleton)
# ============================================================

_es_client = None


def get_es() -> Elasticsearch:
    """Singleton ES client. Initialized lazily."""
    global _es_client
    if _es_client is None:
        _es_client = Elasticsearch(
            ES_HOST,
            basic_auth=(ES_USER, ES_PASS),
            verify_certs=False,
            request_timeout=60,
        )
        if not _es_client.ping():
            raise RuntimeError(
                f"\n✗ Cannot reach Elasticsearch at {ES_HOST}.\n"
                "Start port-forward in another terminal:\n"
                "    kubectl port-forward service/elasticsearch-es-http -n elastic 9200:9200"
            )
        info = _es_client.info()
        print(f"✓ Connected to Elasticsearch {info['version']['number']}")
    return _es_client


# ============================================================
# Internal: paginated fetch
# ============================================================

def _paginated_fetch(index: str, query: dict, sort: list,
                     source: list, batch_size: int = 5000) -> List[dict]:
    """Fetch all hits from a query using point-in-time + search_after."""
    es = get_es()
    pit = es.open_point_in_time(index=index, keep_alive="2m")["id"]
    records = []
    search_after = None
    
    try:
        while True:
            body = {
                "size":    batch_size,
                "query":   query,
                "sort":    sort,
                "_source": source,
                "pit":     {"id": pit, "keep_alive": "2m"},
            }
            if search_after:
                body["search_after"] = search_after
            
            r = es.search(body=body)
            hits = r["hits"]["hits"]
            if not hits:
                break
            
            for h in hits:
                records.append({"_id": h["_id"], **h["_source"]})
            
            search_after = hits[-1]["sort"]
            if len(hits) < batch_size:
                break
    finally:
        es.close_point_in_time(id=pit)
    
    return records


# ============================================================
# Public API: load posts
# ============================================================

def load_posts(platform: str,
               cities_only: bool = False,
               exclude_bots: bool = False,
               clean_bluesky: bool = True) -> pd.DataFrame:
    """Load posts as a DataFrame from one platform.
    
    Args:
        platform: 'mastodon' or 'bluesky'
        cities_only: if True, only posts with city in 4 target cities
        exclude_bots: if True, exclude known bot/news accounts
        clean_bluesky: if True (default), exclude weather-bias BlueSky posts
    
    Returns:
        DataFrame with columns:
            id, platform, city, date, created_at,
            sentiment_compound, sentiment_label,
            sentiment_pos, sentiment_neg, sentiment_neu,
            author, content_clean, harvest_strategy
    """
    if platform == "mastodon":
        index = IDX_MASTODON
        platform_name = "Mastodon"
        author_field = "author_acct"
        bot_set = BOT_ACCOUNTS_MASTODON
    elif platform == "bluesky":
        index = IDX_BLUESKY
        platform_name = "BlueSky"
        author_field = "author_handle"
        bot_set = BOT_ACCOUNTS_BLUESKY
    else:
        raise ValueError(f"Unknown platform: {platform}")
    
    # Build query
    must_clauses = []
    must_not_clauses = []
    
    if cities_only:
        must_clauses.append({"terms": {"city": CITIES}})
    
    if platform == "bluesky" and clean_bluesky:
        must_not_clauses.extend(CLEAN_BLUESKY_FILTER["bool"]["must_not"])
    
    if exclude_bots and bot_set:
        must_not_clauses.append({"terms": {author_field: list(bot_set)}})
    
    if must_clauses or must_not_clauses:
        query = {"bool": {}}
        if must_clauses:
            query["bool"]["must"] = must_clauses
        if must_not_clauses:
            query["bool"]["must_not"] = must_not_clauses
    else:
        query = {"match_all": {}}
    
    source = [
        "city", "date", "created_at",
        "sentiment_compound", "sentiment_label",
        "sentiment_pos", "sentiment_neg", "sentiment_neu",
        author_field, "content_clean", "harvest_strategy",
    ]
    
    records = _paginated_fetch(index, query, [{"_doc": "asc"}], source)
    
    if not records:
        return pd.DataFrame()
    
    df = pd.DataFrame([
        {
            "id":                 r["_id"],
            "platform":           platform_name,
            "city":               r.get("city"),
            "date":               r.get("date"),
            "created_at":         r.get("created_at"),
            "sentiment_compound": r.get("sentiment_compound"),
            "sentiment_label":    r.get("sentiment_label"),
            "sentiment_pos":      r.get("sentiment_pos"),
            "sentiment_neg":      r.get("sentiment_neg"),
            "sentiment_neu":      r.get("sentiment_neu"),
            "author":             r.get(author_field),
            "content_clean":      r.get("content_clean"),
            "harvest_strategy":   r.get("harvest_strategy"),
        }
        for r in records
    ])
    
    # Parse dates (handle missing gracefully)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    
    return df


# ============================================================
# Public API: load weather
# ============================================================

def load_weather(cities_only: bool = True) -> pd.DataFrame:
    """Load weather records as a DataFrame.
    
    Args:
        cities_only: if True, only the 4 target cities
    
    Returns:
        DataFrame with all weather fields + parsed 'date' column.
    """
    query = ({"terms": {"city": CITIES}} if cities_only
             else {"match_all": {}})
    
    es = get_es()
    pit = es.open_point_in_time(index=IDX_WEATHER, keep_alive="2m")["id"]
    records = []
    search_after = None
    
    try:
        while True:
            body = {
                "size": 1000,
                "query": query,
                "sort": [{"date": "asc"}],
                "pit":  {"id": pit, "keep_alive": "2m"},
            }
            if search_after:
                body["search_after"] = search_after
            
            r = es.search(body=body)
            hits = r["hits"]["hits"]
            if not hits:
                break
            for h in hits:
                records.append(h["_source"])
            search_after = hits[-1]["sort"]
            if len(hits) < 1000:
                break
    finally:
        es.close_point_in_time(id=pit)
    
    df = pd.DataFrame(records)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["city", "date"]).reset_index(drop=True)


# ============================================================
# Public API: derived aggregations
# ============================================================

def daily_sentiment(posts_df: pd.DataFrame,
                    min_posts: int = 3,
                    by_platform: bool = True,
                    by_city: bool = False) -> pd.DataFrame:
    """Aggregate posts to daily mean sentiment.
    
    Args:
        posts_df: DataFrame from load_posts() (can be concat of multiple)
        min_posts: minimum posts/day to keep cell (reliability filter)
        by_platform: aggregate per platform
        by_city: aggregate per city
    
    Returns:
        DataFrame with columns:
            date, [platform], [city], n_posts,
            avg_sentiment_compound, avg_sentiment_pos, avg_sentiment_neg
    """
    df = posts_df.copy()
    # Use 'date' field (yyyy-MM-dd, no timezone) — robust to concat tz issues
    df["day"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df = df[df["day"].notna()]
    
    group_cols = ["day"]
    if by_platform:
        group_cols.append("platform")
    if by_city:
        group_cols.append("city")
    
    agg = df.groupby(group_cols).agg(
        n_posts=("id", "count"),
        avg_sentiment_compound=("sentiment_compound", "mean"),
        avg_sentiment_pos=("sentiment_pos", "mean"),
        avg_sentiment_neg=("sentiment_neg", "mean"),
        avg_sentiment_neu=("sentiment_neu", "mean"),
    ).reset_index()
    
    agg = agg.rename(columns={"day": "date"})
    return agg[agg["n_posts"] >= min_posts].reset_index(drop=True)


def join_posts_weather(daily_sent: pd.DataFrame,
                       weather_df: pd.DataFrame,
                       by_city: bool = False) -> pd.DataFrame:
    """Join daily sentiment with daily weather.
    
    Args:
        daily_sent: output of daily_sentiment()
        weather_df: output of load_weather()
        by_city: if daily_sent has city column, join on (date, city);
                 else average weather across cities per day first
    
    Returns:
        Joined DataFrame
    """
    weather = weather_df.copy()
    weather["date"] = pd.to_datetime(weather["date"]).dt.normalize()
    
    if by_city:
        return daily_sent.merge(weather, on=["date", "city"], how="inner")
    
    # Average weather across cities per day (representative AU baseline)
    numeric_cols = weather.select_dtypes(include="number").columns.tolist()
    weather_avg = (weather.groupby("date")[numeric_cols]
                          .mean().reset_index())
    return daily_sent.merge(weather_avg, on="date", how="inner")


# ============================================================
# Public API: utilities
# ============================================================

def get_overview() -> Dict[str, int]:
    """Quick data inventory."""
    es = get_es()
    return {
        "mastodon_total":  es.count(index=IDX_MASTODON)["count"],
        "bluesky_total":   es.count(index=IDX_BLUESKY)["count"],
        "bluesky_clean":   es.count(index=IDX_BLUESKY, query=CLEAN_BLUESKY_FILTER)["count"],
        "weather_total":   es.count(index=IDX_WEATHER)["count"],
    }


def find_field(df: pd.DataFrame, *keywords: str) -> Optional[str]:
    """Find a column matching ALL given keywords (case-insensitive)."""
    for c in df.columns:
        cl = c.lower()
        if all(k.lower() in cl for k in keywords):
            return c
    return None


# ============================================================
# Smoke test (run module directly)
# ============================================================

if __name__ == "__main__":
    print("Running smoke test for data_loader...\n")
    
    print("Inventory:")
    overview = get_overview()
    for k, v in overview.items():
        print(f"  {k:20s}  {v:,}")
    print()
    
    print("Loading sample of each...")
    m = load_posts("mastodon", cities_only=True)
    print(f"  Mastodon (4 cities): {len(m):,}")
    b = load_posts("bluesky",  cities_only=True)
    print(f"  BlueSky  (4 cities): {len(b):,}")
    w = load_weather()
    print(f"  Weather:             {len(w):,}")
    print()
    
    print("Sample sentiment aggregation:")
    posts = pd.concat([m, b], ignore_index=True)
    daily = daily_sentiment(posts, min_posts=3, by_platform=True)
    print(daily.head(5))
    print()
    
    print(f"Total daily cells: {len(daily)}")
    print(f"Per platform: {daily['platform'].value_counts().to_dict()}")
