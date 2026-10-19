"""Elasticsearch helpers — bulk index + count check.

Reads config from environment variables OR Fission-mounted files.
- Local (historical harvester): uses os.environ (loaded from .env)
- Fission function: uses files mounted by ConfigMap/Secret
"""

import json
import os
from pathlib import Path
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _read_config_value(env_name, configmap_name=None, secret_name=None, default=None):
    """Read a config value, trying in order:
    1. Environment variable (works locally with .env)
    2. ConfigMap-mounted file (Fission)
    3. Secret-mounted file (Fission)
    4. Default
    """
    # 1. Environment variable
    val = os.environ.get(env_name)
    if val:
        return val

    # 2. ConfigMap mounted file (Fission default mount path)
    if configmap_name:
        path = Path(f"/configs/default/{configmap_name}/{env_name}")
        if path.exists():
            return path.read_text().strip()

    # 3. Secret mounted file
    if secret_name:
        path = Path(f"/secrets/default/{secret_name}/{env_name}")
        if path.exists():
            return path.read_text().strip()

    return default


def _es_config():
    """Read ES config from env vars or Fission-mounted ConfigMap/Secret files."""
    return {
        "url": _read_config_value(
            "ES_URL",
            configmap_name="fission-es-config",
            default="https://localhost:9200",
        ),
        "auth": (
            _read_config_value(
                "ES_USER",
                secret_name="es-creds",
                default="elastic",
            ),
            _read_config_value(
                "ES_PASSWORD",
                secret_name="es-creds",
                default="elastic",
            ),
        ),
    }


def bulk_index(index_name, docs, id_field="id"):
    """Bulk-index a list of docs. Idempotent (overwrites by _id).

    Returns (indexed_count, failed_count).
    """
    if not docs:
        return (0, 0)

    cfg = _es_config()

    lines = []
    for doc in docs:
        lines.append(json.dumps({"index": {"_index": index_name, "_id": doc[id_field]}}))
        lines.append(json.dumps(doc, default=str))
    body = "\n".join(lines) + "\n"

    r = requests.post(
        f"{cfg['url']}/_bulk",
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/x-ndjson"},
        auth=cfg["auth"],
        verify=False,
        timeout=120,
    )
    r.raise_for_status()
    result = r.json()

    indexed = sum(1 for it in result["items"] if "error" not in it.get("index", {}))
    failed  = len(result["items"]) - indexed

    if failed:
        for it in result["items"]:
            err = it.get("index", {}).get("error")
            if err:
                print(f"  ❌ Sample bulk error: {json.dumps(err, indent=2)[:400]}")
                break

    return (indexed, failed)


def count(index_name):
    """Return document count for an index."""
    cfg = _es_config()
    r = requests.get(
        f"{cfg['url']}/{index_name}/_count",
        auth=cfg["auth"],
        verify=False,
    )
    r.raise_for_status()
    return r.json()["count"]
