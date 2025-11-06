# Deployment Guide

This guide covers the production deployment and monitoring setup for the Local Business Intelligence Bot.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Monitoring Setup](#monitoring-setup)
6. [Health Checks](#health-checks)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)

## Prerequisites

### System Requirements

- **CPU**: Minimum 4 cores, recommended 8+ cores
- **Memory**: Minimum 8GB RAM, recommended 16GB+ RAM
- **Storage**: Minimum 100GB SSD, recommended 500GB+ SSD
- **Network**: Stable internet connection with sufficient bandwidth for AI API calls

### Software Requirements

- Docker 24.0+ and Docker Compose 2.0+
- Kubernetes 1.25+ (for K8s deployment)
- kubectl configured with cluster access
- Helm 3.0+ (optional, for monitoring stack)
- Git for source code management

### External Services

- **OpenAI API**: GPT-5 Nano access for review classification
- **Anthropic API**: Claude 3.5 Haiku access for business advisory
- **Google Places API**: For review import functionality
- **SMTP Server**: For email notifications
- **SSL Certificates**: For HTTPS in production

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/local-business-intelligence-bot.git
cd local-business-intelligence-bot
```

### 2. Configure Environment Variables

Copy the production environment template:

```bash
cp .env.production .env
```

Edit `.env` with your actual values:

```bash
# Required: Update these values
POSTGRES_PASSWORD=your-secure-password-here
REDIS_PASSWORD=your-redis-password-here
JWT_SECRET_KEY=your-jwt-secret-key-here
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GOOGLE_PLACES_API_KEY=your-google-places-api-key-here

# Optional: Configure based on your setup
FRONTEND_URL=https://businessbot.yourdomain.com
BACKEND_URL=https://businessbot.yourdomain.com/api
SMTP_HOST=smtp.yourdomain.com
SMTP_USERNAME=noreply@yourdomain.com
SMTP_PASSWORD=your-smtp-password-here
```

### 3. Generate Secure Keys

```bash
# Generate JWT secret key
openssl rand -hex 32

# Generate backup encryption key
openssl rand -hex 32
```

## Docker Deployment

### Quick Start

```bash
# Make deployment script executable
chmod +x scripts/deploy.sh

# Deploy to staging
./scripts/deploy.sh staging

# Deploy to production
./scripts/deploy.sh production
```

### Manual Docker Compose Deployment

```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Run database migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Create admin user
docker-compose -f docker-compose.prod.yml exec backend python backend/create_admin.py
```

### Service URLs (Docker Compose)

- **Frontend**: http://localhost:80
- **Backend API**: http://localhost:8000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Database**: localhost:5432
- **Redis**: localhost:6379

## Kubernetes Deployment

### 1. Prepare Cluster

```bash
# Create namespace
kubectl create namespace businessbot-prod

# Create secrets (base64 encode your values)
kubectl create secret generic businessbot-secrets \
  --from-literal=POSTGRES_PASSWORD=your-password \
  --from-literal=REDIS_PASSWORD=your-password \
  --from-literal=JWT_SECRET_KEY=your-secret \
  --from-literal=OPENAI_API_KEY=your-key \
  --from-literal=ANTHROPIC_API_KEY=your-key \
  --from-literal=GOOGLE_PLACES_API_KEY=your-key \
  -n businessbot-prod
```

### 2. Deploy Application

```bash
# Deploy all components
kubectl apply -f k8s/production-deployment.yaml

# Check deployment status
kubectl get pods -n businessbot-prod
kubectl get services -n businessbot-prod

# Check logs
kubectl logs -f deployment/backend -n businessbot-prod
```

### 3. Configure Ingress

Update the ingress configuration in `k8s/production-deployment.yaml`:

```yaml
spec:
  tls:
  - hosts:
    - businessbot.yourdomain.com
    secretName: businessbot-tls
  rules:
  - host: businessbot.yourdomain.com
```

### 4. SSL Certificate Setup

```bash
# Install cert-manager (if not already installed)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@yourdomain.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

## Monitoring Setup

### Prometheus and Grafana

The monitoring stack is automatically deployed with the application. Access:

- **Prometheus**: http://your-domain:9090
- **Grafana**: http://your-domain:3000

### Grafana Configuration

1. Login with admin/admin (change password on first login)
2. Import dashboards from `monitoring/grafana/dashboards/`
3. Configure alert channels for notifications

### Custom Metrics

The application exposes custom metrics at `/metrics`:

- `businessbot_requests_total`: Total HTTP requests
- `businessbot_request_duration_seconds`: Request duration
- `businessbot_ai_api_calls_total`: AI API calls count
- `businessbot_ai_api_cost_total`: AI API costs
- `businessbot_reviews_processed_total`: Reviews processed
- `businessbot_errors_total`: Application errors

### Alerting Rules

Key alerts configured in `monitoring/alert_rules.yml`:

- Application down
- High response time (>2s)
- High error rate (>10%)
- Database connectivity issues
- High AI costs
- Review processing backlog

## Health Checks

### Automated Health Checks

```bash
# Run comprehensive health check
./scripts/health-check.sh production https://businessbot.yourdomain.com

# Check specific environment
./scripts/health-check.sh staging http://localhost
```

### Manual Health Checks

```bash
# Basic health check
curl https://businessbot.yourdomain.com/health

# Detailed health check
curl https://businessbot.yourdomain.com/api/health/detailed

# Metrics endpoint
curl https://businessbot.yourdomain.com/metrics
```

### Kubernetes Health Checks

```bash
# Check pod health
kubectl get pods -n businessbot-prod
kubectl describe pod <pod-name> -n businessbot-prod

# Check service endpoints
kubectl get endpoints -n businessbot-prod

# Check ingress
kubectl get ingress -n businessbot-prod
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues

```bash
# Check database pod
kubectl logs -f deployment/postgres -n businessbot-prod

# Test database connection
kubectl exec -it deployment/backend -n businessbot-prod -- python -c "
from backend.db.database import get_db
import asyncio
async def test():
    async for db in get_db():
        print('Database connected')
        break
asyncio.run(test())
"
```

#### 2. AI API Issues

```bash
# Check API key configuration
kubectl get secret businessbot-secrets -n businessbot-prod -o yaml

# Test AI service
curl -X POST https://businessbot.yourdomain.com/api/reviews/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "Great food!", "business_id": "test"}'
```

#### 3. High Memory Usage

```bash
# Check resource usage
kubectl top pods -n businessbot-prod

# Scale up if needed
kubectl scale deployment backend --replicas=3 -n businessbot-prod
```

#### 4. SSL Certificate Issues

```bash
# Check certificate status
kubectl describe certificate businessbot-tls -n businessbot-prod

# Check cert-manager logs
kubectl logs -f deployment/cert-manager -n cert-manager
```

### Log Analysis

```bash
# Application logs
kubectl logs -f deployment/backend -n businessbot-prod

# Nginx logs
kubectl logs -f deployment/frontend -n businessbot-prod

# Database logs
kubectl logs -f deployment/postgres -n businessbot-prod

# Aggregate logs with Loki
curl -G -s "http://loki:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="businessbot-backend"}' \
  --data-urlencode 'start=2024-01-01T00:00:00Z' \
  --data-urlencode 'end=2024-01-01T23:59:59Z'
```

## Maintenance

### Regular Tasks

#### 1. Database Maintenance

```bash
# Run database vacuum (weekly)
kubectl exec -it deployment/postgres -n businessbot-prod -- \
  psql -U businessbot -d businessbot -c "VACUUM ANALYZE;"

# Check database size
kubectl exec -it deployment/postgres -n businessbot-prod -- \
  psql -U businessbot -d businessbot -c "
  SELECT pg_size_pretty(pg_database_size('businessbot'));"
```

#### 2. Backup Verification

```bash
# Test backup restoration
./scripts/test-backup-restore.sh

# Check backup integrity
kubectl exec -it deployment/backend -n businessbot-prod -- \
  python -m backend.services.backup_service verify
```

#### 3. Security Updates

```bash
# Update base images
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull nginx:alpine

# Rebuild and deploy
./scripts/deploy.sh production latest
```

#### 4. Performance Optimization

```bash
# Analyze slow queries
kubectl exec -it deployment/postgres -n businessbot-prod -- \
  psql -U businessbot -d businessbot -c "
  SELECT query, mean_time, calls 
  FROM pg_stat_statements 
  ORDER BY mean_time DESC LIMIT 10;"

# Clear Redis cache if needed
kubectl exec -it deployment/redis -n businessbot-prod -- \
  redis-cli FLUSHDB
```

### Scaling

#### Horizontal Scaling

```bash
# Scale backend
kubectl scale deployment backend --replicas=5 -n businessbot-prod

# Scale frontend
kubectl scale deployment frontend --replicas=3 -n businessbot-prod

# Auto-scaling is configured via HPA
kubectl get hpa -n businessbot-prod
```

#### Vertical Scaling

Update resource limits in `k8s/production-deployment.yaml`:

```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### Monitoring and Alerting

#### 1. Set Up Alert Channels

Configure Grafana alert channels:
- Email notifications
- Slack integration
- PagerDuty for critical alerts

#### 2. Custom Dashboards

Create business-specific dashboards:
- Review processing metrics
- AI cost tracking
- User activity patterns
- System performance

#### 3. Log Retention

Configure log retention policies:
- Application logs: 30 days
- Access logs: 90 days
- Error logs: 1 year
- Audit logs: 7 years (GDPR compliance)

### Disaster Recovery

#### 1. Backup Strategy

- **Database**: Daily automated backups with 30-day retention
- **Application data**: Weekly full backups
- **Configuration**: Version controlled in Git
- **Secrets**: Encrypted and stored securely

#### 2. Recovery Procedures

```bash
# Restore from backup
kubectl exec -it deployment/backend -n businessbot-prod -- \
  python -m backend.services.backup_service restore --backup-id=<backup-id>

# Verify data integrity
./scripts/health-check.sh production https://businessbot.yourdomain.com
```

#### 3. Failover Testing

- Monthly failover tests
- Document recovery time objectives (RTO: 4 hours)
- Document recovery point objectives (RPO: 1 hour)

## Security Considerations

### 1. Network Security

- Use private networks for internal communication
- Implement network policies in Kubernetes
- Regular security scans with tools like Trivy

### 2. Secret Management

- Rotate secrets regularly (quarterly)
- Use Kubernetes secrets or external secret managers
- Never commit secrets to version control

### 3. Access Control

- Implement RBAC for Kubernetes access
- Use service accounts with minimal permissions
- Regular access reviews

### 4. Compliance

- GDPR compliance monitoring
- Regular security audits
- Data retention policy enforcement

## Support and Documentation

- **Application Logs**: Available in Grafana/Loki
- **Metrics**: Prometheus + Grafana dashboards
- **Health Checks**: Automated monitoring and alerting
- **Documentation**: Keep this guide updated with changes
- **Runbooks**: Create specific runbooks for common issues

For additional support, refer to the main README.md and API documentation.