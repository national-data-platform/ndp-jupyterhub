# docker
# docker build ./jhub/helm/customize -f ./jhub/helm/customize/Dockerfile -t gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh:2.0.3 --platform=linux/amd64
FROM jupyterhub/k8s-hub:2.0.0
#LABEL authors="sergeygurvich"

#USER root

#RUN mkdir -p /templates
#COPY templates/* /templates/
RUN pip install kubernetes

COPY images/ndp_logo.png /usr/local/share/jupyterhub/static/images/ndp_logo.png
COPY images/ndp-landing-image.png /usr/local/share/jupyterhub/static/images/ndp-landing-image.png

#USER jovyan