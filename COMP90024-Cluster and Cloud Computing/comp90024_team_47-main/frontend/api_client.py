"""api_client.py — HTTP API access layer (alternative to data_loader.py).

Provides the same public API as data_loader, but fetches data via
the RESTful API served by backend/api/main.py instead of direct ES.

This module exists to satisfy COMP90024 A2 requirement:
"The server side of your application should expose its data to the
 JupyterNotebook through a RESTful design."

The notebook can switch transparently between ES (data_loader) and 
HTTP (api_client) by changing one import line.

Prerequisites:
    pip install requests pandas
    kubectl port-forward svc/ccc-rest-api 8000:80
"""

import warnings
from typing import Dict, Optional

import requests
import pandas as pd

warnings.filterwarnings("ignore")


# ============================================================
# Configuration (mirrors data_loader.py)
# ============================================================

API_BASE = "http://localhost:8000/api"
API_TIMEOUT = 60

CITIES = ["Melbourne", "Sydney", "Brisbane", "Perth"]

COLORS = {
    "Mastodon":   "#1f77b4",
    "BlueSky":    "#ff7f0e",
    "Melbourne":  "#e74c3c",
    "Sydney":     "#3498db",
    "Brisbane":   "#f39c12",
    "Perth":      "#27ae60",
}

# BlueSky selection-bias filter (same as data_loader)
# Applied client-side after fetch since API doesn't expose this filter
WEATHER_BIAS_STRATEGIES = {
    "search:heatwave",
    "search:polar blast",
    "search:auswx",
}


# ============================================================
# HTTP session (connection pool)
# ============================================================

_session = None


def get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        # Quick health check
        try:
            r = _session.get(f"{API_BASE}/health", timeout=5)
            r.raise_for_status()
            print(f"✓ Connected to API at {API_BASE}")
        except Exception as e:
            raise RuntimeError(
                f"\n✗ Cannot reach API at {API_BASE}.\n"
                "Start port-forward in another terminal:\n"
                "    kubectl port-forward svc/ccc-rest-api 8000:80\n"
                f"Error: {e}"
            )
    return _session


# ============================================================
# Public API: load_posts
# ============================================================

