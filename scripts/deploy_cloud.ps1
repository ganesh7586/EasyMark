# ==============================================================================
# EasyMark - Cloud Container Release & GHCR Publisher (PowerShell)
# Builds multi-service Docker images, tags them, and pushes to GitHub Container Registry
# ==============================================================================

[CmdletBinding()]
param (
    [string]$Registry = "ghcr.io",
    [string]$Owner = "ganesh7586",
    [string]$ImageTag = "latest",
    [switch]$Push = $false
)

$ErrorActionPreference = "Stop"
$ProjectName = "easymark"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " EasyMark Enterprise Cloud Deployment Release Pipeline" -ForegroundColor Cyan
Write-Host " Target Registry: $Registry/$Owner" -ForegroundColor DarkCyan
Write-Host " Tag:             $ImageTag" -ForegroundColor DarkCyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Build AI Engine
Write-Host "`n[1/3] Building AI Engine ($Registry/$Owner/${ProjectName}-ai:$ImageTag)..." -ForegroundColor Yellow
docker build -t "$Registry/$Owner/${ProjectName}-ai:$ImageTag" -f ai-service/Dockerfile ai-service

# 2. Build Express Gateway
Write-Host "`n[2/3] Building Express Gateway ($Registry/$Owner/${ProjectName}-backend:$ImageTag)..." -ForegroundColor Yellow
docker build -t "$Registry/$Owner/${ProjectName}-backend:$ImageTag" -f backend/Dockerfile backend

# 3. Build React Frontend
Write-Host "`n[3/3] Building React Frontend ($Registry/$Owner/${ProjectName}-frontend:$ImageTag)..." -ForegroundColor Yellow
docker build -t "$Registry/$Owner/${ProjectName}-frontend:$ImageTag" -f frontend/Dockerfile frontend

Write-Host "`nAll EasyMark microservices built successfully!" -ForegroundColor Green

if ($Push) {
    Write-Host "`nPushing container images to $Registry..." -ForegroundColor Magenta
    docker push "$Registry/$Owner/${ProjectName}-ai:$ImageTag"
    docker push "$Registry/$Owner/${ProjectName}-backend:$ImageTag"
    docker push "$Registry/$Owner/${ProjectName}-frontend:$ImageTag"
    Write-Host "All images published to $Registry successfully." -ForegroundColor Green
} else {
    Write-Host "`nPass -Push flag when ready to upload tagged containers to $Registry." -ForegroundColor Gray
}
