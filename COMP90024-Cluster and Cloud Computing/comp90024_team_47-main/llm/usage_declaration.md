# LLM Usage Declaration

## Tools used

- **Claude** (Anthropic) — primary AI assistant used by the team

## Where LLMs were used

The team used Claude as a pair-programming and discussion partner for 
the following categories of work:

- **Concept clarification** — Kubernetes RBAC, Fission pool/newdeploy 
  executor types, ElasticSearch mapping types (keyword vs text).
- **Debugging assistance** — diagnosing the BlueSky `createSession` 
  rate-limiting issue and designing the JWT refresh caching solution; 
  resolving Fission function pod permission issues for ConfigMap access.
- **Code review** — reviewing transform modules, ES query construction, 
  FastAPI endpoint design.
- **Architecture discussion** — trade-offs between ETL and ELT, 
  declarative vs imperative K8s resource management, harvest strategy 
  provenance tracking.
- **Documentation** — drafting LaTeX report structure, READMEs, and 
  inline code comments.

## Where LLMs were NOT used (team original)

- Research question selection (RQ1, RQ2, RQ3).
- Final analytical interpretations.
- Schema design decisions (mapping types, index strategy).
- Cluster topology and deployment choices.
- Identification of the selection bias issue in `SEARCH_QUERIES` 
  (caught during peer code review).

## Verification

All AI-suggested code was:

1. Read and understood by a team member before integration.
2. Tested in the live cluster environment (cluster `comp90024`, 
   4 nodes) before commit.
3. Adapted to fit our specific naming conventions, namespace 
   structure, and Fission CLI version.

LLMs were treated as advisors, not oracles. We rejected or modified 
their suggestions where appropriate — for example, we chose a 
2-hour cron over LLM-suggested 30-minute cron (still over BlueSky's 
rate limit), and chose query-time filtering over LLM-suggested data 
re-collection for the selection-bias issue.
