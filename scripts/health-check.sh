#!/bin/bash

# Health check script for Local Business Intelligence Bot
set -e

# Configuration
ENVIRONMENT=${1:-staging}
BASE_URL=${2:-http://localhost}
TIMEOUT=${3:-30}

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

# Check service health
check_service_health() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}
    
    log_info "Checking ${service_name} health..."
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url" || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        log_info "${service_name} is healthy (HTTP $response)"
        return 0
    else
        log_error "${service_name} is unhealthy (HTTP $response)"
        return 1
    fi
}

# Check detailed service health
check_detailed_health() {
    local service_name=$1
    local url=$2
    
    log_info "Checking ${service_name} detailed health..."
    
    local response=$(curl -s --max-time $TIMEOUT "$url" || echo '{"status":"error"}')
    local status=$(echo "$response" | jq -r '.status // "unknown"')
    
    if [ "$status" = "healthy" ]; then
        log_info "${service_name} detailed health check passed"
        
        # Extract additional metrics if available
        local db_status=$(echo "$response" | jq -r '.checks.database.status // "unknown"')
        local redis_status=$(echo "$response" | jq -r '.checks.redis.status // "unknown"')
        
        log_info "  Database: $db_status"
        log_info "  Redis: $redis_status"
        
        return 0
    else
        log_error "${service_name} detailed health check failed: $status"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
        return 1
    fi
}

