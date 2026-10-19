# COMP90024 Team 47 — AusFlux

> A Cloud-Native Pipeline for Cross-Platform Sentiment Analysis of Australian Cities Under Weather Influence
>
> COMP90024 Cluster and Cloud Computing, Assignment 2  
> University of Melbourne, Semester 1, 2026

---

## Overview

**AusFlux** ingests, indexes, and analyses social-media posts from
Mastodon and BlueSky alongside daily weather observations from Open-Meteo
for four Australian cities (Melbourne, Sydney, Brisbane, Perth). The
system is deployed end-to-end on the Melbourne Research Cloud (MRC)
across a four-node Kubernetes cluster, comprising three Fission
streaming functions, an ECK-managed Elasticsearch storage layer, a
FastAPI service exposing 14 REST endpoints, and a Jupyter notebook that
consumes the data through a distinctive dual-mode access pattern.

At the time of submission the system has indexed over 33,000 documents
across three Elasticsearch indices and has been operating continuously
without restart for over three weeks.


## Research Questions

1. **RQ1.** Do weather conditions correlate with daily aggregate
   social-media sentiment in each of the four target Australian cities?

2. **RQ2.** How do Mastodon and BlueSky users differ in their sentiment
   expression and discourse vocabulary within the Australian context?


## Team

| Name           | Student ID | Email                                          |
|----------------|------------|------------------------------------------------|
| Xianglong Fu   | 1574396    | xianglong.fu@student.unimelb.edu.au            |
| Muchuan Ji     | 1677216    | muchuan.ji@student.unimelb.edu.au              |
| Zhuo Wen       | 1721633    | zwen5515@student.unimelb.edu.au                |
| Zeming Ji      | 1710904    | zeming.ji@student.unimelb.edu.au               |
| Chang Gu       | 1628985    | changgu@student.unimelb.edu.au                 |


## Deliverables

| Artefact            | Location                                              |
|---------------------|-------------------------------------------------------|
| Report (PDF)        | `docs/report.pdf`                                     |
| Demo video          | See `docs/report.pdf` Appendix D for the YouTube URL  |
| Kubeconfig          | `config.47.yaml` (shared separately with teaching team) |
| Git tag             | `v1.0-submission`                                     |


## Repository Layout

```text
COMP90024_team_47/
├── README.md                # This file
├── .gitlab-ci.yml           # CI/CD pipeline (Test / Build / Deploy)
├── .gitignore
├── .env.example             # Template for environment variables
│
├── frontend/                # Jupyter analytical client
│   ├── comp90024_team_47_analysis.ipynb   # Primary integrated notebook
│   ├── data_loader.py       # Elasticsearch direct (PIT pagination)
│   ├── api_client.py        # HTTP access via REST API
│   └── ...                  # Prototype notebooks and design notes
│
├── backend/
│   ├── api/                 # FastAPI service (14 endpoints, 754 LOC)
│   ├── fission/             # Three Fission streaming functions
│   │   ├── mastodon_streaming/
│   │   ├── bluesky_streaming/
│   │   └── weather_streaming/
│   └── shared/              # Reusable modules (sentiment, cities, transforms)
│
├── database/
│   ├── mappings/            # Elasticsearch index schemas (JSON)
│   ├── queries/             # Documented query patterns
│   └── load_*_history.py    # One-shot historical backfill scripts
│
├── k8s/                     # Kubernetes manifests (Deployment, ConfigMap, RBAC)
├── test/                    # Automated test suite (478 LOC, pytest, FakeES mock)
├── data/                    # Cached fixtures and aggregation snapshots
├── docs/                    # Report PDF, architecture diagram, figures
└── llm/                     # LLM usage declaration
```


## Quick Start

The instructions below assume `kubectl` access to the `comp90024`
cluster on the Melbourne Research Cloud has already been configured
through the kubeconfig file `config.47.yaml`.


### 1. Verify cluster health

```bash
kubectl get nodes
kubectl get pods --all-namespaces
```

You should see four nodes (one control-plane + three workers) and
running pods across the `default`, `fission`, and `elastic` namespaces.


### 2. Expose the REST API locally

```bash
kubectl port-forward svc/ccc-rest-api 8000:80
```

The API is now reachable at `http://localhost:8000`. Sanity check:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/summary
```

Interactive Swagger UI is available at `http://localhost:8000/docs`.


### 3. Expose Elasticsearch locally (for direct-mode notebook access)

```bash
kubectl port-forward service/elasticsearch-es-http -n elastic 9200:9200
```

Elasticsearch is now reachable at `https://localhost:9200`.


### 4. Run the analytical notebook

```bash
cd frontend
jupyter notebook comp90024_team_47_analysis.ipynb
```

In **Cell 3**, set the data-access mode:

```python
USE_API = True     # via REST API (default, assignment-mandated)
# USE_API = False  # direct Elasticsearch (faster, for development)
```

Then `Kernel → Restart Kernel and Run All Cells`. The notebook fetches
all data and renders 12 figures across the two research scenarios.


### 5. Run the test suite

```bash
pytest -q
```

All 7 test modules execute in approximately one second locally.
The same suite runs in GitLab CI on every push (see `.gitlab-ci.yml`).


## Architectural Highlights

Two design decisions distinguish AusFlux from a baseline solution
to the assignment brief.

**Dual-mode data access.** The analytical notebook switches between
direct Elasticsearch access and HTTP access through the REST API via a
single import flag. Both paths apply identical filters and produce
identical analytical output; the spec-compliant REST path becomes a
live, demonstrable component rather than a token gesture. See the
report Section 2 for details.

**Persistent JWT cache.** BlueSky's per-account session rate limit on
`createSession` is resolved by caching session tokens in a Kubernetes
ConfigMap with RBAC-scoped access from the Fission function. This
pattern provides cross-invocation state for a serverless function using
only native Kubernetes primitives, without introducing an additional
database service. Harvested BlueSky volume increased approximately
six-fold after deployment. See the report Section 8 for details.


## Technology Stack

| Layer          | Technology                                |
|----------------|-------------------------------------------|
| Infrastructure | OpenStack (Melbourne Research Cloud)      |
| Orchestration  | Kubernetes v1.34.6                        |
| Serverless     | Fission (pool-manager execution strategy) |
| Storage        | Elasticsearch (managed by ECK operator)   |
| API            | FastAPI (Python)                          |
| Client         | Jupyter Notebook                          |
| CI/CD          | GitLab CI                                 |
| Sentiment      | VADER                                     |


## License and Acknowledgements

This project was developed as coursework for COMP90024 Cluster and
Cloud Computing at the University of Melbourne, Semester 1, 2026.
External data is sourced from the public APIs of Mastodon
(`mastodon.au`), BlueSky (AT Protocol), and Open-Meteo, in accordance
with their respective terms of use. Use of large language models
during development is declared in the report (Section 11) and in
`llm/usage_declaration.md`.