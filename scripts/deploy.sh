#!/bin/bash

# Production deployment script for Local Business Intelligence Bot
set -e

# Configuration
ENVIRONMENT=${1:-staging}
REGISTRY="ghcr.io"
IMAGE_NAME="your-org/businessbot"
VERSION=${2:-latest}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check if helm is installed (optional)
    if ! command -v helm &> /dev/null; then
        log_warn "Helm is not installed - some features may not be available"
    fi
    
    log_info "Prerequisites check completed"
}

# Build and push Docker images
build_and_push_images() {
    log_info "Building and pushing Docker images..."
    
    # Build backend image
    log_info "Building backend image..."
    docker build -t ${REGISTRY}/${IMAGE_NAME}-backend:${VERSION} -f docker/backend/Dockerfile .
    docker push ${REGISTRY}/${IMAGE_NAME}-backend:${VERSION}
    
    # Build frontend image
    log_info "Building frontend image..."
    docker build -t ${REGISTRY}/${IMAGE_NAME}-frontend:${VERSION} -f docker/frontend/Dockerfile .
    docker push ${REGISTRY}/${IMAGE_NAME}-frontend:${VERSION}
    
    log_info "Images built and pushed successfully"
}

# Deploy to Kubernetes
deploy_to_kubernetes() {
    log_info "Deploying to Kubernetes (${ENVIRONMENT})..."
    
    # Set kubectl context based on environment
    if [ "$ENVIRONMENT" = "production" ]; then
        kubectl config use-context production-cluster
        NAMESPACE="businessbot-prod"
    else
        kubectl config use-context staging-cluster
        NAMESPACE="businessbot-staging"
    fi
    
    # Create namespace if it doesn't exist
    kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply Kubernetes manifests
    if [ "$ENVIRONMENT" = "production" ]; then
        kubectl apply -f k8s/production-deployment.yaml
    else
        kubectl apply -f k8s/staging-deployment.yaml
    fi
    
    # Update image tags
    kubectl set image deployment/backend backend=${REGISTRY}/${IMAGE_NAME}-backend:${VERSION} -n ${NAMESPACE}
    kubectl set image deployment/frontend frontend=${REGISTRY}/${IMAGE_NAME}-frontend:${VERSION} -n ${NAMESPACE}
    kubectl set image deployment/worker worker=${REGISTRY}/${IMAGE_NAME}-backend:${VERSION} -n ${NAMESPACE}
    
    # Wait for rollout to complete
    log_info "Waiting for deployment to complete..."
    kubectl rollout status deployment/backend -n ${NAMESPACE} --timeout=600s
    kubectl rollout status deployment/frontend -n ${NAMESPACE} --timeout=600s
    kubectl rollout status deployment/worker -n ${NAMESPACE} --timeout=600s
    
    log_info "Kubernetes deployment completed"
}

# Deploy with Docker Compose (for local/staging)
deploy_with_compose() {
    log_info "Deploying with Docker Compose..."
    
    # Set environment variables
    export BACKEND_IMAGE=${REGISTRY}/${IMAGE_NAME}-backend:${VERSION}
    export FRONTEND_IMAGE=${REGISTRY}/${IMAGE_NAME}-frontend:${VERSION}
    
    # Deploy based on environment
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml up -d
    else
        docker-compose -f docker-compose.yml up -d
    fi
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    check_service_health
    
    log_info "Docker Compose deployment completed"
}

# Check service health
check_service_health() {
    log_info "Checking service health..."
    
    # Check backend health
    for i in {1..30}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            log_info "Backend service is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Backend service health check failed"
            exit 1
        fi
        sleep 10
    done
    
    # Check frontend health
    for i in {1..30}; do
        if curl -f http://localhost:80/health > /dev/null 2>&1; then
            log_info "Frontend service is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Frontend service health check failed"
            exit 1
        fi
        sleep 10
    done
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        # Run migrations in Kubernetes
        kubectl run migration-job --image=${REGISTRY}/${IMAGE_NAME}-backend:${VERSION} \
            --restart=Never --rm -i --tty \
            --env="DATABASE_URL=${DATABASE_URL}" \
            -- alembic upgrade head
    else
        # Run migrations with Docker Compose
        docker-compose exec backend alembic upgrade head
    fi
    
    log_info "Database migrations completed"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring..."
    
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        # Deploy monitoring stack with Helm
        if command -v helm &> /dev/null; then
            # Add Prometheus Helm repository
            helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
            helm repo update
            
            # Install Prometheus stack
            helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
                --namespace monitoring --create-namespace \
                --values monitoring/prometheus-values.yaml
        else
            log_warn "Helm not available - skipping monitoring setup"
        fi
    else
        # Monitoring is included in docker-compose.prod.yml
        log_info "Monitoring services started with Docker Compose"
    fi
    
    log_info "Monitoring setup completed"
}

# Cleanup old deployments
cleanup_old_deployments() {
    log_info "Cleaning up old deployments..."
    
    # Remove old Docker images
    docker image prune -f
    
    # Remove unused volumes
    docker volume prune -f
    
    log_info "Cleanup completed"
}

# Main deployment function
main() {
    log_info "Starting deployment to ${ENVIRONMENT} environment..."
    
    # Determine deployment type
    DEPLOYMENT_TYPE=${DEPLOYMENT_TYPE:-docker-compose}
    if [ "$ENVIRONMENT" = "production" ] && command -v kubectl &> /dev/null; then
        DEPLOYMENT_TYPE="kubernetes"
    fi
    
    log_info "Using deployment type: ${DEPLOYMENT_TYPE}"
    
    # Run deployment steps
    check_prerequisites
    build_and_push_images
    
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        deploy_to_kubernetes
    else
        deploy_with_compose
    fi
    
    run_migrations
    setup_monitoring
    cleanup_old_deployments
    
    log_info "Deployment completed successfully!"
    log_info "Application should be available at:"
    
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        log_info "  - Frontend: https://businessbot.yourdomain.com"
        log_info "  - API: https://businessbot.yourdomain.com/api"
        log_info "  - Monitoring: https://monitoring.yourdomain.com"
    else
        log_info "  - Frontend: http://localhost:80"
        log_info "  - API: http://localhost:8000"
        log_info "  - Monitoring: http://localhost:3000"
    fi
}

# Handle script arguments
case "$1" in
    production|staging|development)
        main
        ;;
    --help|-h)
        echo "Usage: $0 [environment] [version]"
        echo "  environment: production, staging, or development (default: staging)"
        echo "  version: Docker image version tag (default: latest)"
        echo ""
        echo "Environment variables:"
        echo "  DEPLOYMENT_TYPE: kubernetes or docker-compose"
        echo "  DATABASE_URL: Database connection string"
        exit 0
        ;;
    *)
        log_error "Invalid environment. Use: production, staging, or development"
        echo "Use --help for more information"
        exit 1
        ;;
esac