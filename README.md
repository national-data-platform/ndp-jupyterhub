# NDP JupyterHub
## Core Documentation
- JupyterHub Deployment documentation on [Nautilus](https://docs.nationalresearchplatform.org/userdocs/jupyter/jupyterhub/)
- JupyterHub with z2jh can be found at https://z2jh.jupyter.org/

## Basic Set Up for NDP JupyterHub Customization

### Prepare Nautilus Namespace

1. Create a namespace using the Nautilus portal or use one of the NDP namespaces (production / staging / test).
2. Ask NRP support to make you an admin in that namespace
3. Download `kubeconfig` file from the Nautilus portal

### Set up helm in your namespace

1. Download and install `helm` locally:
   
   ```bash
   curl https://raw.githubusercontent.com/kubernetes/helm/master/scripts/get | bash
   ```
   
   You can use [other installation methods](https://github.com/kubernetes/helm/blob/master/docs/install.md)
   if curling into bash bothers you.

### Install JupyterHub

1. Fetch the version of JupyterHub chart mentioned in `requirements.yaml`.

   ```bash
   cd helm/ndp-hub
   helm dep up
   cd ..
   ```

2. Add random bytes for proxy:

   ```bash
   openssl rand -hex 32
   ```
   
   Add output to `ndp-hub/values_<env>.yaml`:
  
   ```
   jupyterhub:
     proxy:
       secretToken: "..."
   ```

3. Create kubernetes secret
- In `jhub/helm/ndp-hub/jupyterhub_secret.yaml`, insert the values obtained from NDP admins
- Execute:
   ```bash
   kubectl create secret generic jupyterhub-secret --from-file=values.yaml=jhub/helm/ndp-hub/jupyterhub_secret.yaml -n ndp-test
   ```

4. Install the hub

   ```bash
   helm upgrade --cleanup-on-fail --install ndp-hub ndp-hub --kube-context nautilus --namespace <namespace> --values ndp-hub/values_<env>.yaml
   ```

5. Wait for the pods to be ready, and go to the URL specified in values_env.yaml

6. To uninstall the deployment:
   
   ```bash
   helm uninstall ndp-hub --kube-context nautilus --namespace <namespace>
   ```
