# Makefile for managing JupyterHub deployment on Kubernetes using Helm
#
# This Makefile provides targets to:
# - Update Helm chart dependencies
# - Create and delete Kubernetes namespaces and secrets
# - Deploy, uninstall, and check the status of the JupyterHub Helm release
# - Retrieve Ingress information for accessing JupyterHub

# Configuration
CONFIG_FILE ?= config.mk
-include $(CONFIG_FILE)

# Kubernetes context
DEFAULT_KUBE_CONTEXT := $(shell kubectl config current-context 2>/dev/null)
ifeq ($(strip $(KUBE_CONTEXT)),)
KUBE_CONTEXT := $(if $(DEFAULT_KUBE_CONTEXT),$(DEFAULT_KUBE_CONTEXT),microk8s)
endif
KUBECTL := kubectl $(if $(KUBE_CONTEXT),--context $(KUBE_CONTEXT))

# Helm release and namespace configuration
HELM_RELEASE ?= ndp-jhub # Name of the Helm release
NAMESPACE ?= ndp-jhub

# Define values files and spawner config
VALUES_FILE := ndp-hub/values.yaml
SITE_VALUES_FILE ?= ndp-hub/site-values.yaml
SPAWNER_FILE := ndp-hub/spawner.py

# Overrides values from site-values.yaml
VALUES_ARGS := -f $(VALUES_FILE)
ifneq ($(wildcard $(SITE_VALUES_FILE)),)
VALUES_ARGS += -f $(SITE_VALUES_FILE)
endif

# Embed spawner config file into jhub helm chart values
SPAWNER_SET_ARG := --set-file jupyterhub.hub.extraConfig.default\\\.py=$(SPAWNER_FILE)


.PHONY: update create-ns create-jhub-secret delete-jhub-secret deploy uninstall status get-ingress

# Updates Helm chart dependencies by downloading them into the charts/ directory
update:
	helm dependency update ndp-hub

# Create namespace if it does not exist
create-ns:
	@echo "Creating namespace $(NAMESPACE) if it does not exist..."
	$(KUBECTL) get namespace $(NAMESPACE) >/dev/null 2>&1 || $(KUBECTL) create namespace $(NAMESPACE)

# Create a kubernetes secret for keycloak client_id and client_secret
create-jhub-secret: create-ns
	@echo "Creating JupyterHub secret in namespace $(NAMESPACE)..."
	$(KUBECTL) create secret generic jupyterhub-secret \
		--from-file=values.yaml=ndp-hub/jupyterhub_secret.yaml \
		--namespace $(NAMESPACE)

# Delete the kubernetes secret for keycloak client_id and client_secret
delete-jhub-secret:
	@echo "Deleting JupyterHub secret in namespace $(NAMESPACE)..."
	$(KUBECTL) delete secret jupyterhub-secret --namespace $(NAMESPACE) || true

# Deploy the Helm chart
deploy:
	@echo "Deploying $(HELM_RELEASE) to $(NAMESPACE)..."
	helm upgrade --cleanup-on-fail \
		--install $(HELM_RELEASE) ./ndp-hub \
		--kube-context $(KUBE_CONTEXT) \
		--namespace $(NAMESPACE) \
		--create-namespace \
		$(VALUES_ARGS) \
		$(SPAWNER_SET_ARG)

# Uninstall the Helm chart
uninstall:
	@echo "Uninstalling $(HELM_RELEASE) from $(NAMESPACE)..."
	helm uninstall $(HELM_RELEASE) \
		--kube-context $(KUBE_CONTEXT) \
		--namespace $(NAMESPACE)

# Check the status of the Helm release
status:
	@echo "Checking status of $(HELM_RELEASE) in $(NAMESPACE)..."
	helm status $(HELM_RELEASE) \
		--kube-context $(KUBE_CONTEXT) \
		--namespace $(NAMESPACE)

# Get the Ingress IP for accessing JupyterHub
get-ingress:
	@echo "Fetching Ingress details for $(HELM_RELEASE) ..."
	@$(KUBECTL) get ingress -n $(NAMESPACE) -o wide
