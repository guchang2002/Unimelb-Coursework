#!/usr/bin/env python
"""
COMP90024 Team 47 — BlueSky historical backfill (one-shot)

Strategies:
  1. Author feeds of trusted Australian accounts (deep history)
  2. Keyword searches (broad but shallow)

Bot posts are kept (with author_is_bot=true) — analysis filters at query time.

Idempotent: re-runs overwrite by _id (bluesky_<cid>).

Usage:
    cd ~/Desktop/COMP90024_team_47
    python database/load_bluesky_history.py
"""

import os
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Make backend/shared importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

# Load .env
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from atproto import Client

from shared.transforms.bluesky import transform as transform_bluesky
from shared.es_client import bulk_index, count

# =================== Config ===================

BSKY_HANDLE       = os.environ.get("BSKY_HANDLE")
BSKY_APP_PASSWORD = os.environ.get("BSKY_APP_PASSWORD")

HISTORY_DAYS  = int(os.environ.get("HISTORY_DAYS", "90"))
EARLIEST_DATE = datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)

# Trusted Australian accounts to deep-pull
TRUSTED_AU_ACCOUNTS = [
    "australia.theguardian.com",      # Guardian Australia
    "crikey.com.au",                   # Crikey
    "adammorton.bsky.social",          # Adam Morton (Guardian)
    "mikeyslezak.bsky.social",         # Michael Slezak (ABC)
    "snurb.info",                      # Axel Bruns (academic)
]

# Per-account fetch cap
ACCOUNT_CAP = 500

# Keyword search queries (city + weather + topic)
SEARCH_QUERIES = [
    "Melbourne weather",
    "Sydney weather",
    "Brisbane weather",
    "Perth weather",
    "Melbourne",
    "Sydney",
    "Brisbane",
    "Perth",
    "auswx",
    "polar blast",
    "australia weather",
    "heatwave",
]

# Per-search cap (BlueSky search returns max 100/page)
SEARCH_CAP = 100

# Bulk write batch size
BULK_BATCH = 500

INDEX = "posts_bluesky"


# =================== Fetch helpers ===================

def fetch_author_feed(client, handle, cap):
    """Paginated get_author_feed."""
    print(f"\n📰 @{handle} (cap {cap})")
    posts = []
    cursor = None
    earliest_seen = None

    while len(posts) < cap:
        try:
            params = {"actor": handle, "limit": min(100, cap - len(posts))}
            if cursor:
                params["cursor"] = cursor
            resp = client.get_author_feed(**params)
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
            break

        if not resp.feed:
            break

        for item in resp.feed:
            posts.append(item.post)

        cursor = resp.cursor
        if not cursor:
            break

        # Time wall check
        if posts:
            last_dt_str = posts[-1].record.created_at if hasattr(posts[-1].record, 'created_at') else None
            if last_dt_str:
                try:
                    last_dt = datetime.fromisoformat(str(last_dt_str).replace("Z", "+00:00"))
                    earliest_seen = last_dt
                    if last_dt < EARLIEST_DATE:
                        print(f"    ✓ Reached time wall ({last_dt.date()}), stopping")
                        return posts
                except Exception:
                    pass

        if len(posts) % 100 == 0:
            print(f"    ... {len(posts)} posts (earliest: {earliest_seen.date() if earliest_seen else '?'})")

        time.sleep(0.3)

    print(f"    Got {len(posts)} posts")
    return posts


def fetch_search(client, query, cap):
    """Paginated search_posts."""
    print(f"\n🔎 search '{query}' (cap {cap})")
    posts = []
    cursor = None

    while len(posts) < cap:
        try:
            params = {"q": query, "limit": min(100, cap - len(posts))}
            if cursor:
                params["cursor"] = cursor
            resp = client.app.bsky.feed.search_posts(params=params)
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
            break

        if not resp.posts:
            break

        posts.extend(resp.posts)
        cursor = resp.cursor
        if not cursor:
            break
        time.sleep(0.3)

    print(f"    Got {len(posts)} posts")
    return posts


def post_to_dict(post, strategy):
    """Convert atproto post object to dict, attach strategy metadata."""
    d = post.model_dump()
    d["_source_strategy"] = strategy
    return d


# =================== Pipeline ===================

def run():
    if not BSKY_HANDLE or not BSKY_APP_PASSWORD:
        print("❌ BSKY_HANDLE or BSKY_APP_PASSWORD not set in .env")
        sys.exit(1)

    print(f"=== BlueSky historical backfill ===")
    print(f"  History window: past {HISTORY_DAYS} days (since {EARLIEST_DATE.date()})")
    print(f"  Index target:   {INDEX}")

    # Login
    client = Client()
    client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)
    print(f"  Logged in as @{client.me.handle}")

    # Phase 1: collect raw posts (deduplicate by uri)
    raw_by_uri = {}  # uri -> (post_dict, strategy)

    # 1a. Trusted accounts deep pull
    for handle in TRUSTED_AU_ACCOUNTS:
        for post in fetch_author_feed(client, handle, ACCOUNT_CAP):
            if post.uri not in raw_by_uri:
                raw_by_uri[post.uri] = (post_to_dict(post, f"feed:{handle}"), f"feed:{handle}")

    # 1b. Keyword searches
    for query in SEARCH_QUERIES:
        for post in fetch_search(client, query, SEARCH_CAP):
            if post.uri not in raw_by_uri:
                raw_by_uri[post.uri] = (post_to_dict(post, f"search:{query}"), f"search:{query}")

    print(f"\n=== Collection summary ===")
    print(f"  Total unique posts: {len(raw_by_uri)}")
    
    strats = Counter(s for _, s in raw_by_uri.values())
    print("  Top 10 strategies:")
    for s, c in strats.most_common(10):
        print(f"    {c:5d}  {s}")

    # Phase 2: filter by time wall
    keep = []
    too_old = 0
    for d, strategy in raw_by_uri.values():
        try:
            record = d.get("record") or {}
            dt_str = record.get("created_at") if isinstance(record, dict) else None
            if dt_str:
                dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
                if dt < EARLIEST_DATE - timedelta(days=10):
                    too_old += 1
                    continue
        except Exception:
            pass
        keep.append((d, strategy))

    print(f"\n  Filtered (too old):  {too_old}")
    print(f"  Within window:       {len(keep)}")

    # Phase 3: transform + bulk index
    print(f"\n=== Transform + index ===")
    total_indexed = 0
    total_failed  = 0
    transform_failed = 0

    for i in range(0, len(keep), BULK_BATCH):
        batch = keep[i:i + BULK_BATCH]
        docs = []
        for d, strategy in batch:
            try:
                doc = transform_bluesky(d, harvest_strategy=strategy)
                if doc is None:
                    continue
                docs.append(doc)
            except Exception as e:
                transform_failed += 1
                if transform_failed <= 3:
                    print(f"    ⚠️  Transform failed: {e}")

        indexed, failed = bulk_index(INDEX, docs)
        total_indexed += indexed
        total_failed  += failed
        print(f"  Batch {i // BULK_BATCH + 1}: indexed {indexed} / failed {failed}")

    print(f"\n=== Done ===")
    print(f"  Total indexed:    {total_indexed}")
    print(f"  Total failed:     {total_failed}")
    print(f"  Transform failed: {transform_failed}")
    print(f"  ES {INDEX} count: {count(INDEX)}")


if __name__ == "__main__":
    run()
