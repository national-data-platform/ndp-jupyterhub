# JupyterHub Collaboration — Deploy Guide

Deploys the group-sync collab infrastructure to a new namespace.

**Namespace placeholder:** replace `<ns>` with the target namespace throughout.

---

## Prerequisites

- `kubectl` access to the target namespace
- Docker + push access to `gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images`
- Helm configured for the cluster
- Existing JupyterHub running in `<ns>`

---

## Step 1 — Generate secrets

```bash
openssl rand -hex 16   # → POSTGRES_PASSWORD
openssl rand -hex 32   # → GROUP_SYNC_TOKEN
```

Keep both values; you'll need them in the next two steps.

---

## Step 2 — Create k8s secrets

```bash
kubectl create secret generic postgres-secret \
  --from-literal=password=<POSTGRES_PASSWORD> \
  -n <ns> --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic group-sync-secret \
  --from-literal=jupyterhub-api-token=<GROUP_SYNC_TOKEN> \
  -n <ns> --dry-run=client -o yaml | kubectl apply -f -
```

---

## Step 3 — Deploy PostgreSQL

Edit `k8s/postgres.yaml`: update `namespace` to `<ns>`, then:

```bash
kubectl apply -f k8s/postgres.yaml -n <ns>

# Wait for postgres pod to be Running
kubectl get pods -n <ns> -l app=postgres -w
```

---

## Step 4 — Migrate SQLite → PostgreSQL

> **Skip this step if the existing JupyterHub is already on PostgreSQL.**
> Only needed when the hub's `values.yaml` has `db.type: sqlite-pvc` (the default).

This requires a short maintenance window (hub will be scaled to 0).

### 4a. Confirm the hub is on SQLite

```bash
kubectl exec -n <ns> $(kubectl get pod -n <ns> -l component=hub -o jsonpath='{.items[0].metadata.name}') \
  -- env | grep -i db
# If no DB_URL appears, it's on SQLite
```

### 4b. Scale hub to 0

```bash
kubectl scale deployment hub --replicas=0 -n <ns>
```

### 4c. Run a migration pod

The file `k8s/migrate-sqlite-postgres.yaml` mounts the hub's SQLite PVC and runs pgloader.
Update `claimName` if your PVC name differs from `hub-db-dir`, then:

```bash
kubectl apply -f k8s/migrate-sqlite-postgres.yaml -n <ns>
kubectl wait --for=condition=Ready pod/sqlite-migrate -n <ns> --timeout=60s

# Run pgloader inside the pod
kubectl exec -n <ns> sqlite-migrate -- pgloader \
  sqlite:///db/jupyterhub.sqlite \
  "postgresql://jupyterhub:${POSTGRES_PASSWORD}@postgres:5432/jupyterhub"

# Verify row counts (use postgres pod — pgloader image has no psql)
POSTGRES_POD=$(kubectl get pod -n <ns> -l app=postgres -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n <ns> $POSTGRES_POD -- psql -U jupyterhub -d jupyterhub \
  -c "SELECT 'users', count(*) FROM users UNION ALL SELECT 'spawners', count(*) FROM spawners UNION ALL SELECT 'api_tokens', count(*) FROM api_tokens;"

# Fix pgloader type mismatches — required or the hub will crashloop on startup
kubectl exec -n <ns> $POSTGRES_POD -- psql -U jupyterhub -d jupyterhub \
  -f /dev/stdin < k8s/post_migration_fixes.sql

# Clean up migration pod
kubectl delete pod sqlite-migrate -n <ns>
```

The SQLite PVC is not deleted — it remains as a rollback option.

---

## Step 5 — Build and push the Docker image

Skip if reusing an existing image tag.

```bash
docker build ./helm/k8s_hub_docker_image \
  -f ./helm/k8s_hub_docker_image/Dockerfile \
  -t gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh:<tag> \
  --platform=linux/amd64

docker push gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh:<tag>
```

---

## Step 6 — Update values and spawner

In the environment's `values_<env>.yaml`, apply these changes:

```yaml
jupyterhub:
  hub:
    image:
      name: gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh
      tag: "<tag>"
    deploymentStrategy:
      type: RollingUpdate          # required for Postgres; SQLite only supports Recreate
    db:
      type: postgres
      url: "postgresql+psycopg2://jupyterhub:placeholder@postgres:5432/jupyterhub"
    extraEnv:
      JUPYTERHUB_DB_PASS:
        valueFrom:
          secretKeyRef:
            name: postgres-secret
            key: password
      JUPYTERHUB_GROUP_SYNC_TOKEN:
        valueFrom:
          secretKeyRef:
            name: group-sync-secret
            key: jupyterhub-api-token
```

In `spawner_<env>.py`, ensure `NAMESPACE`, `WORKSPACE_API_URL`, and `KEYCLOAK_URL` point to the correct environment.

```bash
cd helm/ndp-hub && python generate_values.py --env <env>
```

---

## Step 7 — Deploy hub

