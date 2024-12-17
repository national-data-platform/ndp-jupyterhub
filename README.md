# NDP JupyterHub
## Core Documentation
- JupyterHub Deployment documentation on [Nautilus](https://docs.nationalresearchplatform.org/userdocs/jupyter/jupyterhub/)
- JupyterHub with z2jh can be found at https://z2jh.jupyter.org/

## Basic Set Up for NDP JupyterHub Customization

### Prepare Nautilus Namespace and Local Configuration

Use this [documentation](https://docs.nationalresearchplatform.org/) for comprehensive Nautilus setup:

1. Create a namespace using the Nautilus portal or use one of the NDP official namespaces (`ndp` / `ndp-staging` / `ndp-test`).
2. Ask NRP support to make you an admin in that namespace
3. Download `kubeconfig` file from the Nautilus portal

### Set up helm in your namespace

1. Download and install [`helm`](https://helm.sh/) locally:
   (source: https://z2jh.jupyter.org/en/stable/kubernetes/setup-helm.html)
   
   ```bash
   curl https://raw.githubusercontent.com/helm/helm/HEAD/scripts/get-helm-3 | bash
   helm version
   ```
   
   You can use [other installation methods](https://github.com/kubernetes/helm/blob/master/docs/install.md)
   if curling into bash bothers you.

### Install JupyterHub
1. Make Helm aware of the JupyterHub Helm chart repository so you can install the JupyterHub chart from it without having to use a long URL name.
   (source: https://z2jh.jupyter.org/en/stable/jupyterhub/installation.html#install-jupyterhub)
    ```bash
    helm repo add jupyterhub https://hub.jupyter.org/helm-chart/
    helm repo update
    ```
2. Fetch the version of JupyterHub chart mentioned in `helm/ndp-hub/requirements.yaml`.

   ```bash
   cd helm/ndp-hub
   helm dependency build
   helm dep up
   cd ..
   ```

3. Add random bytes for proxy:

   ```bash
   openssl rand -hex 32
   ```
   
   Add/replace output to `ndp-hub/values_<env>.yaml`:
  
   ```
   jupyterhub:
     proxy:
       secretToken: "..."
   ```

4. Create kubernetes secret
- In `jhub/helm/ndp-hub/jupyterhub_secret.yaml`, insert the client/secret values obtained from NDP admins
- Execute:
   ```bash
   kubectl create secret generic jupyterhub-secret --from-file=values.yaml=jhub/helm/ndp-hub/jupyterhub_secret.yaml --namespace <namespace>
   ```

5. Install the hub
- TEST
   ```bash
   make deploy-test
   ```
- STAGING
   ```bash
   make deploy-staging
   ```
- PRODUCTION
   ```bash
   make deploy-prod
   ```

6. Wait for the pods to be ready, and go to the URL specified in `jhub/helm/ndp-hub/values_env.yaml`:
   - https://ndp-test-jupyterhub.nrp-nautilus.io/
   - https://ndp-staging-jupyterhub.nrp-nautilus.io/
   - https://ndp-jupyterhub.nrp-nautilus.io/

7. To uninstall the deployment:
   
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

- `helm/ndp-hub` folder contains 3 `spawner_env.py` complimentary configuration files, such that values_env.yaml references spawner_env.py:
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
 - ~~https://github.com/national-data-platform/jupyter-templates - this is to override few UI web pages, based on this guide: https://jupyterhub.readthedocs.io/en/stable/howto/templates.html#extending-templates.~~ Note: this is not needed anymore as pics and templates are hardcoded into hub image (helm/k8s_hub_docker_image/Dockerfile).
 - https://github.com/national-data-platform/ndp-jupyterlab-extension - NDP extension for JupyterLab. It is being installed on single-user server instance each time while spawning. Defined in `spawner_env.py` files.
 - https://github.com/national-data-platform/jupyterlab-git - Special version of JupyterLab GIT extension. It was created to allow passing GIT link into GIT Clone dialog for NDP needs. It is being installed on single-user server instance each time while spawning. Defined in `spawner_env.py` files.
5. The main JupyterHub image is customized as well to be able to serve NDP logo images. It can be modified and built from `helm/k8s_hub_docker_image/Dockerfile`. In case of creating new image version, it has to be modified inside `helm/ndp-hub/values_<env>.yaml` files:
   ```
   hub:
     image:
       name: gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh
       tag: "2.0.9"
   ```
   
6. All NDP docker images and Python packages(PyPi) are stored in NRP Gitlab (https://gitlab.nrp-nautilus.io/).
- **Gitlab Container Registry (for Docker images)**. Enter your Gitlab username and personal access token:
``
docker login gitlab-registry.nrp-nautilus.io
``
Now, you should be able to push images to our Gitlab registry. For example: 
```
docker push gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh:2.0.10
```

Our images are located at: https://gitlab.nrp-nautilus.io/ndp/ndp-docker-images/container_registry

- **GitLab Package Registry (for PyPi packages)**.
To be able to push or pull private Python packages, the local machine should be set up according to the instructions at https://gitlab.nrp-nautilus.io/help/user/packages/package_registry/index.
Add authentication (https://gitlab.nrp-nautilus.io/help/user/packages/pypi_repository/index.md#authenticate-with-a-deploy-token).

Create file: ~/.pypirc
```
[distutils]
index-servers =
    gitlab

[gitlab]
repository = https://gitlab.nrp-nautilus.io/api/v4/projects/ndp%2Fndp-docker-images/packages/pypi
username = <your_personal_access_token_name>
password = <your_personal_access_token>
```
After that, you'll be able to push PyPi packages, so they can be installed later by standard pip command:
```
pip install jupyterlab-git ndp-jupyterlab-extension --index-url https://gitlab.nrp-nautilus.io/api/v4/projects/3930/packages/pypi/simple
```

Our packages are located at: https://gitlab.nrp-nautilus.io/ndp/ndp-docker-images/-/packages 

