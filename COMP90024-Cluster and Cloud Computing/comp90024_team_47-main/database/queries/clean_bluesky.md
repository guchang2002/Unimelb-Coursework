# Clean BlueSky Data Query

## Why filter

BlueSky historical data was collected via 3 strategies (recorded in `harvest_strategy` field):

| Strategy | Posts | Status |
|---|---|---|
| `feed:*` (trusted AU accounts: Guardian, Crikey, Snurb, etc) | 1149 | ✅ Clean |
| `search:<city>` (Melbourne / Sydney / Brisbane / Perth) | 376 | ✅ Clean baseline |
| `search:*weather*` / `search:heatwave` / `search:polar blast` / `search:auswx` | 824 | ⚠️ Biased toward weather mentions |

The weather-keyword searches **inflate** weather discussion frequency:
when comparing platform sentiment toward weather events (RQ2) or computing
city-level baselines (RQ1), these biased posts skew the result.

Streaming SEARCH_QUERIES (post 5/9) no longer include weather keywords —
this filter only applies to historical data.

## Use this filter for RQ1 / RQ2

ES query template:

```json
GET posts_bluesky/_search
{
  "query": {
    "bool": {
      "must": [
        { "term": { "city": "Melbourne" } }
      ],
      "must_not": [
        { "wildcard": { "harvest_strategy": "*weather*" } },
        { "term":     { "harvest_strategy": "search:heatwave" } },
        { "term":     { "harvest_strategy": "search:polar blast" } },
        { "term":     { "harvest_strategy": "search:auswx" } }
      ]
    }
  }
}
```

Python equivalent (for Jupyter):

```python
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
```

## Available "clean" data

After applying the filter:
- Total: ~2025 posts (out of 2849 historical, plus ongoing streaming)
- By city: Melbourne ~150, Sydney ~140, Brisbane ~110, Perth ~110, unknown ~1500

## When NOT to apply this filter

- **RQ3 user demographics**: filter is about content bias, not author bias.
  Use full data.
- **Reporting collection methodology**: report results both with and without
  filter for transparency.

## Mastodon does not have this issue

Mastodon historical was collected via local timeline + AU hashtags
(`auspol`, `auswx`, `melbourne`, `sydney`, `brisbane`, `perth`, `australia`).
No weather-keyword searches were used. No filter needed.
