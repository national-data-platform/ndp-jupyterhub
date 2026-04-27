#!/bin/bash
PVC_DIR=$(ls /home/jovyan/work | grep "User-Persistent-Storage" | head -1)
PERSIST_DIR="/home/jovyan/work/${PVC_DIR}/.code-server"
mkdir -p "$PERSIST_DIR"
rm -rf /home/jovyan/.local/share/code-server
ln -sf "$PERSIST_DIR" /home/jovyan/.local/share/code-server
chown -R jovyan:users "$PERSIST_DIR" 2>/dev/null || true
chown -h jovyan:users /home/jovyan/.local/share/code-server 2>/dev/null || true
exec /opt/conda/bin/jupyterhub-singleuser-orig "$@"