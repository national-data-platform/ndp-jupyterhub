# COMPOSE_FILE=docker-compose.dev.yaml

# First python3/python on PATH that is Python 3; override with `make PYTHON=/path/to/python`
PYTHON ?= $(or $(shell \
    for p in python3 python; do \
      $$p -c 'import sys; sys.exit(sys.version_info[0] < 3)' >/dev/null 2>&1 \
        && { echo $$p; break; }; \
    done), \
  $(error Python 3 not found on PATH. Please install Python 3 \
    (https://www.python.org/downloads/) and re-run make))

default: deploy-test

deploy-test:
	 cd ndp-hub && $(PYTHON) generate_values.py --env test
	 helm upgrade --cleanup-on-fail --install ndp-hub ndp-hub --kube-context nautilus --namespace ndp-test --values ndp-hub/_values_test.yaml
deploy-local:
	 cd ndp-hub && $(PYTHON) generate_values.py --env local
	 helm upgrade --cleanup-on-fail --install ndp-hub ndp-hub --kube-context kind-jhub-local --namespace ndp-test-local --values ndp-hub/_values_local.yaml
deploy-staging:
	 cd ndp-hub && $(PYTHON) generate_values.py --env staging
	 helm upgrade --cleanup-on-fail --install ndp-hub ndp-hub --kube-context nautilus --namespace ndp-staging --values ndp-hub/_values_staging.yaml
deploy-prod:
	 cd ndp-hub && $(PYTHON) generate_values.py --env prod
	 helm upgrade --cleanup-on-fail --install ndp-hub ndp-hub --kube-context nautilus --namespace ndp --values ndp-hub/_values_prod.yaml

# Local KinD cluster (jhub-local / namespace ndp-test-local): `make kind-up`, then open http://localhost:8082
LOCAL_SECRET_FILE ?= ndp-hub/jupyterhub_secret_local.yaml

.PHONY: kind-up kind-cluster kind-secrets kind-down

kind-up kind-cluster kind-secrets deploy-local kind-down: export KUBECONFIG := $(CURDIR)/config-kind

kind-up: kind-cluster kind-secrets deploy-local
	@echo "NDP JupyterHub is running at http://localhost:8082"
	@echo "To access the k8s kind cluster, run: export KUBECONFIG=$(CURDIR)/config-kind"

kind-cluster:
	kind get clusters | grep -qx jhub-local || kind create cluster --config kind-config.yaml
	kubectl config set-context kind-jhub-local --namespace ndp-test-local

kind-secrets:
	kubectl --context kind-jhub-local get namespace ndp-test-local >/dev/null 2>&1 || kubectl --context kind-jhub-local create namespace ndp-test-local
	kubectl --context kind-jhub-local -n ndp-test-local create secret generic jupyterhub-secret --from-file=values.yaml=$(LOCAL_SECRET_FILE) --dry-run=client -o yaml | kubectl --context kind-jhub-local apply -f -
	kubectl --context kind-jhub-local -n ndp-test-local get secret jupyterhub-metrics-secret >/dev/null 2>&1 || \
		kubectl --context kind-jhub-local -n ndp-test-local create secret generic jupyterhub-metrics-secret --from-literal=metrics-api-key=$$(openssl rand -hex 32)

kind-down:
	kind delete cluster --name jhub-local