```bash
make deploy-<env>

# Watch hub come up
kubectl get pods -n <ns> -l component=hub -w
kubectl logs -n <ns> -l component=hub -f
```

Hub should start, connect to Postgres, and run DB migrations automatically.

---

## Step 8 — Verify hub

```bash
# No DB errors in hub logs
kubectl logs -n <ns> -l component=hub | grep -i "error\|postgres\|alembic"

# Collaborations page loads
curl -I https://<hub-url>/hub/collaborations

# Entity map endpoint responds
curl -s https://<hub-url>/hub/ndp/group-entities \
  -H "Authorization: token <any-admin-token>" | python3 -m json.tool | head -20
```

---

## Step 9 — Deploy group-sync

Always apply the ConfigMap from the file first, then the deployment manifest.
Update `k8s/group_sync_deployment.yaml` with the correct namespace, `WORKSPACE_API_URL`, `KEYCLOAK_URL`, and `NAMESPACE` env var before applying.

```bash
kubectl create configmap group-sync-script \
  --from-file=group_sync.py=k8s/group_sync.py \
  -n <ns> --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f k8s/group_sync_deployment.yaml
```

---

## Step 10 — Verify end-to-end

```bash
kubectl logs -n <ns> -l app=group-sync -f

# Expected log lines:
# Authenticated with Keycloak service account
# Fetched N groups (where_created=NDP)
# Syncing 'group-name' → 'slug-abcd1234' (N members)
# Sync complete, sleeping 60s...
```

Once sync is complete, restart the hub so it picks up all newly created groups and roles:

```bash
kubectl rollout restart deployment hub -n <ns>
```

Navigate to `https://<hub-url>/hub/collaborations` and confirm:
- Group servers are listed
- Entity column shows `type: name` values
- Admin nav link only visible to full admins

---

## What this branch adds

A summary of the non-environment-specific changes introduced in this branch, relative to a vanilla prod deployment. Useful when porting to a new environment or reviewing what was changed.

### `values_<env>.yaml`

| Change | Why |
|---|---|
| `hub.image.tag` bumped to `3.0.14` | Images `3.x` and above are built specifically for JupyterHub collaboration support. Versions from `3.0.1` to the latest `3.x` are mostly UI and minor feature changes on top of that base. |
| `db.type: postgres` + `db.url` | PostgreSQL is required for `RollingUpdate`; SQLite only supports `Recreate` |
| `deploymentStrategy.type: RollingUpdate` | Zero-downtime restarts; only possible with Postgres |
| `extraEnv.JUPYTERHUB_DB_PASS` | Hub reads the Postgres password from this env var at startup |
| `extraEnv.JUPYTERHUB_GROUP_SYNC_TOKEN` | API token used by the group-sync service to call the JupyterHub admin API |

### `spawner_<env>.py`

#### New features

- **Collaborations page** (`/hub/collaborations`) — custom handler that renders `collaborations.html` in place of the default admin panel. Registered via `c.JupyterHub.extra_handlers`.
- **Group entity map** (`/hub/ndp/group-entities`) — JSON endpoint serving a `{group_slug: "entity_type: entity_name"}` map used by the collaborations page frontend for the entity column.
- **Startup group fetch** — at hub boot, fetches all groups from the workspaces API and pre-registers per-group collab access roles (`collab-access-{name}`) so group members can access their collab server immediately without waiting for a hub restart.
- **Collab pod spawning** — usernames ending in `-collab` take a separate spawn path: uses the *requesting* user's auth token (collab users have no auth state of their own), skips the private user PVC, disables PVC creation (`storage_pvc_ensure = False`), and installs `jupyter-collaboration` at startup.
- **Single-entity display** — when a user belongs to exactly one entity, the spawn form shows a static label instead of a dropdown.
- **group-sync service** — registered as a JupyterHub service with `admin: True` using the token from `JUPYTERHUB_GROUP_SYNC_TOKEN`. `c.JupyterHub.load_groups = {"collaborative": []}` pre-creates the `collaborative` group at hub startup.
- **PostgreSQL db_url** — `c.JupyterHub.db_url` set explicitly from `JUPYTERHUB_DB_PASS` env var.
- **`get_groups_by_cndp()` function** — fetches all groups for a CNDP namespace; used during collab spawn to match a collab username back to its group's entity.

#### Robustness fixes (also present in this branch)

- `if not auth_state: return` early exit in `auth_state_hook` — prevents a crash if auth state is missing.
- `getattr(spawner, 'entity_id', '')` instead of direct attribute access — guards against missing attributes on the spawner.
- Token refresh in `options_form` — explicitly calls `check_refresh_token_keycloak` and saves the refreshed token before fetching entities.
- Services and load_roles use `.append()` instead of direct assignment — safe for additive config across multiple config blocks.

---

## Rollback

If the hub fails to start after Step 7:

```bash
helm rollback <release-name> -n <ns>
```

If migrated from SQLite, the original PVC (`hub-db-dir`) is still intact. Revert `db.type` to `sqlite-pvc` in the values file and redeploy to restore the previous state.
