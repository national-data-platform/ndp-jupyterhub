# Build and push a multi-platform (amd64, arm64) Docker image using Buildx. 

# Update 'yutianqin/ndp-k8s-hub:<tag>' as needed.
# '--no-cache' is used to ensure that no cached layers are utilized, forcing a fresh build.
# '-f ./Dockerfile' explicitly specifies the Dockerfile to be used.
# The final context for the build is the current directory ('.')

docker buildx build --platform linux/amd64,linux/arm64 -t yutianqin/ndp-k8s-hub:v1 --push --no-cache -f ./Dockerfile .