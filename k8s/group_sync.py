#!/usr/bin/env python3
"""
Sync collaboration group config from NDP Workspaces API to JupyterHub.

For each group returned by the workspaces API this script will:
  - Create the JupyterHub group (idempotent)
  - Add members to the group
  - Create a {group_name_slug}-{group_id_short}-collab user
  - Add the collab user to the "collaborative" group
  - Create/update the collab-access role so group members can spawn/access the collab server

Environment variables:
  JUPYTERHUB_API_TOKEN      - Token for JupyterHub admin API (from group-sync-secret)
  KEYCLOAK_CLIENT_ID        - Keycloak client_id (from jupyterhub-secret)
  KEYCLOAK_CLIENT_SECRET    - Keycloak client_secret (from jupyterhub-secret)
  WHERE_CREATED             - Namespace filter for workspaces API (e.g. NDP, WSTC, NAFSI)
  JUPYTERHUB_API_URL        - Internal hub URL (default: http://hub:8081/hub/api)
  WORKSPACE_API_URL         - Workspaces API base URL
  KEYCLOAK_URL              - Keycloak base URL
  POLL_INTERVAL             - Seconds between syncs. 0 = one-shot (CronJob), >0 = loop (Deployment)
"""

import os
import re
import sys
import time
import logging
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

JUPYTERHUB_API_URL   = os.environ.get("JUPYTERHUB_API_URL", "http://hub:8081/hub/api")
JUPYTERHUB_API_TOKEN = os.environ["JUPYTERHUB_API_TOKEN"]
WORKSPACE_API_URL    = os.environ.get("WORKSPACE_API_URL", "https://ndp-test.sdsc.edu/workspaces-api")
KEYCLOAK_URL         = os.environ.get("KEYCLOAK_URL", "https://idp-test.nationaldataplatform.org")
WHERE_CREATED        = os.environ.get("WHERE_CREATED", "NDP")
POLL_INTERVAL        = int(os.environ.get("POLL_INTERVAL", "0"))
NAMESPACE            = os.environ.get("NAMESPACE", "ndp-test")

_known_groups = None  # None = first run; dict of {group_id: jhub_name}


def load_keycloak_creds():
    """
    Load Keycloak client_id and client_secret from the mounted jupyterhub-secret
    file (same secret and parsing logic the hub uses in use_k8s_secret).
    Falls back to KEYCLOAK_CLIENT_ID / KEYCLOAK_CLIENT_SECRET env vars.
    Returns ("", "") if neither is available — auth will be skipped.
    """
    secret_file = os.environ.get("JUPYTERHUB_SECRET_FILE", "")
    if secret_file:
        try:
            with open(secret_file) as f:
                content = f.read()
            client_id = content.split('client_secret: ')[0].split('client_id: ')[1].split('\n')[0]
            client_secret = content.split('client_secret: ')[1].rstrip('\n')
            return client_id, client_secret
        except Exception as e:
            log.warning(f"Could not parse Keycloak creds from {secret_file}: {e}")
    return os.environ.get("KEYCLOAK_CLIENT_ID", ""), os.environ.get("KEYCLOAK_CLIENT_SECRET", "")


KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET = load_keycloak_creds()

HUB_HEADERS = {
    "Authorization": f"token {JUPYTERHUB_API_TOKEN}",
    "Content-Type": "application/json",
}