def load_posts(platform: str,
               cities_only: bool = False,
               exclude_bots: bool = False,
               clean_bluesky: bool = True,
               batch_size: int = 500) -> pd.DataFrame:
    """Load posts via HTTP API. Same signature as data_loader.load_posts.
    
    Note: Filtering (cities, bots, weather-bias) is applied client-side
    after fetch, since the API does not expose all these filter options.
    
    Args:
        platform: 'mastodon' or 'bluesky'
        cities_only: if True, filter to 4 target cities client-side
        exclude_bots: if True, exclude known bots client-side
        clean_bluesky: if True (default), apply weather-bias filter
        batch_size: pagination size per request
    """

    batch_size = min(batch_size, 500) # API max limit is 500

    if platform not in ("mastodon", "bluesky"):
        raise ValueError(f"Unknown platform: {platform}")
    
    session = get_session()
    
    all_items = []
    offset = 0
    total = None
    
    while True:
        url = f"{API_BASE}/posts"
        params = {
            "platform": platform,
            "limit": batch_size,
            "offset": offset,
        }
        
        r = session.get(url, params=params, timeout=API_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        
        items = data.get("items", [])
        if not items:
            break
        
        if total is None:
            total = data.get("total", 0)
            print(f"  Fetching {total:,} {platform} posts via API "
                  f"(batches of {batch_size})...")
        
        all_items.extend(items)
        offset += len(items)
        
        # Progress
        if offset % (batch_size * 5) == 0 or offset >= total:
            print(f"    {offset:,} / {total:,}")
        
        if offset >= total or len(items) < batch_size:
            break
    
    if not all_items:
        return pd.DataFrame()
    
    # Build DataFrame (mirror data_loader schema)
    platform_name = "Mastodon" if platform == "mastodon" else "BlueSky"
    author_field = "author_acct" if platform == "mastodon" else "author_handle"
    
    rows = []
    for item in all_items:
        rows.append({
            "id":                 item.get("id"),
            "platform":           platform_name,
            "city":               item.get("city"),
            "date":               item.get("date"),
            "created_at":         item.get("created_at"),
            "sentiment_compound": item.get("sentiment_compound"),
            "sentiment_label":    item.get("sentiment_label"),
            "sentiment_pos":      item.get("sentiment_pos"),
            "sentiment_neg":      item.get("sentiment_neg"),
            "sentiment_neu":      item.get("sentiment_neu"),
            "author":             item.get(author_field),
            "content_clean":      item.get("content_clean"),
            "harvest_strategy":   item.get("harvest_strategy"),
        })
    
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    
    # ---- Client-side filters (since API doesn't expose them) ----
    
    if cities_only:
        df = df[df["city"].isin(CITIES)].reset_index(drop=True)
    
    if platform == "bluesky" and clean_bluesky:
        # Mirror data_loader filter: exclude weather-keyword search strategies
        mask = (df["harvest_strategy"].str.contains("weather", case=False, na=False) |
                df["harvest_strategy"].isin(WEATHER_BIAS_STRATEGIES))
        df = df[~mask].reset_index(drop=True)
    
    if exclude_bots:
        # Drop most-active accounts (simple heuristic, since API doesn't tag bots)
        BOT_PATTERNS = ["newsbeep", "dlvr", "byteseu", "toptags", "rankednews"]
        for pat in BOT_PATTERNS:
            df = df[~df["author"].str.contains(pat, case=False, na=False)]
        df = df.reset_index(drop=True)
    
    return df


# ============================================================
# Public API: load_weather
# ============================================================

def load_weather(cities_only: bool = True, batch_size: int = 500) -> pd.DataFrame:
    """Load weather via HTTP API."""

    batch_size = min(batch_size, 500)
    
    session = get_session()
    
    all_items = []
    offset = 0
    total = None
    
    while True:
        params = {"limit": batch_size, "offset": offset}
        r = session.get(f"{API_BASE}/weather", params=params, timeout=API_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        
        items = data.get("items", [])
        if not items:
            break
        
        if total is None:
            total = data.get("total", 0)
            print(f"  Fetching {total:,} weather records via API...")
        
        all_items.extend(items)
        offset += len(items)
        
        if offset >= total or len(items) < batch_size:
            break
    
    df = pd.DataFrame(all_items)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    
    if cities_only and not df.empty:
        df = df[df["city"].isin(CITIES)].reset_index(drop=True)
    
    return df.sort_values(["city", "date"]).reset_index(drop=True) if not df.empty else df


# ============================================================
# Public API: derived aggregations (same as data_loader)
# ============================================================

def daily_sentiment(posts_df: pd.DataFrame,
                    min_posts: int = 3,
                    by_platform: bool = True,
                    by_city: bool = False) -> pd.DataFrame:
    """Aggregate posts to daily mean sentiment. Pure pandas, identical to data_loader."""
    df = posts_df.copy()
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
    ).reset_index().rename(columns={"day": "date"})
    
    return agg[agg["n_posts"] >= min_posts].reset_index(drop=True)


def join_posts_weather(daily_sent: pd.DataFrame,
                       weather_df: pd.DataFrame,
                       by_city: bool = False) -> pd.DataFrame:
    """Join daily sentiment with daily weather. Pure pandas."""
    weather = weather_df.copy()
    weather["date"] = pd.to_datetime(weather["date"]).dt.normalize()
    
    if by_city:
        return daily_sent.merge(weather, on=["date", "city"], how="inner")
    
    numeric_cols = weather.select_dtypes(include="number").columns.tolist()
    weather_avg = weather.groupby("date")[numeric_cols].mean().reset_index()
    return daily_sent.merge(weather_avg, on="date", how="inner")


# ============================================================
# Public API: utilities
# ============================================================

def get_overview() -> Dict[str, int]:
    """Hit /api/summary."""
    session = get_session()
    r = session.get(f"{API_BASE}/summary", timeout=15)
    r.raise_for_status()
    data = r.json()
    
    return {
        "mastodon_total":  data["by_source"]["mastodon"]["count"],
        "bluesky_total":   data["by_source"]["bluesky"]["count"],
        "bluesky_clean":   None,  # API doesn't expose; would need client-side count
        "weather_total":   data["by_source"]["weather"]["count"],
    }


def find_field(df: pd.DataFrame, *keywords: str) -> Optional[str]:
    """Find a column matching all keywords (case-insensitive)."""
    for c in df.columns:
        cl = c.lower()
        if all(k.lower() in cl for k in keywords):
            return c
    return None


# ============================================================
# Smoke test
# ============================================================

if __name__ == "__main__":
    print("Running smoke test for api_client...\n")
    
    overview = get_overview()
    for k, v in overview.items():
        print(f"  {k:18s}  {v if v else 'N/A'}")
    print()
    
    print("Loading samples...")
    m = load_posts("mastodon", cities_only=True)
    print(f"  Mastodon (4 cities): {len(m):,}")
    b = load_posts("bluesky", cities_only=True)
    print(f"  BlueSky  (4 cities): {len(b):,}")
    w = load_weather()
    print(f"  Weather: {len(w):,}")
    
    print("\nSample aggregation:")
    posts = pd.concat([m, b], ignore_index=True)
    daily = daily_sentiment(posts, min_posts=3, by_platform=True)
    print(daily.head(5))
    print(f"\nTotal daily cells: {len(daily)}")