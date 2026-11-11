#!/usr/bin/env bash
# ==============================================================================
# EasyMark - Cloud Container Release & GHCR Publisher
# Builds multi-service Docker images, tags them, and pushes to GitHub Container Registry
# ==============================================================================

set -euo pipefail

REGISTRY=${CONTAINER_REGISTRY:-"ghcr.io"}
OWNER=${REPO_OWNER:-"ganesh7586"}
IMAGE_TAG=${IMAGE_TAG:-"latest"}
PROJECT_NAME="easymark"

echo "=========================================================="
echo " EasyMark Enterprise Cloud Deployment Release Pipeline"
echo " Target Registry: ${REGISTRY}/${OWNER}"
echo " Tag:             ${IMAGE_TAG}"
echo "=========================================================="

# 1. Build and tag AI Service
echo "[1/3] Building AI Engine (${REGISTRY}/${OWNER}/${PROJECT_NAME}-ai:${IMAGE_TAG})..."
docker build \
  -t "${REGISTRY}/${OWNER}/${PROJECT_NAME}-ai:${IMAGE_TAG}" \
  -f ai-service/Dockerfile ai-service

# 2. Build and tag Express Gateway
echo "[2/3] Building Express Gateway (${REGISTRY}/${OWNER}/${PROJECT_NAME}-backend:${IMAGE_TAG})..."
docker build \
  -t "${REGISTRY}/${OWNER}/${PROJECT_NAME}-backend:${IMAGE_TAG}" \
  -f backend/Dockerfile backend

# 3. Build and tag React Frontend
echo "[3/3] Building React Frontend (${REGISTRY}/${OWNER}/${PROJECT_NAME}-frontend:${IMAGE_TAG})..."
docker build \
  -t "${REGISTRY}/${OWNER}/${PROJECT_NAME}-frontend:${IMAGE_TAG}" \
  -f frontend/Dockerfile frontend

echo "----------------------------------------------------------"
echo "All images built successfully!"
echo "To publish images, ensure you are authenticated:"
echo "  echo \$GH_PAT | docker login ghcr.io -u ${OWNER} --password-stdin"
echo "Then push with:"
echo "  docker push ${REGISTRY}/${OWNER}/${PROJECT_NAME}-ai:${IMAGE_TAG}"
echo "  docker push ${REGISTRY}/${OWNER}/${PROJECT_NAME}-backend:${IMAGE_TAG}"
echo "  docker push ${REGISTRY}/${OWNER}/${PROJECT_NAME}-frontend:${IMAGE_TAG}"
echo "=========================================================="
