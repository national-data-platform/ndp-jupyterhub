#!/bin/bash

# Namespace where JupyterHub is running (test namespace)
NAMESPACE=ndp-test

for pod in $(kubectl get pods -n $NAMESPACE --selector=component=singleuser-server -o jsonpath='{.items[*].metadata.name}')
do
    echo "Checking pod: $pod"

    # Fetch logs once
    logs=$(kubectl logs $pod -n $NAMESPACE)
    
   echo "$logs" | grep -q "HTTP 403: Forbidden"
   exit_status_1=$?
#    echo "$exit_status_1"

   echo "$logs" | grep -q "Error notifying Hub of activity"
   exit_status_2=$?
#    echo "$exit_status_2"
   
   if [ $exit_status_1 -eq 0 ] && [ $exit_status_2 -eq 0 ]; then
      echo "Idle pod detected - $pod. Terminating pod."
      kubectl delete pod $pod -n $NAMESPACE
   else
      echo "$pod is active."
   fi
done