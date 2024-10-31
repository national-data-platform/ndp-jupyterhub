# docker
# docker build ./helm/customize -f ./helm/customize/Dockerfile -t gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh:2.0.10 --platform=linux/amd64
FROM jupyterhub/k8s-hub:3.0.0
#LABEL authors="sergeygurvich"

#USER root

#RUN mkdir -p /templates
#COPY templates/* /templates/


COPY images/ndp_logo.png /usr/local/share/jupyterhub/static/images/ndp_logo.png
COPY images/ndp-landing-image.png /usr/local/share/jupyterhub/static/images/ndp-landing-image.png

RUN pip install kubernetes
#USER jovyan

# Change version in helm/ndp-hub/charts/jupyterhub/values.yaml:
#   image:
#    name: gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh
#    tag: "2.0.9"