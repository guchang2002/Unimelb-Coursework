#!/usr/bin/env python
"""
COMP90024 Team 47 — Mastodon historical backfill (one-shot)

Fetches up to 90 days of posts from mastodon.au using:
  - local timeline (real Australian users)
  - hashtag timelines (#auspol, #auswx, #melbourne, etc)

Each post is transformed via shared/transforms/mastodon.py and bulk-indexed
into ES `posts_mastodon`. Reblogs are skipped (they'd duplicate originals).

Idempotent: re-runs overwrite by _id (mastodon_<id>).

Usage:
    # Make sure port-forward to ES is running:
    #   kubectl port-forward service/elasticsearch-es-http -n elastic 9200:9200
    
    cd ~/Desktop/COMP90024_team_47
    python database/load_mastodon_history.py
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

# Load .env from repo root
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from shared.transforms.mastodon import transform as transform_mastodon
from shared.es_client import bulk_index, count

# =================== Config ===================

MASTODON_TOKEN = os.environ.get("MASTODON_TOKEN")
MASTODON_BASE  = "https://mastodon.au"

HISTORY_DAYS   = int(os.environ.get("HISTORY_DAYS", "90"))
EARLIEST_DATE  = datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)

HASHTAGS = ["auspol", "melbourne", "sydney", "brisbane", "perth", "australia"]

LOCAL_CAP = 5000
TAG_CAP   = 1000
BULK_BATCH = 500

INDEX = "posts_mastodon"


def _get(url, params=None):
    """Mastodon GET with auth + retry on 429."""
    headers = {"Authorization": f"Bearer {MASTODON_TOKEN}"}
    for attempt in range(3):
        r = requests.get(url, headers=headers, params=params, timeout=20)
        if r.status_code == 429:
            wait = int(r.headers.get("X-RateLimit-Reset-After", "30"))
            print(f"    ⏸  Rate limited, sleeping {wait}s...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Failed after 3 retries")


def fetch_paginated(url, params, cap):
    """Paginate via max_id until time wall or cap reached."""
    all_posts = []
    max_id = None
    earliest_seen = None

    while len(all_posts) < cap:
        p = dict(params)
        p["limit"] = 40
        if max_id:
            p["max_id"] = max_id

        try:
            batch = _get(url, params=p)
        except Exception as e:
            print(f"    ⚠️  Fetch error: {e}")
            break

        if not batch:
            break

        all_posts.extend(batch)
        max_id = batch[-1]["id"]

        last_dt_str = batch[-1].get("created_at")
        if last_dt_str:
            try:
                last_dt = datetime.fromisoformat(last_dt_str.replace("Z", "+00:00"))
                earliest_seen = last_dt
                if last_dt < EARLIEST_DATE:
                    print(f"    ✓ Reached time wall ({last_dt.date()}), stopping")
                    break
            except Exception:
                pass

        if len(all_posts) % 200 == 0:
            print(f"    ... {len(all_posts)} posts (earliest: {earliest_seen.date() if earliest_seen else '?'})")

        time.sleep(0.3)

    return all_posts


def fetch_local_timeline():
    print(f"\n📍 Local timeline (mastodon.au, cap {LOCAL_CAP}, time wall {EARLIEST_DATE.date()})")
    return fetch_paginated(
        f"{MASTODON_BASE}/api/v1/timelines/public",
        params={"local": "true"},
        cap=LOCAL_CAP,
    )


def fetch_hashtag(tag):
    print(f"\n🏷️  #{tag} (cap {TAG_CAP})")
    return fetch_paginated(
        f"{MASTODON_BASE}/api/v1/timelines/tag/{tag}",
        params={},
        cap=TAG_CAP,
    )


def run():
    if not MASTODON_TOKEN:
        print("❌ MASTODON_TOKEN not set in .env")
        sys.exit(1)

    print(f"=== Mastodon historical backfill ===")
    print(f"  History window: past {HISTORY_DAYS} days (since {EARLIEST_DATE.date()})")
    print(f"  Index target:   {INDEX}")

    # Phase 1: collect raw posts
    raw_posts = {}  # id -> (post, strategy)

    for post in fetch_local_timeline():
        if post["id"] not in raw_posts:
            raw_posts[post["id"]] = (post, "local")

    for tag in HASHTAGS:
        for post in fetch_hashtag(tag):
            if post["id"] not in raw_posts:
                raw_posts[post["id"]] = (post, f"tag:{tag}")

    print(f"\n=== Collection summary ===")
    print(f"  Total unique posts: {len(raw_posts)}")
    
    strats = Counter(s for _, s in raw_posts.values())
    for s, c in strats.most_common():
        print(f"    {c:5d}  {s}")

    # Phase 2: filter older-than-window
    keep = []
    too_old = 0
    for post, strategy in raw_posts.values():
        try:
            dt = datetime.fromisoformat(post["created_at"].replace("Z", "+00:00"))
            if dt < EARLIEST_DATE - timedelta(days=10):
                too_old += 1
                continue
        except Exception:
            pass
        keep.append((post, strategy))

    print(f"\n  Filtered (too old):  {too_old}")
    print(f"  Within window:       {len(keep)}")

    # Phase 3: transform + bulk index
    print(f"\n=== Transform + index ===")
    total_indexed = 0
    total_failed  = 0
    transform_failed = 0
    skipped_reblogs  = 0

    for i in range(0, len(keep), BULK_BATCH):
        batch = keep[i:i + BULK_BATCH]
        docs = []
        for post, strategy in batch:
            try:
                doc = transform_mastodon(post, harvest_strategy=strategy)
                if doc is None:
                    skipped_reblogs += 1
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
    print(f"  Skipped reblogs:  {skipped_reblogs}")
    print(f"  Transform failed: {transform_failed}")
    print(f"  ES {INDEX} count: {count(INDEX)}")


if __name__ == "__main__":
    run()