def get_service_token():
    """
    Fetch a short-lived access token from Keycloak using client credentials.
    Returns None if client credentials are not configured (open endpoint).
    """
    if not KEYCLOAK_CLIENT_ID or not KEYCLOAK_CLIENT_SECRET:
        return None
    resp = requests.post(
        f"{KEYCLOAK_URL}/realms/NDP/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": KEYCLOAK_CLIENT_ID,
            "client_secret": KEYCLOAK_CLIENT_SECRET,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_groups(token):
    """
    Fetch groups from workspaces API filtered by WHERE_CREATED.
    Returns a list of { group_id, group_name, entity_id, members: [...] }
    """
    headers = {"accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(
        f"{WORKSPACE_API_URL}/group/get_groups_by_cndp",
        params={"where_created": WHERE_CREATED},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def make_jhub_name(group_id, group_name):
    """
    Build a unique JupyterHub-safe name from group_name + short group_id.
    group_name is not unique in the API, so we suffix with 8 chars of group_id.

    e.g. "ES group - 2", "1769f3af-..." → "es-group-2-1769f3af"
    """
    slug = re.sub(r"[^a-z0-9]+", "-", group_name.lower()).strip("-")[:24]
    return f"{slug}-{group_id[:8]}"


def ensure_group(jhub_group):
    r = requests.post(f"{JUPYTERHUB_API_URL}/groups/{jhub_group}", headers=HUB_HEADERS)
    if r.status_code not in (200, 201, 409):
        log.warning(f"Unexpected status creating group '{jhub_group}': {r.status_code} {r.text}")


def add_users_to_group(jhub_group, users):
    if not users:
        return
    r = requests.post(
        f"{JUPYTERHUB_API_URL}/groups/{jhub_group}/users",
        headers=HUB_HEADERS,
        json={"users": users},
    )
    if r.status_code not in (200, 201):
        log.warning(f"Unexpected status adding users to '{jhub_group}': {r.status_code} {r.text}")


def ensure_user(username):
    r = requests.post(f"{JUPYTERHUB_API_URL}/users/{username}", headers=HUB_HEADERS)
    if r.status_code not in (200, 201, 409):
        log.warning(f"Unexpected status creating user '{username}': {r.status_code} {r.text}")


def restart_hub():
    """Trigger a rolling restart of the hub deployment using the pod's service account token."""
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
            sa_token = f.read().strip()
        ca_cert = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
        patch = {"spec": {"template": {"metadata": {"annotations": {
            "group-sync/restartedAt": datetime.utcnow().isoformat()
        }}}}}
        r = requests.patch(
            f"https://kubernetes.default.svc/apis/apps/v1/namespaces/{NAMESPACE}/deployments/hub",
            headers={"Authorization": f"Bearer {sa_token}", "Content-Type": "application/strategic-merge-patch+json"},
            json=patch,
            verify=ca_cert,
        )
        if r.status_code == 200:
            log.info("Hub rolling restart triggered for new groups")
        else:
            log.error(f"Failed to restart hub: {r.status_code} {r.text}")
    except Exception as e:
        log.error(f"Failed to restart hub: {e}", exc_info=True)


def delete_group(jhub_group):
    r = requests.delete(f"{JUPYTERHUB_API_URL}/groups/{jhub_group}", headers=HUB_HEADERS)
    if r.status_code not in (200, 204, 404):
        log.warning(f"Unexpected status deleting group '{jhub_group}': {r.status_code} {r.text}")


def delete_role(role_name):
    r = requests.delete(f"{JUPYTERHUB_API_URL}/roles/{role_name}", headers=HUB_HEADERS)
    if r.status_code not in (200, 204, 404):
        log.warning(f"Unexpected status deleting role '{role_name}': {r.status_code} {r.text}")


def remove_user_from_group(jhub_group, username):
    r = requests.delete(
        f"{JUPYTERHUB_API_URL}/groups/{jhub_group}/users",
        headers=HUB_HEADERS,
        json={"users": [username]},
    )
    if r.status_code not in (200, 204, 404):
        log.warning(f"Unexpected status removing '{username}' from '{jhub_group}': {r.status_code} {r.text}")


def delete_group(jhub_group):
    r = requests.delete(f"{JUPYTERHUB_API_URL}/groups/{jhub_group}", headers=HUB_HEADERS)
    if r.status_code not in (200, 204, 404):
        log.warning(f"Unexpected status deleting group '{jhub_group}': {r.status_code} {r.text}")


def delete_role(role_name):
    r = requests.delete(f"{JUPYTERHUB_API_URL}/roles/{role_name}", headers=HUB_HEADERS)
    if r.status_code not in (200, 204, 404):
        log.warning(f"Unexpected status deleting role '{role_name}': {r.status_code} {r.text}")


def remove_user_from_group(jhub_group, username):
    r = requests.delete(
        f"{JUPYTERHUB_API_URL}/groups/{jhub_group}/users",
        headers=HUB_HEADERS,
        json={"users": [username]},
    )
    if r.status_code not in (200, 204, 404):
        log.warning(f"Unexpected status removing '{username}' from '{jhub_group}': {r.status_code} {r.text}")


def upsert_role(role_name, scopes, groups):
    r = requests.get(f"{JUPYTERHUB_API_URL}/roles/{role_name}", headers=HUB_HEADERS)
    if r.status_code == 200:
        requests.delete(f"{JUPYTERHUB_API_URL}/roles/{role_name}", headers=HUB_HEADERS)
    r = requests.post(
        f"{JUPYTERHUB_API_URL}/roles",
        headers=HUB_HEADERS,
        json={"name": role_name, "scopes": scopes},
    )
    if r.status_code not in (200, 201):
        log.warning(f"Unexpected status creating role '{role_name}': {r.status_code} {r.text}")
        return
    for group in groups:
        r = requests.post(
            f"{JUPYTERHUB_API_URL}/groups/{group}/roles/{role_name}",
            headers=HUB_HEADERS,
        )
        if r.status_code not in (200, 201):
            log.warning(f"Unexpected status assigning role '{role_name}' to group '{group}': {r.status_code} {r.text}")


def sync():
    global _known_groups

    token = get_service_token()
    if token:
        log.info("Authenticated with Keycloak service account")
    else:
        log.info("No Keycloak credentials configured, calling workspaces API without auth")

    groups = fetch_groups(token)
    log.info(f"Fetched {len(groups)} groups (where_created={WHERE_CREATED})")

    current_groups = {g["group_id"]: make_jhub_name(g["group_id"], g["group_name"]) for g in groups}

    if _known_groups is None:
        _known_groups = current_groups
        log.info(f"First run: recorded {len(_known_groups)} existing groups as baseline")

    new_ids     = current_groups.keys() - _known_groups.keys()
    deleted_ids = _known_groups.keys() - current_groups.keys()

    # Trigger hub restart immediately for new groups — before iterating all groups
    if new_ids:
        new_names = [g["group_name"] for g in groups if g["group_id"] in new_ids]
        log.info(f"{len(new_ids)} new group(s) detected: {new_names} — triggering hub restart")
        restart_hub()

    # Clean up deleted groups via REST API — no hub restart needed
    if deleted_ids:
        log.info(f"{len(deleted_ids)} group(s) removed from workspaces API, cleaning up")
        for deleted_id in deleted_ids:
            jhub_name   = _known_groups[deleted_id]
            collab_user = f"{jhub_name}-collab"
            log.info(f"Cleaning up deleted group → '{jhub_name}'")
            delete_role(f"collab-access-{jhub_name}")
            remove_user_from_group("collaborative", collab_user)
            delete_group(jhub_name)

    _known_groups = current_groups

    ensure_group("collaborative")

    for group in groups:
        group_id   = group["group_id"]
        group_name = group["group_name"]
        members    = [m for m in (group.get("members") or []) if m]

        jhub_name   = make_jhub_name(group_id, group_name)
        collab_user = f"{jhub_name}-collab"

        log.info(f"Syncing '{group_name}' → '{jhub_name}' ({len(members)} members)")

        ensure_group(jhub_name)
        for _member in members:
            ensure_user(_member)
        add_users_to_group(jhub_name, members)
        ensure_user(collab_user)
        add_users_to_group("collaborative", [collab_user])


if __name__ == "__main__":
    if POLL_INTERVAL > 0:
        log.info(f"Starting group sync loop (interval={POLL_INTERVAL}s, where_created={WHERE_CREATED})")
        while True:
            try:
                sync()
                log.info(f"Sync complete, sleeping {POLL_INTERVAL}s...")
            except Exception as e:
                log.error(f"Sync failed: {e}", exc_info=True)
            time.sleep(POLL_INTERVAL)
    else:
        log.info(f"Running one-shot group sync (where_created={WHERE_CREATED})")
        try:
            sync()
            log.info("Group sync complete")
        except Exception as e:
            log.error(f"Group sync failed: {e}", exc_info=True)
            sys.exit(1)
