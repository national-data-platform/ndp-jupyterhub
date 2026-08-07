# docker
# docker build ./helm/k8s_hub_docker_image -f ./helm/k8s_hub_docker_image/Dockerfile -t gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh:2.0.14 --platform=linux/amd64
# docker push gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh:2.0.14
FROM jupyterhub/k8s-hub:3.0.0

LABEL org.opencontainers.image.version="2.0.14"
LABEL org.opencontainers.image.description="change jhub favicon to ndp"
LABEL org.opencontainers.image.source="https://gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images"

COPY templates/403.html /etc/jupyterhub/custom/403.html
COPY templates/page.html /etc/jupyterhub/custom/page.html`
COPY templates/spawn.html /etc/jupyterhub/custom/spawn.html

COPY pics/ndp_logo.png /usr/local/share/jupyterhub/static/images/ndp_logo.png
COPY pics/ndp-landing-image.png /usr/local/share/jupyterhub/static/images/ndp-landing-image.png
COPY pics/ndp_favicon.ico /usr/local/share/jupyterhub/static/favicon.ico

RUN pip install kubernetes

# In values_test.yaml:
#jupyterhub:
#  hub:
#    image:
#      name: gitlab-registry.nrp-nautilus.io/ndp/ndp-docker-images/jh
#      tag: "2.0.14"