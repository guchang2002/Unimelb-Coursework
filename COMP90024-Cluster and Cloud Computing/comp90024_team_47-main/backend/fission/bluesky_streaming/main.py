"""Fission function: bluesky_streaming
Triggered every 2 hours by cron.
Fetches latest posts from BlueSky via HTTP API (no atproto SDK).

JWT REFRESH CACHING:
  - Stores refreshJwt in K8s ConfigMap "bluesky-jwt"
  - Each cron call: read refreshJwt -> refreshSession (NOT rate-limited!)
  - createSession only called when refreshJwt is missing/expired
  - Avoids BlueSky's createSession rate limit (~30/day/IP)

SEARCH STRATEGY (clean, no weather-keyword bias):
  - Trusted AU accounts (deep)
  - 4 city searches: Melbourne/Sydney/Brisbane/Perth (no "weather" suffix)
  - Generic AU topics: "Australia", "auspol"

Idempotent: re-runs overwrite by deterministic _id (bluesky_<cid>).
"""

import os
import sys
from datetime import datetime, timezone

# Make ./shared importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from kubernetes import client, config

from shared.transforms.bluesky import transform as transform_bluesky
from shared.es_client import bulk_index, count


# =================== Config ===================

def _read_secret(name, key):
    """Read a Fission-mounted secret value, fallback to env var."""
    path = f"/secrets/default/{name}/{key}"
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return os.environ.get(key)


BSKY_HANDLE       = _read_secret("bluesky-creds", "BSKY_HANDLE")
BSKY_APP_PASSWORD = _read_secret("bluesky-creds", "BSKY_APP_PASSWORD")

BSKY_API = "https://bsky.social/xrpc"

# Trusted AU accounts (deep)
TRUSTED_AU_ACCOUNTS = [
    "australia.theguardian.com",
    "crikey.com.au",
    "adammorton.bsky.social",
    "snurb.info",
]
ACCOUNT_LIMIT = 50

# Clean queries (no weather bias — see database/queries/clean_bluesky.md)
SEARCH_QUERIES = [
    "Melbourne",
    "Sydney",
    "Brisbane",
    "Perth",
    "Australia",
    "auspol",
]
SEARCH_LIMIT = 50

INDEX = "posts_bluesky"

# JWT cache: K8s ConfigMap
JWT_CONFIGMAP_NAME = "bluesky-jwt"
JWT_NAMESPACE      = "default"


# =================== K8s ConfigMap helpers (JWT cache) ===================

def _k8s_v1():
    """Initialize K8s client in-cluster (uses fission-fetcher ServiceAccount)."""
    config.load_incluster_config()
    return client.CoreV1Api()


def get_cached_refresh_jwt():
    """Read refreshJwt from ConfigMap. Return None if missing/empty."""
    try:
        v1 = _k8s_v1()
        cm = v1.read_namespaced_config_map(JWT_CONFIGMAP_NAME, JWT_NAMESPACE)
        rjwt = (cm.data or {}).get("refreshJwt", "").strip()
        return rjwt if rjwt else None
    except Exception:
        return None


def save_refresh_jwt(refresh_jwt):
    """Write refreshJwt to ConfigMap. Idempotent (create or replace)."""
    try:
        v1 = _k8s_v1()
        body = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name=JWT_CONFIGMAP_NAME),
            data={"refreshJwt": refresh_jwt},
        )
        try:
            v1.replace_namespaced_config_map(JWT_CONFIGMAP_NAME, JWT_NAMESPACE, body)
        except client.exceptions.ApiException as e:
            if e.status == 404:
                v1.create_namespaced_config_map(JWT_NAMESPACE, body)
            else:
                raise
        return True
    except Exception as e:
        print(f"WARNING: save_refresh_jwt failed: {e}")
        return False


# =================== BlueSky HTTP API ===================

