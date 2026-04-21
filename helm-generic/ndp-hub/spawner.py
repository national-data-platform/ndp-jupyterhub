from tornado.web import HTTPError
from kubespawner import KubeSpawner
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
import requests
import logging
from jinja2 import Template
from oauthenticator.generic import GenericOAuthenticator
from secrets import token_hex
import copy
import os
import base64
import http.client
import socket
import json
from datetime import date, datetime


def use_k8s_secret(namespace, secret_name):
    config.load_incluster_config()
    v1 = client.CoreV1Api()

    # get secret values
    secret = v1.read_namespaced_secret(name=secret_name, namespace=namespace)
    secret_data = secret.data
    value = base64.b64decode(secret_data['values.yaml']).decode('utf-8')  # extract string from k8s secret

    client_id_splitted = value.split('client_secret: ')[0].split('client_id: ')[1]  # isolate cliect_secret_value
    client_id_splitted = client_id_splitted.split('\n')[0]  # cut \n

    client_secret_splitted = value.split('client_secret: ')[1]  # isolate cliect_secret_value
    client_secret_splitted = client_secret_splitted[:-1]  # cut \n

    return client_id_splitted, client_secret_splitted

NAMESPACE = os.environ.get('NDP_JUPYTERHUB_NAMESPACE', 'ndp-jhub')

CLIENT_ID, CLIENT_SECRET = use_k8s_secret(namespace=NAMESPACE, secret_name='jupyterhub-secret')
KEYCLOAK_URL = os.environ.get('NDP_KEYCLOAK_URL', 'https://idp.nationaldataplatform.org').rstrip('/')
KEYCLOAK_REALM = os.environ.get('NDP_KEYCLOAK_REALM', 'NDP').strip('/')
OAUTH_BASE = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect"

NDP_EXT_VERSION = '0.0.22+aa2458c'

USER_PERSISTENT_STORAGE_FOLDER = "_User-Persistent-Storage"
STORAGE_CLASS = os.environ.get('PVC_STORAGE_CLASS', 'microk8s-hostpath')

CKAN_API_URL = "https://nationaldataplatform.org/catalog/api/3/action/"
PREKAN_API_URL = "https://nationaldataplatform.org/catalog2/ndp/"
WORKSPACE_API_URL = "https://nationaldataplatform.org/workspaces-api"
REFRESH_EVERY_SECONDS = 1200

os.environ['JUPYTERHUB_CRYPT_KEY'] = token_hex(32)

