# Kubernetes Resources

K8s configuration for COMP90024 Team 47's data pipeline.

## Resources

| Type | Name | Purpose |
|---|---|---|
| Secret | mastodon-creds | Mastodon API token |
| Secret | bluesky-creds | BlueSky handle + app password |
| Secret | es-creds | Elasticsearch credentials |
| ConfigMap | fission-es-config | ES_URL for Fission functions |
| ConfigMap | bluesky-jwt | Cached refreshJwt for BlueSky session |
| Role + RoleBinding | bluesky-jwt-rw | Allow Fission pods to update bluesky-jwt |

## Deploy from scratch

```bash
# 1. Secrets — copy template, fill in real values, apply
cp secrets.example.yaml secrets.yaml
# Edit secrets.yaml with real credentials, then:
kubectl apply -f secrets.yaml
rm secrets.yaml   # keep this off disk after apply

# 2. ConfigMaps (no secrets, can apply directly)
kubectl apply -f configmaps.yaml

# 3. RBAC for BlueSky JWT cache
kubectl apply -f rbac/bluesky-jwt-rbac.yaml
```

## Fission resources (CLI, not declarative YAML)

The Fission environment, functions, and timers are deployed via the
`fission` CLI from `backend/fission/<function>/deploy.sh`. Each function
directory has its own `deploy.sh`. From repo root:

```bash
# Create environment (one-time)
fission environment create \
  --name python-39 \
  --image fission/python-env:latest \
  --builder fission/python-builder:latest \
  --version 3

# Deploy each function (idempotent; re-run to update)
cd backend/fission/weather_streaming  && ./deploy.sh && cd -
cd backend/fission/mastodon_streaming && ./deploy.sh && cd -
cd backend/fission/bluesky_streaming  && ./deploy.sh && cd -

# Create cron timers (one-time per function)
fission timer create --name weather-streaming-cron  --function weather-streaming  --cron "0 2 * * *"
fission timer create --name mastodon-streaming-cron --function mastodon-streaming --cron "*/10 * * * *"
fission timer create --name bluesky-streaming-cron  --function bluesky-streaming  --cron "0 */2 * * *"
```

## Verify deployment

```bash
kubectl get secrets -n default | grep -E "mastodon|bluesky|es-creds"
kubectl get configmap -n default | grep -E "fission-es|bluesky-jwt"
kubectl get role,rolebinding -n default | grep bluesky-jwt
fission function list
fission timer list
```