def create_new_session():
    """Full createSession: returns (accessJwt, refreshJwt). Counted toward rate limit."""
    r = requests.post(
        f"{BSKY_API}/com.atproto.server.createSession",
        json={"identifier": BSKY_HANDLE, "password": BSKY_APP_PASSWORD},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return data["accessJwt"], data["refreshJwt"]


def refresh_session(refresh_jwt):
    """Refresh session: returns (accessJwt, refreshJwt). NOT rate-limited."""
    r = requests.post(
        f"{BSKY_API}/com.atproto.server.refreshSession",
        headers={"Authorization": f"Bearer {refresh_jwt}"},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return data["accessJwt"], data["refreshJwt"]


def get_session():
    """Get a working accessJwt. Tries refresh first, falls back to createSession.

    Returns: (accessJwt, used_create_session: bool)
    """
    cached_refresh = get_cached_refresh_jwt()

    if cached_refresh:
        try:
            access_jwt, new_refresh = refresh_session(cached_refresh)
            save_refresh_jwt(new_refresh)
            return access_jwt, False
        except Exception as e:
            print(f"INFO: refresh_session failed ({e}), falling back to createSession")

    # No cached or refresh failed -> createSession (rate limited!)
    access_jwt, refresh_jwt = create_new_session()
    save_refresh_jwt(refresh_jwt)
    return access_jwt, True


def get_author_feed(jwt, actor, limit=50):
    headers = {"Authorization": f"Bearer {jwt}"}
    r = requests.get(
        f"{BSKY_API}/app.bsky.feed.getAuthorFeed",
        headers=headers,
        params={"actor": actor, "limit": limit},
        timeout=20,
    )
    if r.status_code != 200:
        return []
    feed = r.json().get("feed", [])
    return [item["post"] for item in feed if "post" in item]


def search_posts(jwt, query, limit=50):
    headers = {"Authorization": f"Bearer {jwt}"}
    r = requests.get(
        f"{BSKY_API}/app.bsky.feed.searchPosts",
        headers=headers,
        params={"q": query, "limit": limit},
        timeout=20,
    )
    if r.status_code != 200:
        return []
    return r.json().get("posts", [])


# =================== Field name adapter ===================

def _normalize_post(post):
    """BlueSky HTTP API returns camelCase, transform expects snake_case."""
    if not isinstance(post, dict):
        return post

    p = dict(post)

    if "likeCount" in p:
        p["like_count"] = p["likeCount"]
    if "repostCount" in p:
        p["repost_count"] = p["repostCount"]
    if "replyCount" in p:
        p["reply_count"] = p["replyCount"]

    if "author" in p and isinstance(p["author"], dict):
        a = dict(p["author"])
        if "displayName" in a:
            a["display_name"] = a["displayName"]
        p["author"] = a

    if "record" in p and isinstance(p["record"], dict):
        r = dict(p["record"])
        if "createdAt" in r:
            r["created_at"] = r["createdAt"]
        if "facets" in r and isinstance(r["facets"], list):
            new_facets = []
            for f in r["facets"]:
                if not isinstance(f, dict):
                    new_facets.append(f)
                    continue
                f2 = dict(f)
                if "features" in f2 and isinstance(f2["features"], list):
                    new_features = []
                    for feat in f2["features"]:
                        if isinstance(feat, dict) and "$type" in feat:
                            feat = dict(feat)
                            feat["py_type"] = feat["$type"]
                        new_features.append(feat)
                    f2["features"] = new_features
                new_facets.append(f2)
            r["facets"] = new_facets
        p["record"] = r

    return p


# =================== Main ===================

def main():
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if not BSKY_HANDLE or not BSKY_APP_PASSWORD:
        return {
            "error": "BlueSky credentials not available",
            "started_at": started_at,
        }

    # Phase 0: get session (try refresh first, fall back to create)
    try:
        jwt, used_create = get_session()
    except Exception as e:
        return {
            "error": f"session failed: {str(e)[:200]}",
            "started_at": started_at,
        }

    # Phase 1: collect (dedupe by uri)
    raw_by_uri = {}

    for handle in TRUSTED_AU_ACCOUNTS:
        try:
            for post in get_author_feed(jwt, handle, limit=ACCOUNT_LIMIT):
                uri = post.get("uri")
                if uri and uri not in raw_by_uri:
                    raw_by_uri[uri] = (post, f"feed:{handle}")
        except Exception:
            pass

    for query in SEARCH_QUERIES:
        try:
            for post in search_posts(jwt, query, limit=SEARCH_LIMIT):
                uri = post.get("uri")
                if uri and uri not in raw_by_uri:
                    raw_by_uri[uri] = (post, f"search:{query}")
        except Exception:
            pass

    fetched_count = len(raw_by_uri)

    # Phase 2: normalize + transform
    docs = []
    transform_failed = 0

    for post, strategy in raw_by_uri.values():
        try:
            normalized = _normalize_post(post)
            doc = transform_bluesky(normalized, harvest_strategy=strategy)
            if doc is None:
                continue
            docs.append(doc)
        except Exception:
            transform_failed += 1

    # Phase 3: bulk index
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
        "fetched":             fetched_count,
        "transformed":         len(docs),
        "transform_failed":    transform_failed,
        "indexed":             indexed,
        "failed":              failed,
        "posts_bluesky_count": count(INDEX),
        "session_type":        "createSession" if used_create else "refreshSession",
        "started_at":          started_at,
        "finished_at":         datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
