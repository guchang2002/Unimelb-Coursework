"""Fission function: mastodon_streaming
Triggered every ~10 minutes by cron, fetches latest posts from
mastodon.au (local timeline + AU hashtags), writes to posts_mastodon.

Idempotent: re-runs overwrite by deterministic _id (mastodon_<id>).
ES bulk_index acts as natural deduplication via _id collisions.
"""

import os
import sys
from datetime import datetime, timezone

# Make ./shared importable (bundled into zip)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from shared.transforms.mastodon import transform as transform_mastodon
from shared.es_client import bulk_index, count
from shared.cities import CITIES  # not used directly but imported to validate shared


# =================== Config ===================

# Read MASTODON_TOKEN from Fission-mounted secret file
def _read_secret(name, key):
    path = f"/secrets/default/{name}/{key}"
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return os.environ.get(key)  # fallback for local testing


MASTODON_TOKEN = _read_secret("mastodon-creds", "MASTODON_TOKEN")
MASTODON_BASE  = "https://mastodon.au"

# Per-strategy fetch caps (small, since we run every 10 min)
LOCAL_PAGES = 3   # 3 pages × 40 = 120 newest local posts
TAG_PAGES   = 1   # 1 page × 40 per hashtag (less critical, run often)

HASHTAGS = ["auspol", "melbourne", "sydney", "brisbane", "perth", "australia"]

INDEX = "posts_mastodon"


# =================== Mastodon API ===================

def fetch_pages(url, params, n_pages):
    """Fetch n_pages of posts (40/page), paginated by max_id."""
    headers = {"Authorization": f"Bearer {MASTODON_TOKEN}"}
    posts = []
    max_id = None

    for page in range(n_pages):
        p = dict(params)
        p["limit"] = 40
        if max_id:
            p["max_id"] = max_id

        try:
            r = requests.get(url, headers=headers, params=p, timeout=15)
            if r.status_code != 200:
                break
            batch = r.json()
            if not batch:
                break
            posts.extend(batch)
            max_id = batch[-1]["id"]
        except Exception:
            break

    return posts


# =================== Main ===================

def main():
    """Fission entry point. Returns dict serialized as JSON."""
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if not MASTODON_TOKEN:
        return {
            "error": "MASTODON_TOKEN not available",
            "started_at": started_at,
        }

    # Phase 1: collect raw posts
    raw_by_id = {}  # id -> (post, strategy)

    # 1a. Local timeline
    for post in fetch_pages(
        f"{MASTODON_BASE}/api/v1/timelines/public",
        params={"local": "true"},
        n_pages=LOCAL_PAGES,
    ):
        if post["id"] not in raw_by_id:
            raw_by_id[post["id"]] = (post, "local")

    # 1b. Hashtags
    for tag in HASHTAGS:
        for post in fetch_pages(
            f"{MASTODON_BASE}/api/v1/timelines/tag/{tag}",
            params={},
            n_pages=TAG_PAGES,
        ):
            if post["id"] not in raw_by_id:
                raw_by_id[post["id"]] = (post, f"tag:{tag}")

    fetched_count = len(raw_by_id)

    # Phase 2: transform
    docs = []
    skipped_reblogs = 0
    transform_failed = 0

    for post, strategy in raw_by_id.values():
        try:
            doc = transform_mastodon(post, harvest_strategy=strategy)
            if doc is None:
                skipped_reblogs += 1
                continue
            docs.append(doc)
        except Exception:
            transform_failed += 1

    # Phase 3: bulk index (ES dedupes by _id)
    indexed = 0
    failed = 0
    if docs:
        try:
            indexed, failed = bulk_index(INDEX, docs)
        except Exception as e:
            return {
                "error": f"bulk_index failed: {str(e)[:300]}",
                "fetched": fetched_count,
                "transformed": len(docs),
                "started_at": started_at,
            }

    return {
        "fetched":          fetched_count,
        "transformed":      len(docs),
        "skipped_reblogs":  skipped_reblogs,
        "transform_failed": transform_failed,
        "indexed":          indexed,
        "failed":           failed,
        "posts_mastodon_count": count(INDEX),
        "started_at":       started_at,
        "finished_at":      datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
