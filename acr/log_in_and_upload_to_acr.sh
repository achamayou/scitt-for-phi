# Source environment for the test ACR instance
source ./acr_env
# Log in to Azure CLI
az login --use-device-code
# Log in to demo ACR
az acr login -n $ACR_NAME

# Upload the In-Toto Statement to ACR
oras push $IMAGE --artifact-type in-toto/model-manifest ../model-manifest.json:application/vnd.in-toto+json
# Attach the SCIT Transparent Statement
oras attach $IMAGE --artifact-type scitt/transparent-statement ../2ts-statement.scitt:application/scitt-statement+cose
# Discover the Manifest for the now uploaded In-Toto Statement
oras manifest fetch --pretty $IMAGE
# Discover the SCITT Transparent Statement
oras discover --format tree $IMAGE

# Fetch the In-Toto Statement
mkdir -p download
oras pull $IMAGE --output download --allow-path-traversal
# Fetch the SCITT Transparent Statement
export SCITT_STATEMENT=$(oras discover --format json $IMAGE | jq -r .manifests[0].reference)
oras pull $SCITT_STATEMENT --output download --allow-path-traversal