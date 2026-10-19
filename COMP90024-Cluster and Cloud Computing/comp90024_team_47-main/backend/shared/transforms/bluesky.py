"""BlueSky post -> ES posts_bluesky document."""

import re
from datetime import datetime, timezone

from shared.cities import CITY_NAMES, infer_city
from shared.keywords import WEATHER_KEYWORDS, BEVERAGE_KEYWORDS, extract_keywords
from shared.sentiment import score as vader_score


# Known bot handles (from sample analysis)
BOT_HANDLES = {
    "emv-alerts.sushifeed.org",
    "theage.nzcow.com",
    "smhaustralia.nzcow.com",
    "world-info.bsky.social",
    "epsteinweb.bsky.social",
    "rankednews.bsky.social",
    "mlb.nws-bot.us",
}


def is_bot(handle):
    """Identify bots: handle blacklist + .nzcow.com domain heuristic."""
    if not handle:
        return False
    if handle in BOT_HANDLES:
        return True
    if handle.endswith(".nzcow.com"):
        return True
    return False


def to_iso_z(dt_str):
    """Normalize timestamps to ISO 8601 with trailing Z (UTC)."""
    if not dt_str:
        return None
    if isinstance(dt_str, str) and dt_str.endswith("Z"):
        return dt_str
    try:
        dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return str(dt_str)


def uri_to_web_url(uri):
    """at:// URI -> https://bsky.app/... web URL."""
    if not uri or not uri.startswith("at://"):
        return None
    m = re.match(r"at://([^/]+)/app\.bsky\.feed\.post/(.+)", uri)
    if m:
        return f"https://bsky.app/profile/{m.group(1)}/post/{m.group(2)}"
    return None


def transform(post, harvest_strategy=None):
    """Transform raw BlueSky post -> posts_bluesky ES document.

    Args:
        post: dict from atproto SDK (model_dump())
        harvest_strategy: 'search:Melbourne weather' / 'feed:guardian' etc

    Returns: dict matching posts_bluesky mapping.
    """
    record = post.get("record") or {}
    author = post.get("author") or {}

    clean = record.get("text", "") if isinstance(record, dict) else ""
    handle = author.get("handle", "")

    # Tags + mentions from facets
    tags = []
    mentions = []
    facets = record.get("facets") or [] if isinstance(record, dict) else []
    for f in facets:
        for feat in (f.get("features") or []):
            ftype = feat.get("py_type", "")
            if "facet#tag" in ftype:
                tags.append((feat.get("tag") or "").lower())
            elif "facet#mention" in ftype:
                mentions.append(feat.get("did") or "")

    # City inference: search query first, then hashtag, then content
    city, city_src = None, None
    if harvest_strategy and harvest_strategy.startswith("search:"):
        for cn in CITY_NAMES:
            if cn in harvest_strategy:
                city, city_src = cn, "search_query"
                break
    if not city:
        for tag in tags:
            for cn in CITY_NAMES:
                if cn.lower() == tag:
                    city, city_src = cn, "hashtag"
                    break
            if city:
                break
    if not city:
        city, city_src = infer_city(clean)

    created_iso = to_iso_z(record.get("created_at") if isinstance(record, dict) else None)
    date_str = created_iso[:10] if created_iso else None

    sent = vader_score(clean)
    weather_kw = extract_keywords(clean, WEATHER_KEYWORDS)
    beverage_kw = extract_keywords(clean, BEVERAGE_KEYWORDS)

    likes = int(post.get("like_count") or 0)
    reposts = int(post.get("repost_count") or 0)
    replies = int(post.get("reply_count") or 0)
    engagement = likes + reposts + replies

    langs = record.get("langs") if isinstance(record, dict) else None
    if isinstance(langs, list) and langs:
        language = langs[0]
    elif isinstance(langs, str):
        language = langs
    else:
        language = None

    uri = post.get("uri", "")
    cid = post.get("cid", "")

    return {
        "id":              f"bluesky_{cid or uri.split('/')[-1]}",
        "platform":        "bluesky",
        "uri":             uri,
        "cid":             cid,

        "author_did":      author.get("did", ""),
        "author_handle":   handle,
        "author_display_name": author.get("display_name", ""),
        "author_is_bot":   is_bot(handle),

        "content_clean":   clean,
        "content_length":  len(clean),

        "language":        language,
        "tags":            tags,
        "mentions":        mentions,
        "url":             uri_to_web_url(uri),

        "city":            city,
        "city_inferred_from": city_src,

        "created_at":      created_iso,
        "date":            date_str,
        "harvested_at":    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "harvest_strategy": harvest_strategy,

        "sentiment_compound": sent["compound"] if sent else None,
        "sentiment_pos":      sent["pos"]      if sent else None,
        "sentiment_neg":      sent["neg"]      if sent else None,
        "sentiment_neu":      sent["neu"]      if sent else None,
        "sentiment_label":    sent["label"]    if sent else None,

        "weather_keywords":   weather_kw,
        "beverage_keywords":  beverage_kw,

        "like_count":         likes,
        "repost_count":       reposts,
        "reply_count":        replies,
        "engagement_score":   engagement,

        "raw_payload":        post,
    }