original_profile_list = [
    {
        'display_name': "NDP-EP/SciDx Remote Execution Environment",
        'default': False,
        'slug': "13",
        'kubespawner_override': {
            'image': 'yutianqin/scidx-rexec-quickstart:latest',
            'image_pull_policy': 'Always',
        }
    },
    {
        'display_name': "NDP Endpoint Data Streaming & Data Staging Examples",
        'default': False,
        'slug': "12",
        'kubespawner_override': {
            'image': 'yutianqin/rai-utah-hackathon:latest',
        }
    },
    {
        'display_name': "Minimal NDP Starter Jupyter Lab",
        'default': True,
        'slug': "1",
    },
    {
        'display_name': "Minimal NDP Starter Jupyter Lab + RStudio",
        'slug': "11",
        'default': False,
        'kubespawner_override': {
            'image': 'gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jhub-spawn:rstudio_v0.0.1',
            'default_url': '/lab'
        }
    },
    {
        'display_name': "NDP Catalog Search",
        'default': False,
        'slug': "10",
        'kubespawner_override': {
            'image': 'gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jhub-spawn:catalog_search_v0.9',
        }
    },
    {
        'display_name': "Physics Guided Machine Learning Starter Code ",
        'slug': "2",
        'default': False,
        'kubespawner_override': {
            'image': 'gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jhub-spawn:pgml_v0.1.7.3',
        }
    },
    {
        'display_name': "SAGE Pilot Streaming Data Starter Code",
        'slug': "3",
        'default': False,
        'kubespawner_override': {
            'image': 'gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jhub-spawn:sage_v0.2.1.6',
        }
    },
    {
        'display_name': "EarthScope Consortium Streaming Data Starter Code",
        'slug': "4",
        'default': False,
        'kubespawner_override': {
            'image': 'gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jhub-spawn:earthscope_v0.2.4.3',
        }
    },
    {
        'display_name': "NAIRR Pilot - NASA Harmonized Landsat Sentinel-2 (HLS) Starter Code",
        'slug': "5",
        'default': False,
        'kubespawner_override': {
            'image': 'gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jhub-spawn:nair_v0.0.0.17',
        }
    },
    {
        'display_name': "LLM Training (CUDA 12.3, tested with 1 GPU, 12 cores, 64GB RAM, NVIDIA A100-80GB)",
        'slug': "6",
        'default': False,
        'kubespawner_override': {
            'image': 'gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jhub-spawn:llm_v0.0.0.16_big',
        }
    },
    {
        'display_name': "LLM Service Client (Minimal, No CUDA)",
        'slug': "7",
        'default': False,
        'kubespawner_override': {
            'image': 'gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jhub-spawn:llm_v0.0.0.14_small',
        }
    },
    {
        'display_name': "TLS Fuel-Size Segmentation 2023",
        'slug': "8",
        'default': False,
        'kubespawner_override': {
            'image': 'gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jhub-spawn:tls_class_0.0.0.5',
        }
    },
    {
        'display_name': "NOAA-GOES Analysis",
        'slug': "9",
        'default': False,
        'kubespawner_override': {
            'image': 'gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jhub-spawn:noaa_goes_v0.0.0.3',
        }
    },
    {
        'display_name': "NOAA-SAGE-EARTHSCOPE Starter Codes",
        'slug': "10",
        'default': False,
        'kubespawner_override': {
            'image': 'gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jhub-spawn:utah_demos_0.0.0.1',
        }
    },
]

