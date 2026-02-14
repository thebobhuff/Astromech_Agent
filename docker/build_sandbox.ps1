# Check if Docker is running
docker ps > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Build the image
Write-Host "Building Astromech Sandbox Image..." -ForegroundColor Cyan
docker build -t astromech-sandbox:latest -f docker/Dockerfile.sandbox .

if ($LASTEXITCODE -eq 0) {
    Write-Host "Sandbox Image Built Successfully!" -ForegroundColor Green
    Write-Host "To enable sandbox mode:"
    Write-Host "1. Create or update .env file with: SANDBOX_ENABLED=True"
    Write-Host "2. Restart the backend server."
} else {
    Write-Host "Build Failed." -ForegroundColor Red
}
