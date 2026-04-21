# Generic NDP JupyterHub Kubernetes Deployment Documentation

This guide provides instruction for deploying the generic NDP JupyterHub Helm chart.

## Prerequisites

Ensure you have `kubectl` and `helm` installed and configured to interact with your Kubernetes cluster.

Nginx ingress controller is installed on your cluster; if not, you can follow [installation guide](https://docs.nginx.com/nginx-ingress-controller/installation/installing-nic/).

## Additional Resources

For more information on `kubectl` and `helm`, refer to the following resources:

- [kubectl Installation Guide](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Helm Installation Guide](https://helm.sh/docs/intro/install/)
- [Helm Documentation](https://helm.sh/docs/intro/using_helm/)

## **Installation**

1. #### **Copy and edit the example once so all targets share the same settings:**

    ```bash
    cp config.example.mk config.mk
    ```
    Then open ./config.mk and set values<br>
    ```bash
    vi config.mk
    ```
    [Optional: Click to see example `config.mk`](#configmk-settings)

2. #### **Setting Up Keycloak Client Credentials**

    Create a local secret file from the template (kept out of git):

    ```bash
    cp ./ndp-hub/jupyterhub_secret.yaml.template ./ndp-hub/jupyterhub_secret.yaml
    ```

    Then open ./ndp-hub/jupyterhub_secret.yaml and fill in the **`client_id`** and **`client_secret`** values provided by your NDP administrators: [support@nationaldataplatform.org](mailto:support@nationaldataplatform.org)
    ```bash
    vi ./ndp-hub/jupyterhub_secret.yaml
    ```

    Once the file is ready, apply the secret to your cluster: 
    >Quick heads-up: This command will create a Kubernetes secret containing your Keycloak client credentials you provided in `./ndp-hub/jupyterhub_secret.yaml`, which JupyterHub will use for authentication. Further details are in the [JupyterHub Secret Explanation](#jupyterhub-secret-explaination) section below.

    ```bash
    make create-jhub-secret
    ```

3. #### **Centralize Site Overrides**

    Copy the example file and fill in the fields that matter for your site:

    ```bash
    cp ./ndp-hub/site-values.example.yaml ./ndp-hub/site-values.yaml
    ```
    Then open ./ndp-hub/site-values.yaml and set values<br>
    ```bash
    vi ./ndp-hub/site-values.yaml
    ```
    For details and examples, [click to see the `Custom Site Values` section below](#custom-site-values)

4. #### **Update Helm Chart Dependencies:** Fetch and update Helm chart dependencies listed in `Chart.yaml`

   ```bash
   make update
   ```

5. #### **Deploy JupyterHub:** Install/upgrade the generic NDP JupyterHub in the target namespace using Helm
    
    >Quick heads-up: This Make target automatically layers `ndp-hub/site-values.yaml` (when present) on top of the defaults(`values.yaml`) and injects `spawner.py` via `--set-file`.

   ```bash
   make deploy
   ```

## **Access your JupyterHub**
`http://<ingress-host>/jupyter/`

## **Optional follow-up**: verify and cleanup

`make status`: Run to confirm helm release is healthy.<br>
`make get-ingress`: Grab the ingress endpoint when you need the URL.<br>
`make uninstall`: Remove the helm release.<br>
`make delete-jhub-secret`: Delete the jupyterhub-secret from the cluster.

## Next Steps
Go back to [**SciDx Kubernetes Document**](https://github.com/sci-ndp/scidx-k8s/tree/main#deploy-jupyterhub) for more details about the overall Kubernetes setup for SciDx service.

<br>

## config.mk Settings
`KUBE_CONTEXT`: kubernetes cluster context (defaults to **kubectl config current-context** if leaves empty, or **"microk8s"** if none).

`NAMESPACE`: namespace to deploy generic NDP Jupyterhub into (default: **ndp-jhub**).

`RELEASE_NAME`: Helm release name for generic NDP JupyterHub deployment (default: **ndp-jhub**).

Example:
```mk
KUBE_CONTEXT = arn:aws:eks:us-west-2:xxxxxxxxxxxx:cluster/cluster-name
HELM_RELEASE = ndp-jhub
NAMESPACE = ndp-jhub
```
[Back to `Installation`](#copy-and-edit-the-example-once-so-all-targets-share-the-same-settings)

## Custom Site Values

Goal: fill in `ndp-hub/site-values.yaml`. <br>
Gather these first:
   1. `Namespace`, it should be the same defined in config.mk → NAMESPACE;
   2. `DNS hostname` of your ingress controller users will hit (e.g., ndp-dev-202.chpc.utah.edu);
   3. `Client ID` from NDP admins, same as in jupyterhub_secret.yaml;
   4. `Group name` from NDP admins, to allow users in that group to login (e.g., jhub_user);
   5. `Admin user email`, at least one;
   6. `StorageClass names` to use for PVCs; run `kubectl get storageclass` if unsure.
   7. `Ingress class name` of your cluster ingress controller; run `kubectl get ingressclass` if unsure.


<br>Then open ndp-hub/site-values.yaml and replace every `<...>` in the template below.

>Caveats:
>1. Replace every `<...>` before deploying. `client_id` here must match the one in `ndp-hub/jupyterhub_secret.yaml`. 
>2. Make sure the keycloak url(`https://idp.nationaldataplatform.org`) in logout_redirect_url matches the NDP_KEYCLOAK_URL in extraEnv, consult NDP admins if unsure: [support@nationaldataplatform.org](mailto:support@nationaldataplatform.org).
>3. The namespace in extraEnv(`NDP_JUPYTERHUB_NAMESPACE`) must match the `NAMESPACE` in config.mk.

```yaml
# ndp-hub/site-values.yaml
jupyterhub:
  ingress:
    ingressClassName: <nginx>               # change if your ingress class is different
    hosts:
      - <hub.example.com>                   # REQUIRED: your DNS hostname
  hub:
    config:
      GenericOAuthenticator:
        oauth_callback_url: https://<hub.example.com>/jupyter/hub/oauth_callback   # same host as above
        logout_redirect_url: https://idp.nationaldataplatform.org/realms/NDP/protocol/openid-connect/logout?post_logout_redirect_uri=https://<hub.example.com>/jupyter/&client_id=<your-client-id>
        allowed_groups:
          - <your-keycloak-group>           # e.g., jhub_user
        admin_users:
          - <admin@example.com>             # admin user email 
    extraEnv:
      NDP_JUPYTERHUB_NAMESPACE: <ndp-jhub>  # must match config.mk NAMESPACE
      NDP_KEYCLOAK_URL: https://idp.nationaldataplatform.org
      NDP_KEYCLOAK_REALM: NDP
      PVC_STORAGE_CLASS: <storage-class>    # group shared PVCs; e.g., microk8s-hostpath, gp2, etc.
    db:
      pvc:
        storageClassName: <storage-class>   # hub DB PVC
  singleuser:
    storage:
      dynamic:
        storageClass: <storage-class>       # per-user PVC
```

### What you just configured
- **Auth**: Callback/logout URLs, which Keycloak groups can log in, and who gets JupyterHub admin.
- **Spawner env**: Namespace (`NDP_JUPYTERHUB_NAMESPACE`) and storage class the spawner uses; `spawner.py` reads these from `jupyterhub.hub.extraEnv`.
- **Storage**: StorageClass for the hub database PVC and for each user’s PVC.
- **Ingress**: Which ingress controller/class to bind to and which hostnames your DNS/TLS should cover.

[Back to `Installation`](#centralize-site-overrides)

## JupyterHub Secret Explaination

By executing `make create-jhub-secret`, you basically run:

```sh
kubectl create secret generic jupyterhub-secret \
  --from-file=values.yaml=jupyterhub_secret.yaml \
  -n jupyterhub
```

- The `--from-file=values.yaml=jupyterhub_secret.yaml` flag loads the contents of `jupyterhub_secret.yaml` into the secret under the key `values.yaml`.
- The resulting secret will look like:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: jupyterhub-secret
data:
  values.yaml: <base64-encoded contents of jupyterhub_secret.yaml>
```

[Back to `Installation`](#setting-up-keycloak-client-credentials)