class MySpawner(KubeSpawner):
    notebook_dir = '/home/jovyan/work'
    profile_form_template = """


                    <style>
                    /* The profile description should not be bold, even though it is inside the <label> tag */
                        font-weight: normal;
                    }
                    </style>

                    <label for="entity-select">What do you want to work on?</label>
                    <select class="form-control input" name="entity" required>
                    <option value="" disabled {% if not preselected_entity %}selected{% endif %}>Select</option>
                    {% for entity in entity_list %}
                    {% set value = entity.workspace_id or entity.entity_id %}
                    {% if value %}
                    {% set selected = "selected" if preselected_entity and value|string == preselected_entity|string else "" %}
                    <option value="{{ value|string }}" {{ selected }}>
                        {{ entity.name or "Unnamed" }}
                    </option>
                    {% endif %}
                    {% endfor %}
                    </select>

                    <!-- Profile selection -->
                    <div class='form-group' id='kubespawner-profiles-list'>
                    <br>
                    <label for="profile-select">Select Pre-Built Image
                        (<a href="https://github.com/national-data-platform/jupyter-notebooks/blob/main/README.md" target="_blank">Pre-Built Image Guide</a>):
                    </label>
                    <select name="profile" id="profile-select" class="form-control input">
                        {% for profile in profile_list %}
                        <option value="{{ loop.index0 }}" {% if profile.default %}selected{% endif %}>
                            {{ profile.display_name }}
                            {% if profile.description %} - {{ profile.description }}{% endif %}
                        </option>
                        {% endfor %}
                    </select>
                    <label for="custom_image">Or Bring Your Own Image 
                        (<a href="https://jupyter-docker-stacks.readthedocs.io/en/latest/using/selecting.html" target="_blank">JupyterLab Compatible</a>):
                    </label>
                    <input name="custom_image" type="text" class="form-control input" autocomplete="on" placeholder="Enter your custom image URL here, including the tag. For example: jupyter/r-notebook:latest"/>

                    <!-- Timeout configuration -->
                    <label for="timeout">Timeout (in seconds): once a server has been successfully spawned, time to wait until it actually starts </label>
                    <input name="timeout" type="text" class="form-control input" autocomplete="off" placeholder="1200"/>
                    </div>

                    <b><i>Note:</b> Please stop your server after it is no longer needed, or in case you want to launch different content image
                    <p style="color:green;">In order to stop the server from running Jupyter Lab, go to File > Hub Control Panel > Stop Server</i></p>
                    <p><i><b>Note:</b> /home/jovyan/work/_User-Persistent-Storage is the persistent volume directory, make sure to save your work in it, otherwise it will be deleted</p>
                    """
    
    async def options_from_form(self, formdata):
        # print(f'1. self._profile_list: {self._profile_list}')
        pvc_users = {}

        if not self.profile_list: # or not hasattr(self, '_profile_list'):
            return formdata

        # profile selection
        selected_profile = int(formdata.get('profile', [0])[0])
        options = self.profile_list[selected_profile]
        # print(f'2. options: {options}')

        # Ensure kubespawner_override exists
        if 'kubespawner_override' not in options:
            options['kubespawner_override'] = {}
        # print(f'3. options: {options}')

        # Check if the selected profile is the custom option
        custom_image = formdata.get('custom_image', [''])[0]
        if custom_image:
            options['kubespawner_override']['image'] = custom_image
        # print(f'4. options: {options}')

        self.log.info("Applying KubeSpawner override for profile '%s'", options['display_name'])
        kubespawner_override = options.get('kubespawner_override', {})

        gpus = int(formdata.get('gpus', [0])[0])

        for k, v in kubespawner_override.items():
            if callable(v):
                v = v(self)
                self.log.info(".. overriding KubeSpawner value %s=%s (callable result)", k, v)
            else:
                self.log.info(".. overriding KubeSpawner value %s=%s", k, v)

            if k != "image":
                setattr(self, k, v)
            else:
                image = v
                if isinstance(v, dict):
                    if gpus > 0:
                        image = v["cuda"]
                    else:
                        image = v["cpu"]

                # if not (":" in image):
                    # image += ":" + 'latest'
                    # image += ":" + formdata.get('tag', [0])[0]

                setattr(self, k, image)

                selected_id = formdata.get('entity', [''])[0]
        
        selected_id = formdata.get('entity', [''])[0]
        entity_name = ''
        workspace_id = ''
        entity_id = ''
        for entity in self.entity_list:
            if entity.get('workspace_id') == selected_id or entity.get('entity_id') == selected_id:
                entity_name = entity.get('name', '')
                workspace_id = entity.get('workspace_id', '')
                entity_id = entity.get('entity_id', '')
                break
        
        self.entity_id = entity_id
        self.workspace_id = workspace_id
        self.entity_name = entity_name

        self.volume_mounts = [
            {
                'name': 'volume-{username}',
                'mountPath': f'/home/jovyan/work/{USER_PERSISTENT_STORAGE_FOLDER}',
            }
        ]
        self.volumes = [
            {
                'name': 'volume-{username}',
                'persistentVolumeClaim': {
                    'claimName': 'claim-{username}'
                }
            },
        ]
        if formdata.get('shm', [0])[0]:
            self.volume_mounts.append({
                'name': 'dshm',
                'mountPath': '/dev/shm',
            })
            self.volumes.append({
                'name': 'dshm',
                'emptyDir': {'medium': 'Memory'}
            })

        if self.user.name in pvc_users:
            self.volume_mounts.append({
                'name': 'cephfs',
                'mountPath': '/cephfs',
            })
            self.volumes.append({
                'name': 'cephfs',
                'persistentVolumeClaim': {
                    'claimName': 'jupyterlab-cephfs-' + pvc_users[self.user.name]
                }
            })
        self.extra_volumes = self.volumes
        self.extra_volume_mounts = self.volume_mounts

        if formdata.get('timeout', [0])[0]:
            self.http_timeout=int(formdata.get('timeout', [0])[0])
        else:
            self.http_timeout = 1200

        return options

    async def options_form(self, spawner):
        try:
            entities = await get_user_entities(spawner.access_token)
        except Exception as e:
            self.log.error(f"Error fetching entities: {e}")
            entities = []

        # Grab ?source=... from request (if present)
        source = None
        if spawner.handler and "source" in spawner.handler.request.arguments:
            source = spawner.handler.request.arguments["source"][0].decode("utf-8")

        print(f"Entities fetched: {entities}")
        print(f"Source: {source}")
        self.entity_list = entities

        template = Template(self.profile_form_template)
        rendered_form = template.render(
            profile_list=self.profile_list,
            entity_list=entities,
            preselected_entity=source,
        )
        return rendered_form



