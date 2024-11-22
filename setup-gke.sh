#!/bin/bash

# Set variables
export PROJECT_ID="ce-demo-space"
export CLUSTER_NAME="llm-cluster"
export CLUSTER_LOCATION="us-central1-a"
export K8S_NAMESPACE="datagen"
export KSA_NAME="datagen-ksa"
export GSA_NAME="datagen-gsa"
export OPENAI_API_BASE="http://vllm-service:8000/v1"

# Get the Cloud Build service account
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Grant Container Registry access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/storage.admin"

# Grant GKE deploy access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/container.developer"

# Create GKE cluster with GPU node pool
gcloud container clusters create llm-cluster \
    --zone us-central1-a \
    --machine-type n1-standard-8 \
    --num-nodes 1

# Add GPU node pool
gcloud container clusters update llm-cluster \
    --zone us-central1-a \
    --update-addons=GpuDriver=ENABLED

gcloud container node-pools create gpu-pool \
    --cluster llm-cluster \
    --zone us-central1-a \
    --machine-type g2-standard-16 \
    --accelerator type=nvidia-l4,count=1,gpu-driver-version=latest \
    --num-nodes 1 \
    --node-taints="nvidia.com/gpu=present:NoSchedule"

# Create Google Service Account
gcloud iam service-accounts create $GSA_NAME \
    --project=$PROJECT_ID

# Grant Storage permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$GSA_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Enable workload identity on the cluster if not already enabled
gcloud container clusters update $CLUSTER_NAME \
    --location=$CLUSTER_LOCATION \
    --workload-pool=$PROJECT_ID.svc.id.goog

# Get Kubernetes Credentials
gcloud container clusters get-credentials $CLUSTER_NAME \
    --zone=$CLUSTER_LOCATION

# Create namespace quota
kubectl apply -f k8s/namespace-quota.yaml

# Create Kubernetes Service Account
kubectl create serviceaccount $KSA_NAME \
    --namespace=$K8S_NAMESPACE

# Allow KSA to impersonate GSA
gcloud iam service-accounts add-iam-policy-binding \
    $GSA_NAME@$PROJECT_ID.iam.gserviceaccount.com \
    --project=$PROJECT_ID \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:$PROJECT_ID.svc.id.goog[$K8S_NAMESPACE/$KSA_NAME]"

# Annotate KSA
kubectl annotate serviceaccount $KSA_NAME \
    --namespace=$K8S_NAMESPACE \
    iam.gke.io/gcp-service-account=$GSA_NAME@$PROJECT_ID.iam.gserviceaccount.com

# Create secrets
kubectl create secret generic api-config \
    --namespace=$K8S_NAMESPACE \
    --from-literal=openai-api-base=$OPENAI_API_BASE

kubectl create secret generic gcp-config \
    --namespace=$K8S_NAMESPACE \
    --from-literal=project-id=$PROJECT_ID

kubectl create secret generic hugging-face-secrets \
    --namespace=$K8S_NAMESPACE \
    --from-env-file=.secrets

# Apply vLLM resources
kubectl apply -f k8s/vllm-daemonset.yaml
kubectl apply -f k8s/vllm-service.yaml
