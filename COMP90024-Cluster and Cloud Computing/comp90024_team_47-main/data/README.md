# Data Directory

This directory contains representative sample data and pre-computed
aggregations from our analytics pipeline.

## Why these files (not full data)?

Our Elasticsearch indices contain over 27,000 documents in total
(13,134 Mastodon posts + 11,723 BlueSky posts + 1,484 weather records
as of 12 May 2026). Full dumps would exceed GitLab's 100MB repo limit
and obscure rather than illuminate the data structure. We instead
include small, representative samples for review and unit-test setup,
plus key aggregation results for traceability of the report's claims.

## Layout

data/
├── samples/
│   ├── mastodon_sample.json     # 5 documents from posts_mastodon
│   ├── bluesky_sample.json      # 5 documents from posts_bluesky
│   └── weather_sample.json      # 4 documents (one per city, latest date)
├── aggregations/
│   ├── rq2_sentiment_distribution.csv      # Counts + % by platform
│   ├── rq2_compound_percentiles.csv        # Compound sentiment distribution
│   └── bluesky_harvest_strategy_distribution.csv  # Provenance breakdown
└── README.md

## File descriptions

### samples/

Each `*_sample.json` file contains 4–5 representative documents extracted
via the Elasticsearch query API, with `raw_payload` and `content_html`
fields excluded (these are stored for traceability in ES but redundant in samples).

The samples were chosen to include documents with non-null `city` attribution,
which best illustrates the schema's join key (city × date) used in cross-index
analyses.

### aggregations/

Pre-computed analytical results referenced in the report:

- **rq2_sentiment_distribution.csv** — Sentiment label counts and percentages
  per platform; the basis for the "BlueSky users skew more negative" finding
  in Section RQ2 of the report.

- **rq2_compound_percentiles.csv** — Mean, P25, P50, P75 of the VADER compound
  score per platform. Shows BlueSky's deeper negative tail (P25: −0.196 vs
  Mastodon's −0.065) despite a similar positive ceiling (P75 ≈ 0.47 on both).

- **bluesky_harvest_strategy_distribution.csv** — Post counts per
  `harvest_strategy` value, used to quantify the selection-bias mitigation
  discussed in `database/queries/clean_bluesky.md`. The 824 posts with
  `search:*weather*` / `heatwave` / `polar blast` / `auswx` strategies
  represent the biased subset filtered out for RQ1.

## Regenerating

The samples can be regenerated from a live cluster via:

```bash
# Forward Elasticsearch port
kubectl port-forward service/elasticsearch-es-http -n elastic 9200:9200

# Then re-run sample queries (see source: data/regenerate.sh if added later)
```