class MyAuthenticator(GenericOAuthenticator):
    async def refresh_user(self, user, handler):
        """
        Will allow to a=start spawning, if access_token/refresh_token are updated, or redirect to logout otherwise
        :param user:
        :param handler:
        :return:
        """
        # print(f'Handler: {handler}')

        print(f"[refresh_user] refreshing authenticator refresh_user for {user.name}")
        print(f"[refresh_user] called for user={user.name!r}, handler={handler!r}")
        auth_state = await user.get_auth_state()
        print(f"[refresh_user] auth_state={auth_state!r}")
        # print(auth_state)
        if auth_state:
            if not await self.check_and_refresh_tokens(user, auth_state):
                if handler:
                    # print(f'Redirecting to logout')
                    # handler.clear_cookie("jupyterhub-hub-login")
                    # handler.clear_cookie("jupyterhub-session-id")
                    # handler.redirect('/hub/logout')
                    # print(f'Redirected to logout')
                    raise HTTPError(401, "Your session has expired. Please log out and log in again.")
                    # Optionally, you can stop further processing
                    # handler.finish()
                    # return False
                return False
        return True

    async def check_and_refresh_tokens(self, user, auth_state):
        """
        Will set new access_token and refresh_token into auth_state and return True, if refresh is possible,
        or will return False otherwise
        :param user:
        :param auth_state:
        :return:
        """
        # print(f"[check_and_refresh_tokens] starting refresh for {user.name!r}")
        refresh_token_valid = self.check_refresh_token_keycloak(auth_state)
        # print(f'refresh_token_valid: {refresh_token_valid}')
        # print(f"[check_and_refresh_tokens] auth_state={auth_state!r}")
        if refresh_token_valid:
            # here we need to refresh access_token
            print('Trying to refresh access_token')
            auth_state['access_token'], auth_state['refresh_token']  = refresh_token_valid
            await user.save_auth_state(auth_state)
            print(f"Updated auth_state saved for {user.name}")
            return True
        else:
            return False



    def check_refresh_token_keycloak(self, auth_state):
        """
        Will return tuple of access_token and refresh_token if refresh is possible, or False otherwise
        :param auth_state:
        :return:
        """
        _access_token = auth_state.get('access_token')
        _refresh_token = auth_state.get('refresh_token')
        print(f"[check_refresh_token_keycloak] Keycloak_URL={KEYCLOAK_URL}, CLIENT_ID={CLIENT_ID}, CLIENT_SECRET={CLIENT_SECRET}")
        try:
            response = requests.post(f"{OAUTH_BASE}/token",
                                    data={
                                        'grant_type': 'refresh_token',
                                        'refresh_token': _refresh_token,
                                        'client_id': CLIENT_ID,
                                        'client_secret': CLIENT_SECRET
                                    })
        except Exception as e:
            print(f"[check_refresh_token_keycloak] HTTP request failed: {e}")
            return False
        
        if response.status_code == 200:
            print(f"Refresh token is still good!")
            new_access_token = response.json().get('access_token')
            new_refresh_token = response.json().get('refresh_token')
            return new_access_token, new_refresh_token
        else:
            print(f"[check_refresh_token_keycloak] response status={response.status_code}, body={response.text}")
            return False

# pass access_token and refresh_token for communicating with NDP APIs
def auth_state_hook(spawner, auth_state):
    spawner.access_token = auth_state['access_token']
    spawner.refresh_token = auth_state['refresh_token']
    spawner.environment.update({'ACCESS_TOKEN': spawner.access_token})
    spawner.environment.update({'REFRESH_TOKEN': spawner.refresh_token})

## Functions to retrieve user PVCs
async def get_user_pvcs(token):
    try:
        conn = http.client.HTTPSConnection("nationaldataplatform.org")
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'}
        conn.request("GET", "/workspaces-api/read_pvc_by_user", headers=headers)
        response = conn.getresponse()
        if response.status != 200:
            return []
        data = json.loads(response.read().decode("utf-8"))
        return data
    except (http.client.HTTPException, TimeoutError, json.JSONDecodeError, socket.timeout):
        return []
    
