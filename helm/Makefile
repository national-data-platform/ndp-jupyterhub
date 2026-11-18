# NDP JupyterHub deploys: shared ndp-hub/values.yaml + ndp-hub/config/<env>.yaml + ndp-hub/spawner.py
# prod deploys only from main (in sync with origin/main).

DEPLOY = helm upgrade --cleanup-on-fail --install ndp-hub ndp-hub \
	--set-file 'jupyterhub.hub.extraConfig.default\.py=ndp-hub/spawner.py' \
	--description "$@ from $$(git rev-parse --abbrev-ref HEAD)@$$(git rev-parse --short HEAD)"

default: deploy-test

deploy-test:
	$(DEPLOY) --kube-context nautilus --namespace ndp-test -f ndp-hub/config/test.yaml
deploy-staging:
	$(DEPLOY) --kube-context nautilus --namespace ndp-staging -f ndp-hub/config/staging.yaml
deploy-prod: check-main
	$(DEPLOY) --kube-context nautilus --namespace ndp -f ndp-hub/config/prod.yaml
deploy-local:
	$(DEPLOY) --kube-context kind-jhub-local --namespace ndp-test-local -f ndp-hub/config/local.yaml

# prod: must be on main and in sync with origin/main; warn on uncommitted changes
check-main:
	@test "$$(git rev-parse --abbrev-ref HEAD)" = main || { echo "ERROR: deploy prod from main only"; exit 1; }
	@git fetch -q origin main && test "$$(git rev-parse HEAD)" = "$$(git rev-parse origin/main)" || \
		{ echo "ERROR: local main is not in sync with origin/main"; exit 1; }
	@git diff --quiet HEAD || echo "WARNING: deploying uncommitted changes"

.PHONY: default deploy-test deploy-staging deploy-prod deploy-local check-main

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
