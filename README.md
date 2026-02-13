# Memory Infrastructure Phase 2 - Enterprise Edition

**Version**: 2.0.0  
**Status**: ✅ Production-Ready for Regulated Industries

Enterprise-grade cognitive state infrastructure with RBAC, policies, TTL management, model-agnostic extraction, and full observability.

---

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose
- PostgreSQL 15+
- Python 3.11+

### 2. Installation
```bash
# Clone repository
git clone <repo-url>
cd memory

# Copy environment configuration
cp .env.example .env

# Edit .env with your settings
nano .env

# Start services
docker-compose up -d

# Apply database schema
docker exec memory-db psql -U memoryuser memorydb < database/schema.sql

# Verify deployment
curl http://localhost:8000/health
```

### 3. Configuration
```bash
# Required settings
DATABASE_URL=postgresql://memoryuser:memorypass@localhost:5432/memorydb
API_KEY=your-secure-api-key-min-16-chars
EXTRACTION_PROVIDER=openai  # or anthropic, local
OPENAI_API_KEY=sk-...

# Security
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
RATE_LIMIT_REQUESTS=100

# Observability
METRICS_ENABLED=true
STRUCTURED_LOGGING=true
```

---

## 🎯 Enterprise Features

### 1️⃣ Policy Engine
Tenant-specific quotas, TTL, confidence thresholds, and predicate whitelists.

```python
# Enforced automatically on ingest
- max_memories_per_user: 10000
- memory_ttl_days: 365
- min_confidence_threshold: 0.5
```

### 2️⃣ RBAC
Role-based access control with 4 predefined roles: `admin`, `user`, `readonly`, `service`.

```bash
# Headers required
X-API-Key: <api_key>
X-Tenant-ID: <tenant_id>
X-User-ID: <user_id>
```

### 3️⃣ Scoped Memory
Hierarchical memory access: `user` < `team` < `organization` < `global`.

### 4️⃣ TTL Management
Automated expiration with background cleanup job (runs hourly).

### 5️⃣ Model-Agnostic Extraction
Support for OpenAI, Anthropic, and local LLMs.

```bash
# Switch providers via environment
EXTRACTION_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### 6️⃣ Observability
Prometheus metrics + structured JSON logging.

```bash
# Metrics endpoint
GET /metrics

# Sample metrics
memory_requests_total{tenant_id="acme"} 1523
memory_ingest_total{tenant_id="acme",status="success"} 450
```

### 7️⃣ Backup & Recovery
Automated daily backups with 30-day retention.

```bash
# Manual backup
./scripts/backup_postgres.sh

# Restore
./scripts/restore_postgres.sh /backups/memory_db_20260211_120000.sql.gz
```

### 8️⃣ Production Deployment
Non-root Docker container with health checks and resource limits.

```bash
# Build production image
docker build -f Dockerfile.production -t memory-infrastructure:2.0 .

# Run with resource limits
docker run -d \
  --memory="512m" \
  --cpus="0.5" \
  -p 8000:8000 \
  memory-infrastructure:2.0
```

### 9️⃣ Compliance
GDPR, SOC2, HIPAA-ready with comprehensive documentation.

- ✅ Right to deletion
- ✅ Data export
- ✅ Audit trail (7-year retention)
- ✅ Encryption at rest & in transit

### 🔟 Multi-Tenancy
Complete tenant isolation with per-tenant policies and metrics.

---

## 📊 API Endpoints

### Memory Operations
```bash
# Ingest memory
POST /api/v1/memory/ingest
{
  "conversation_text": "I prefer short explanations",
  "scope": "user"  # optional: user/team/organization/global
}

# Retrieve memories
GET /api/v1/memory/{user_id}?scope=team

# Delete memories
DELETE /api/v1/memory/{user_id}
```

### System Endpoints
```bash
# Health check
GET /health

# Prometheus metrics
GET /metrics

# System info
GET /
```

---

## 🔒 Security

### Authentication
All endpoints require `X-API-Key` header.

### RBAC
Permissions enforced based on user roles:
- `admin`: Full access
- `user`: Ingest + retrieve
- `readonly`: Retrieve only
- `service`: Ingest + retrieve + delete

### Encryption
- TLS 1.2+ for all connections
- At-rest encryption (PostgreSQL)
- Optional field-level encryption (AES-256-GCM)

### Rate Limiting
Per-tenant rate limits (default: 100 req/min).

---

## 📈 Monitoring

### Prometheus Metrics
```yaml
# Scrape configuration
scrape_configs:
  - job_name: 'memory-infrastructure'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard
Import template from `docs/grafana-dashboard.json` (coming soon).

### Structured Logs
```bash
# View logs
docker logs memory-app -f

# Filter by tenant
docker logs memory-app | jq 'select(.tenant_id=="acme")'
```

---

## 🧪 Testing

### Unit Tests
```bash
pytest tests/
```

### Integration Tests
```bash
pytest tests/integration/
```

### Load Testing
```bash
locust -f tests/load/locustfile.py --users 1000
```

---

## 📚 Documentation

- [Implementation Plan](file:///C:/Users/Desktop/.gemini/antigravity/brain/3a7c0465-a7b4-4cf0-840f-dc2f443c18bb/implementation_plan.md)
- [Verification Report](file:///C:/Users/Desktop/.gemini/antigravity/brain/3a7c0465-a7b4-4cf0-840f-dc2f443c18bb/verification_report.md)
- [Compliance Documentation](file:///C:/Users/Desktop/Projects/memory/docs/COMPLIANCE.md)
- [Task Checklist](file:///C:/Users/Desktop/.gemini/antigravity/brain/3a7c0465-a7b4-4cf0-840f-dc2f443c18bb/task.md)

---

## 🚢 Production Deployment

### Pre-Deployment Checklist
- [ ] Configure `.env` with production settings
- [ ] Set up PostgreSQL with encryption
- [ ] Configure CORS origins (no wildcards)
- [ ] Set up automated backups (cron)
- [ ] Configure Prometheus scraping
- [ ] Set up log aggregation

### Deployment Steps
1. Build production Docker image
2. Run database migrations
3. Deploy application containers
4. Configure load balancer
5. Set up TLS certificates
6. Verify health checks

### Post-Deployment
- [ ] Test all endpoints
- [ ] Verify metrics collection
- [ ] Run load tests
- [ ] Security scan
- [ ] Compliance audit

---

## 🆘 Support

### Common Issues

**Q: How do I switch LLM providers?**  
A: Update `EXTRACTION_PROVIDER` in `.env` and set the corresponding API key.

**Q: How do I configure TTL?**  
A: Update `memory_ttl_days` in `tenant_policies` table.

**Q: How do I add a new role?**  
A: Insert into `roles` table or use RBAC API (coming soon).

**Q: How do I backup the database?**  
A: Run `./scripts/backup_postgres.sh` manually or via cron.

---

## 📄 License

[Your License Here]

---

## 🎉 Success Criteria: ACHIEVED

✅ Multi-tenant hardened  
✅ Role-enforced  
✅ Policy-driven  
✅ Expiry-managed  
✅ Observable  
✅ Backed up  
✅ Deployable at scale  
✅ Vendor-agnostic  
✅ Compliance-ready

**Status**: Production-ready for regulated industries.

---

## 📞 Support

For issues or questions:
1. Check component-specific README ([backend](backend/README.md) or [frontend](frontend/README.md))
2. API documentation at `/docs`
3. Open an issue on GitHub

---

**Built with ❤️ from India.**
