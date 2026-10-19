"""Mastodon post -> ES posts_mastodon document."""

import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from shared.cities import CITY_NAMES, infer_city
from shared.keywords import WEATHER_KEYWORDS, BEVERAGE_KEYWORDS, extract_keywords
from shared.sentiment import score as vader_score


def strip_html(html):
    """Strip HTML tags, return clean plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)


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


def transform(post, harvest_strategy=None):
    """Transform raw Mastodon post -> posts_mastodon ES document.

    Args:
        post: dict from Mastodon API response
        harvest_strategy: 'local' / 'tag:auspol' / 'tag:melbourne' etc

    Returns: dict matching posts_mastodon mapping, or None if post is a reblog.
    """
    # Skip reblogs (boosts) — they duplicate the original post's content
    if post.get("reblog"):
        return None

    html = post.get("content", "")
    clean = strip_html(html)

    acct = post.get("account", {}) or {}
    acct_str = acct.get("acct", "")
    server = acct_str.split("@")[1] if "@" in acct_str else "mastodon.au"

    tags = [t.get("name", "").lower() for t in (post.get("tags") or [])]
    mentions = [m.get("acct", "") for m in (post.get("mentions") or [])]

    # City inference: hashtag first, then content
    city, city_src = None, None
    for tag in tags:
        for cn in CITY_NAMES:
            if cn.lower() == tag:
                city, city_src = cn, "hashtag"
                break
        if city:
            break
    if not city:
        city, city_src = infer_city(clean)

    created_iso = to_iso_z(post.get("created_at"))
    date_str = created_iso[:10] if created_iso else None

    sent = vader_score(clean)
    weather_kw = extract_keywords(clean, WEATHER_KEYWORDS)
    beverage_kw = extract_keywords(clean, BEVERAGE_KEYWORDS)

    favs = int(post.get("favourites_count") or 0)
    reblogs = int(post.get("reblogs_count") or 0)
    replies = int(post.get("replies_count") or 0)
    engagement = favs + reblogs + replies

    return {
        "id":              f"mastodon_{post['id']}",
        "platform":        "mastodon",
        "source_server":   server,

        "author_id":       str(acct.get("id", "")),
        "author_acct":     acct_str,
        "author_display_name": acct.get("display_name", ""),
        "author_is_bot":   bool(acct.get("bot", False)),
        "author_followers_count": int(acct.get("followers_count", 0)),

        "content_html":    html,
        "content_clean":   clean,
        "content_length":  len(clean),

        "language":        post.get("language"),
        "tags":            tags,
        "mentions":        mentions,
        "url":             post.get("url"),

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

        "favourites_count":   favs,
        "reblogs_count":      reblogs,
        "replies_count":      replies,
        "engagement_score":   engagement,

        "raw_payload":        post,
    }