## Function to retrieve user entities
async def get_user_entities(token):
    try:
        conn = http.client.HTTPSConnection("nationaldataplatform.org")
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'}
        conn.request("GET", "/workspaces-api/get_entity_names_by_user", headers=headers)
        response = conn.getresponse()
        if response.status != 200:
            return []
        data = json.loads(response.read().decode("utf-8"))
        return data
    except (http.client.HTTPException, TimeoutError, json.JSONDecodeError, socket.timeout):
        return []

## Function to update PVC status

async def update_pvc(token, pvc_id):
    try:
        conn = http.client.HTTPSConnection("nationaldataplatform.org")
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        payload = json.dumps({
            "pvc_id": pvc_id,
            "status": "Active",
            "last_mounted": datetime.utcnow().isoformat()
        })

        conn.request("PUT", "/workspaces-api/update_pvc", body=payload, headers=headers)
        response = conn.getresponse()

        if response.status == 200:
            print(f"PVC with id {pvc_id} updated succesfully")
        else:
            print(f"Failed to update PVC with id {pvc_id}")

    except (http.client.HTTPException, TimeoutError, json.JSONDecodeError, socket.timeout) as e:
        return f"Exception occurred: {str(e)}"

async def pre_spawn_hook(spawner):
    config.load_incluster_config()
    api = client.CoreV1Api()
    # Reset the profile list to ensure custom image is not retained
    # print(f'10. Resetting profile list..')
    spawner._profile_list = copy.deepcopy(original_profile_list)

    # pip install jupyterlab-launchpad
    git_creds_command0 = f"mkdir -p /home/jovyan/work/{USER_PERSISTENT_STORAGE_FOLDER}/.git"
    git_creds_command1 = f'git config --global credential.helper "store --file=/home/jovyan/work/{USER_PERSISTENT_STORAGE_FOLDER}/.git/.git-credentials"'
    pip_install_command0 = ("pip uninstall jupyterlab-git -y")
    pip_install_command1 = ("pip install --upgrade jupyterlab==4.2.4 jupyter-archive==3.4.0 jupyterlab-launchpad==1.0.1")
    pip_install_command2 = ("pip install jupyterlab-git==0.50.1 --index-url https://gitlab.nrp-nautilus.io/api/v4/projects/3930/packages/pypi/simple --user")
    pip_install_command3 = (f"pip install ndp-jupyterlab-extension=={NDP_EXT_VERSION} --index-url https://gitlab.nrp-nautilus.io/api/v4/projects/3930/packages/pypi/simple --user")

    # Modify the spawner's start command to include the pip install
    original_cmd = spawner.cmd or ["jupyterhub-singleuser"]
    spawner.cmd = [
        "bash",
        "-c",
        f"{git_creds_command0} "
        f"&& {git_creds_command1} "
        f"&& {pip_install_command0} || true "
        f"&& {pip_install_command1} || true "
        f"&& {pip_install_command2} || true "
        f"&& {pip_install_command3} || true "
        f"&& cd /home/jovyan/work || true "
        f"&& exec {' '.join(original_cmd)}"
    ]

    username = spawner.user.name
    spawner.environment.update({"CKAN_API_URL": CKAN_API_URL})
    spawner.environment.update({"PREKAN_API_URL": PREKAN_API_URL})
    spawner.environment.update({"WORKSPACE_API_URL": WORKSPACE_API_URL})
    spawner.environment.update({"REFRESH_EVERY_SECONDS": str(REFRESH_EVERY_SECONDS)})

    entity_id = spawner.entity_id
    workspace_id = spawner.workspace_id
    entity_name = spawner.entity_name
    
    print(f"Workspace ID: {workspace_id}, Entity ID: {entity_id}, Entity Name: {entity_name}")
    spawner.environment.update({'ENTITY_ID': entity_id or ''})
    spawner.environment.update({'WORKSPACE_ID': workspace_id or ''})
    spawner.environment.update({'ENTITY_NAME': entity_name or ''})

    PVCs = await get_user_pvcs(spawner.access_token)
    if PVCs:
        print(f"USER SHARED {PVCs}")
        folder_names = []
        init_containers = []
        for pvc in PVCs:
            if pvc['entity_id'] == entity_id:
                try:
                    folder_name = pvc['folder_name'].replace(" ", "-")
                    id_short = pvc['subgroup_id'][:5]
                    if folder_name in folder_names:
                        folder_name = folder_name+claim_name[-5:]
                    folder_names.append(folder_name)
                    claim_name = pvc['claim_name']
                    volume_name = pvc['volume_id']
                except:
                    pass
                try:
                    api.read_namespaced_persistent_volume_claim(name=claim_name, namespace=NAMESPACE)
                except ApiException as e:
                    print(e)
                    if e.status == 404:
                        print(f"Creating PVC {claim_name}")
                        pvc_manifest = {
                                'apiVersion': 'v1',
                                'kind': 'PersistentVolumeClaim',
                                'metadata': {'name': claim_name, 'namespace': NAMESPACE},
                                'spec': {
                                    'accessModes': ['ReadWriteMany'],
                                    'resources': {'requests': {'storage': '5Gi'}},
                                    # 'storageClassName': 'rook-cephfs-central'
                                    'storageClassName': STORAGE_CLASS
                                }
                            }
                        api.create_namespaced_persistent_volume_claim(namespace=NAMESPACE, body=pvc_manifest)
                        print(f"PVC {claim_name} created successfully.")
                    else:
                        print(f"Error creating PVC {claim_name}: {e}!!!!!!")
                        raise
                logging.info(f"Adding volume and mount for group {folder_name}")
                init_containers.append({
                        'name': f'set-permissions-{id_short}',
                        'image': 'alpine',
                        'command': ['sh', '-c', f'chmod -R 0777 /shared-storage/{folder_name}'],
                        'volumeMounts': [{
                            'name': volume_name,
                            'mountPath': f'/shared-storage/{folder_name}'
                        }]
                    })
                spawner.extra_volume_mounts.append({
                        'name': volume_name,
                        'mountPath': f'/home/jovyan/work/{folder_name}/'
                    })
                spawner.extra_volumes.append({
                        'name': volume_name,
                        'persistentVolumeClaim': {'claimName': claim_name}
                    })
                
            await update_pvc(spawner.access_token, pvc['pvc_id'])
        spawner.extra_pod_config = spawner.extra_pod_config or {}
        spawner.extra_pod_config.setdefault('initContainers', []).extend(init_containers)

