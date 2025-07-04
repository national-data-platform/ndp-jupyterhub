# Makefile for managing JupyterHub deployment on Kubernetes using Helm
#
# This Makefile provides targets to:
# - Update Helm chart dependencies
# - Create and delete Kubernetes namespaces and secrets
# - Generate configuration files
# - Deploy, uninstall, and check the status of the JupyterHub Helm release
# - Retrieve Ingress information for accessing JupyterHub
#
# Variables are defined for the Helm release name, Kubernetes context, namespace, and values file.
# Each target automates a specific part of the deployment workflow.


# Variables
HELM_RELEASE := ndp-jhub # Name of the Helm release
KUBE_CONTEXT := arn:aws:eks:us-west-2:<AWS_ACCOUNT_ID>:cluster/<CLUSTER_NAME> # Set your Kubernetes cluster context here. The provided value is a template for an AWS EKS context
NAMESPACE := jupyterhub
VALUES_FILE := config.yaml

# Updates Helm chart dependencies by downloading them into the charts/ directory
.PHONY: update-dependency
update-dependency:
	helm dependency update ndp-hub

# Create namespace if it does not exist
.PHONY: create-namespace
create-namespace:
	@echo "Creating namespace $(NAMESPACE) if it does not exist..."
	kubectl get namespace $(NAMESPACE) >/dev/null 2>&1 || kubectl create namespace $(NAMESPACE)

# Create a kubernetes secret for keycloak client_id and client_secret
.PHONY: create-jhub-secret
create-jhub-secret: create-namespace
	@echo "Creating JupyterHub secret in namespace $(NAMESPACE)..."
	kubectl create secret generic jupyterhub-secret \
		--from-file=values.yaml=ndp-hub/jupyterhub_secret.yaml \
		--namespace $(NAMESPACE)

# Delete the kubernetes secret for keycloak client_id and client_secret
.PHONY: delete-jhub-secret
delete-jhub-secret:
	@echo "Deleting JupyterHub secret in namespace $(NAMESPACE)..."
	kubectl delete secret jupyterhub-secret --namespace $(NAMESPACE) || true

# Generate the config.yaml file by embedding spawner.py into values.yaml
.PHONY: generate
generate:
	@echo "Generating $(VALUES_FILE)..."
	cd ndp-hub && python generate_config.py

# Clean up generated config.yaml files
.PHONY: clean
clean:
	@echo "Cleaning up generated files..."
	cd ndp-hub && rm -f $(VALUES_FILE)

# Deploy the Helm chart
.PHONY: deploy
deploy:
	@echo "Deploying $(HELM_RELEASE) to $(NAMESPACE)..."
	helm upgrade --cleanup-on-fail \
		--install $(HELM_RELEASE) ./ndp-hub \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--values ndp-hub/$(VALUES_FILE)

# Uninstall the Helm chart
.PHONY: uninstall
uninstall:
	@echo "Uninstalling $(HELM_RELEASE) from $(NAMESPACE)..."
	helm uninstall $(HELM_RELEASE) \
		--kube-context $(KUBE_CONTEXT) \
		--namespace $(NAMESPACE)

# Check the status of the Helm release
.PHONY: status
status:
	@echo "Checking status of $(HELM_RELEASE) in $(NAMESPACE)..."
	helm status $(HELM_RELEASE) \
		--kube-context $(KUBE_CONTEXT) \
		--namespace $(NAMESPACE)

# Get the Ingress IP for accessing JupyterHub
.PHONY: get-ingress
get-ingress:
	@echo "Fetching Ingress details for $(HELM_RELEASE) ..."
	@kubectl get ingress -n $(NAMESPACE) -o wide