# Check database connectivity
check_database() {
    log_info "Checking database connectivity..."
    
    if [ "$ENVIRONMENT" = "kubernetes" ]; then
        # Check via kubectl
        local pod=$(kubectl get pods -l app=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
        if [ -n "$pod" ]; then
            kubectl exec "$pod" -- python -c "
import asyncio
from backend.db.database import get_db
from sqlalchemy import text

async def check_db():
    async for db in get_db():
        result = await db.execute(text('SELECT 1'))
        print('Database connection successful')
        break

asyncio.run(check_db())
" && log_info "Database connectivity check passed" || log_error "Database connectivity check failed"
        else
            log_warn "No backend pods found for database check"
        fi
    else
        # Check via Docker Compose
        docker-compose exec -T backend python -c "
import asyncio
from backend.db.database import get_db
from sqlalchemy import text

async def check_db():
    async for db in get_db():
        result = await db.execute(text('SELECT 1'))
        print('Database connection successful')
        break

asyncio.run(check_db())
" && log_info "Database connectivity check passed" || log_error "Database connectivity check failed"
    fi
}

# Check Redis connectivity
check_redis() {
    log_info "Checking Redis connectivity..."
    
    if [ "$ENVIRONMENT" = "kubernetes" ]; then
        # Check via kubectl
        local pod=$(kubectl get pods -l app=redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
        if [ -n "$pod" ]; then
            kubectl exec "$pod" -- redis-cli ping | grep -q "PONG" && \
                log_info "Redis connectivity check passed" || \
                log_error "Redis connectivity check failed"
        else
            log_warn "No Redis pods found for connectivity check"
        fi
    else
        # Check via Docker Compose
        docker-compose exec -T redis redis-cli ping | grep -q "PONG" && \
            log_info "Redis connectivity check passed" || \
            log_error "Redis connectivity check failed"
    fi
}

# Check AI service configuration
check_ai_services() {
    log_info "Checking AI service configuration..."
    
    local health_url="${BASE_URL}/api/health/detailed"
    local response=$(curl -s --max-time $TIMEOUT "$health_url" || echo '{}')
    
    local ai_status=$(echo "$response" | jq -r '.checks.ai_services.status // "unknown"')
    
    if [ "$ai_status" = "healthy" ]; then
        log_info "AI services configuration check passed"
        return 0
    else
        log_error "AI services configuration check failed: $ai_status"
        local errors=$(echo "$response" | jq -r '.checks.ai_services.errors[]? // empty')
        if [ -n "$errors" ]; then
            echo "$errors"
        fi
        return 1
    fi
}

# Check application metrics
check_metrics() {
    log_info "Checking application metrics..."
    
    local metrics_url="${BASE_URL}/metrics"
    local response=$(curl -s --max-time $TIMEOUT "$metrics_url" || echo '{}')
    
    if echo "$response" | jq -e '.application' > /dev/null 2>&1; then
        local businesses=$(echo "$response" | jq -r '.application.total_businesses // 0')
        local reviews=$(echo "$response" | jq -r '.application.total_reviews // 0')
        local users=$(echo "$response" | jq -r '.application.total_users // 0')
        
        log_info "Application metrics:"
        log_info "  Businesses: $businesses"
        log_info "  Reviews: $reviews"
        log_info "  Users: $users"
        
        return 0
    else
        log_error "Failed to retrieve application metrics"
        return 1
    fi
}

# Check monitoring services
check_monitoring() {
    log_info "Checking monitoring services..."
    
    local prometheus_healthy=false
    local grafana_healthy=false
    
    # Check Prometheus
    if curl -s --max-time $TIMEOUT "${BASE_URL}:9090/-/healthy" > /dev/null 2>&1; then
        log_info "Prometheus is healthy"
        prometheus_healthy=true
    else
        log_warn "Prometheus is not accessible"
    fi
    
    # Check Grafana
    if curl -s --max-time $TIMEOUT "${BASE_URL}:3000/api/health" > /dev/null 2>&1; then
        log_info "Grafana is healthy"
        grafana_healthy=true
    else
        log_warn "Grafana is not accessible"
    fi
    
    if [ "$prometheus_healthy" = true ] || [ "$grafana_healthy" = true ]; then
        return 0
    else
        log_warn "No monitoring services are accessible"
        return 1
    fi
}

# Run load test
run_load_test() {
    log_info "Running basic load test..."
    
    local api_url="${BASE_URL}/api/health"
    local concurrent_requests=10
    local total_requests=100
    
    if command -v ab &> /dev/null; then
        # Use Apache Bench if available
        ab -n $total_requests -c $concurrent_requests "$api_url" > /tmp/load_test.log 2>&1
        
        local success_rate=$(grep "Complete requests" /tmp/load_test.log | awk '{print $3}')
        local avg_time=$(grep "Time per request" /tmp/load_test.log | head -1 | awk '{print $4}')
        
        log_info "Load test completed:"
        log_info "  Successful requests: $success_rate/$total_requests"
        log_info "  Average response time: ${avg_time}ms"
        
        rm -f /tmp/load_test.log
    else
        log_warn "Apache Bench (ab) not available - skipping load test"
    fi
}

# Main health check function
main() {
    log_info "Starting health check for ${ENVIRONMENT} environment..."
    log_info "Base URL: ${BASE_URL}"
    log_info "Timeout: ${TIMEOUT}s"
    
    local failed_checks=0
    
    # Basic health checks
    check_service_health "Frontend" "${BASE_URL}/health" || ((failed_checks++))
    check_service_health "Backend API" "${BASE_URL}/api/health" || ((failed_checks++))
    
    # Detailed health checks
    check_detailed_health "Backend" "${BASE_URL}/api/health/detailed" || ((failed_checks++))
    
    # Infrastructure checks
    check_database || ((failed_checks++))
    check_redis || ((failed_checks++))
    
    # Service configuration checks
    check_ai_services || ((failed_checks++))
    
    # Metrics and monitoring
    check_metrics || ((failed_checks++))
    check_monitoring || true  # Don't fail on monitoring issues
    
    # Performance test
    run_load_test || true  # Don't fail on load test issues
    
    # Summary
    echo ""
    if [ $failed_checks -eq 0 ]; then
        log_info "All health checks passed! ✅"
        exit 0
    else
        log_error "$failed_checks health check(s) failed! ❌"
        exit 1
    fi
}

# Handle script arguments
case "$1" in
    production|staging|development|kubernetes)
        main
        ;;
    --help|-h)
        echo "Usage: $0 [environment] [base_url] [timeout]"
        echo "  environment: production, staging, development, or kubernetes (default: staging)"
        echo "  base_url: Base URL for health checks (default: http://localhost)"
        echo "  timeout: Request timeout in seconds (default: 30)"
        echo ""
        echo "Examples:"
        echo "  $0 staging http://localhost 30"
        echo "  $0 production https://businessbot.yourdomain.com 60"
        echo "  $0 kubernetes http://businessbot-service 30"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        log_error "Invalid environment. Use: production, staging, development, or kubernetes"
        echo "Use --help for more information"
        exit 1
        ;;
esac