c.JupyterHub.template_paths = ['/etc/jupyterhub/custom']
c.JupyterHub.spawner_class = MySpawner
c.JupyterHub.allow_named_servers = False
c.JupyterHub.authenticator_class = MyAuthenticator
# Append a service with an API token for Prometheus metrics scraping
c.JupyterHub.services.append(
    {
        "name": "service-prometheus", 
        "api_token": os.environ["JUPYTERHUB_METRICS_API_KEY"]
    }
)
# Append a service role to scrape prometheus metrics
c.JupyterHub.load_roles.append(
    {
        "name": "service-metrics-role",
        "description": "access metrics",
        "scopes": [
            "read:metrics",
        ],
        "services": [
            "service-prometheus",
        ],
    }
)

# check only once per day not to block single-user
c.MyAuthenticator.auth_refresh_age = 86300
c.MyAuthenticator.refresh_pre_spawn = True

c.MySpawner.environment = {
    'GIT_PYTHON_REFRESH': 'quiet',
}
c.MySpawner.pre_spawn_hook = pre_spawn_hook
# c.MySpawner.http_timeout = 1200
c.MySpawner.auth_state_hook = auth_state_hook
# c.MySpawner.remove = True  # Remove containers once they are stopped
c.MySpawner.profile_list = copy.deepcopy(original_profile_list)

# Keycloak related URLs 
oauth_authorize_url = f"{OAUTH_BASE}/auth"
oauth_token_url = f"{OAUTH_BASE}/token"
oauth_userdata_url = f"{OAUTH_BASE}/userinfo"

for authenticator in (c.GenericOAuthenticator, c.MyAuthenticator):
    authenticator.authorize_url = oauth_authorize_url
    authenticator.token_url = oauth_token_url
    authenticator.userdata_url = oauth_userdata_url
