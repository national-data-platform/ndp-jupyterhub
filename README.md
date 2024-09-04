# NDP JupyterHub
## Core Documentation
- JupyterHub Deployment documentation on [Nautilus](https://docs.nationalresearchplatform.org/userdocs/jupyter/jupyterhub/)
- JupyterHub with z2jh can be found at https://z2jh.jupyter.org/

## Basic Set Up for NDP JupyterHub Customization

### Prepare Nautilus Namespace

1. Create a namespace using the Nautilus portal or use one of the NDP official namespaces (for production / staging / test environments).
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
   
### Important Notes
1. Before making deployment to any environment, make sure to deploy the `helm/ndp-hub/jupyterhub_secret.yaml` with Keycloak secrets.

2.
- `helm/ndp-hub` folder contains 3 `values_env.yaml` Helm configuration files, corresponding to different environments:
   - `values_test.yaml`
   - `values_staging.yaml`
   - `values_prod.yaml`

- `helm/ndp-hub/charts/jupyterhub` folder contains 3 `spawner_env.py` complimentary configuration files, such that values_env.yaml references spawner_env.py:
  - `spawner_test.py`
  - `spawner_staging.py`
  - `spawner_prod.py`

   For example, values_test.yaml file has reference to spawner_test.py. This has been done in order to decouple YAML values from Python and HTML code.
   Each pair of files create unique customized deployment of NDP JupyterHub per each environment.
3. The pre-built images that appear in spawner_env.py files can be modified and built using Dockerfiles inside `images` folder. Each image corresponds to NDP use case such as:
   - NAIRR
   - PGML
   - Earthscope
   - Others

   Note: the content notebooks and other files inside the image typically is downloaded from separate repo:
   - https://github.com/national-data-platform/jupyter-notebooks
4. There are few other Jupyter dependencies in the following GIT repos:
 - https://github.com/national-data-platform/jupyter-templates - this is to override few pages UI, based on this guide: https://jupyterhub.readthedocs.io/en/stable/howto/templates.html#extending-templates
 - https://github.com/national-data-platform/ndp-jupyterlab-extension - NDP extension for JupyterLab. It is being installed on single-user server instance each time while spawning. Defined in `spawner_env.py` files.
 - https://github.com/national-data-platform/jupyterlab-git - Special version of JupyterLab GIT extension. It was created to allow passing GIT link into GIT Clone dialog for NDP needs. It is being installed on single-user server instance each time while spawning. Defined in `spawner_env.py` files.
5. The main JupyterHub image is customized as well to be able to serve NDP logo images. It can be modified and built from `helm/customize/Dockerfile`. In case of creating new image version, it has to be modified inside `helm/ndp-hub/charts/jupyterhub/values.yaml`:
   ```
   hub:
     image:
       name: gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh
       tag: "2.0.9"
   ```