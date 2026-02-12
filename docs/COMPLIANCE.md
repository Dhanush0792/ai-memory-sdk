# Memory Infrastructure Phase 2 - Compliance & Security Documentation

## Data Flow Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTPS (TLS 1.2+)
       ↓
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                           │
│  - Rate Limiting (per tenant)                           │
│  - Request Size Validation                              │
│  - CORS Enforcement (no wildcard)                       │
└──────┬──────────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────────────────┐
│              Authentication Layer                        │
│  - API Key Validation (SHA-256 hashed in audit)         │
│  - Tenant Identification                                │
└──────┬──────────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────────────────┐
│                  RBAC Layer                              │
│  - Role Verification                                    │
│  - Permission Check (ingest/retrieve/delete/admin)      │
│  - Scope Validation                                      │
└──────┬──────────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────────────────┐
│               Policy Engine                              │
│  - Quota Enforcement (user + tenant)                    │
│  - Confidence Threshold Check                           │
│  - Predicate Whitelist Validation                       │
│  - TTL Calculation                                       │
└──────┬──────────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────────────────┐
│          LLM Extraction (External)                       │
│  - OpenAI / Anthropic / Local LLM                       │
│  - NO PII sent (only conversation text)                 │
│  - Structured output validation                         │
└──────┬──────────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────────────────┐
│            Business Logic Layer                          │
│  - Transaction-Safe Storage                             │
│  - Scoped Memory Management                             │
│  - Deterministic Retrieval                              │
└──────┬──────────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL Database                         │
│  - Encrypted at Rest (LUKS / Cloud Provider)            │
│  - Optional Field-Level Encryption (AES-256-GCM)        │
│  - Automated Backups (daily, 30-day retention)          │
└──────┬──────────────────────────────────────────────────┘
       │
       ↓
┌─────────────────────────────────────────────────────────┐
│                 Audit Logs                               │
│  - All operations logged                                │
│  - API keys hashed (SHA-256)                            │
│  - 7-year retention (compliance)                        │
└─────────────────────────────────────────────────────────┘
```

---

## Data Retention Policy

### Active Data
- **Memories**: Retained per tenant policy (default: 365 days)
- **Configurable TTL**: Tenant-specific expiration policies
- **Soft Delete**: Expired memories marked inactive, not immediately purged

### Audit Logs
- **Retention**: 7 years (regulatory compliance)
- **Contents**: Action type, timestamp, tenant/user ID, API key hash, success/failure
- **Exclusions**: Raw conversation text, sensitive PII

### Backups
- **Frequency**: Daily automated backups
- **Retention**: 30 days (configurable)
- **Storage**: Local + optional S3
- **Encryption**: Backups encrypted in transit and at rest

### Hard Deletion
- **Expired Memories**: Purged 90 days after soft delete
- **User Deletion Requests**: Immediate soft delete, hard delete within 30 days
- **Audit Logs**: Never deleted (compliance requirement)

---

## Threat Model Summary

### Threats Mitigated ✅

| Threat | Mitigation | Severity |
|--------|-----------|----------|
| Unauthorized Access | RBAC + API Key Authentication | High |
| Data Exfiltration | Encryption (at-rest + in-transit), Audit Logging | High |
| Quota Abuse | Policy Engine (user + tenant quotas) | Medium |
| SQL Injection | Parameterized Queries, Input Validation | High |
| DoS Attacks | Rate Limiting (per tenant), Request Size Limits | Medium |
| CORS Bypass | Explicit Origin Whitelist (no wildcard) | Medium |
| Malformed LLM Output | Strict JSON Validation, Duplicate Detection | Medium |
| Privilege Escalation | Role-Based Permissions, Scope Hierarchy | High |
| Data Tampering | Transaction-Safe Versioning, Audit Logs | Medium |

### Residual Risks ⚠️

| Risk | Impact | Mitigation Plan |
|------|--------|----------------|
| LLM Provider Breach | High | Use local LLM for sensitive data; encrypt conversation text |
| Insider Threat (Admin) | High | Audit all admin actions; implement 2FA for admin roles |
| Encryption Key Compromise | Critical | Implement key rotation; use HSM for production |
| Database Breach | Critical | Enable at-rest encryption; restrict network access |
| Backup Theft | Medium | Encrypt backups; use S3 with versioning + MFA delete |

---

## Security Checklist

### Authentication & Authorization
- [x] API key required for all endpoints
- [x] API keys hashed in audit logs (SHA-256)
- [x] RBAC enforced on all operations
- [x] Role-based scope restrictions
- [x] Permission checks before data access

### Data Protection
- [x] TLS 1.2+ for all connections
- [x] At-rest encryption supported (PostgreSQL + Cloud)
- [x] Optional field-level encryption (AES-256-GCM)
- [x] Parameterized SQL queries (no string concatenation)
- [x] Input validation on all endpoints

### Network Security
- [x] CORS restricted to explicit origins
- [x] No wildcard CORS allowed
- [x] Rate limiting per tenant
- [x] Request size limits enforced
- [x] Health endpoint unauthenticated (read-only)

### Observability & Audit
- [x] All operations logged to audit table
- [x] Prometheus metrics for monitoring
- [x] Structured logging (JSON format)
- [x] Error tracking and alerting
- [x] 7-year audit log retention

### Deployment Security
- [x] Non-root container user
- [x] Minimal production Docker image
- [x] Health checks configured
- [x] Resource limits defined
- [x] Secrets via environment variables (not hardcoded)

### Compliance
- [x] GDPR: Right to deletion (soft + hard delete)
- [x] GDPR: Data export capability
- [x] GDPR: Audit trail for all operations
- [x] SOC2: Encryption at rest and in transit
- [x] SOC2: Access controls (RBAC)
- [x] SOC2: Audit logging (7-year retention)
- [x] HIPAA: Encryption, audit logs, access controls

---

## GDPR Compliance

### Right to Access
- **Endpoint**: `GET /api/v1/memory/{user_id}`
- **Returns**: All active memories for user
- **Format**: JSON export

### Right to Deletion
- **Endpoint**: `DELETE /api/v1/memory/{user_id}`
- **Process**: Immediate soft delete, hard delete within 30 days
- **Audit**: Deletion logged with timestamp

### Right to Portability
- **Format**: JSON export of all user data
- **Includes**: Memories, metadata, timestamps
- **Excludes**: Internal IDs, system metadata

### Data Minimization
- **Extraction**: Only necessary facts extracted
- **Storage**: No raw conversation text stored
- **Audit**: API keys hashed, no sensitive PII logged

### Consent Management
- **Tenant-Level**: Policies define data retention
- **User-Level**: Users can delete their data anytime
- **Audit**: All consent changes logged

---

## SOC2 Considerations

### Security
- Encryption at rest and in transit
- RBAC for access control
- Audit logging for all operations
- Incident response via structured logging

### Availability
- Health checks for monitoring
- Automated backups (daily)
- Disaster recovery procedures documented
- Horizontal scaling supported

### Processing Integrity
- Transaction-safe versioning
- Deterministic ranking algorithm
- Input validation and sanitization
- Duplicate detection

### Confidentiality
- API key authentication
- Field-level encryption (optional)
- Tenant isolation (multi-tenancy)
- Audit logs exclude sensitive data

### Privacy
- Data retention policies
- User deletion capability
- Audit trail for compliance
- No PII in logs

---

## Incident Response Plan

### Detection
1. Monitor Prometheus metrics for anomalies
2. Review structured logs for errors
3. Alert on failed authentication attempts
4. Track quota violations

### Response
1. **Identify**: Determine scope and impact
2. **Contain**: Revoke compromised API keys
3. **Eradicate**: Patch vulnerabilities
4. **Recover**: Restore from backups if needed
5. **Lessons Learned**: Update security policies

### Communication
- Internal: Notify security team via Slack/PagerDuty
- External: Notify affected tenants within 72 hours (GDPR)
- Regulatory: Report breaches per compliance requirements

---

## Disaster Recovery

### RTO (Recovery Time Objective)
- **Target**: 4 hours
- **Process**: Restore from latest backup, restart services

### RPO (Recovery Point Objective)
- **Target**: 24 hours
- **Process**: Daily backups ensure max 24-hour data loss

### Recovery Steps
1. Identify failure (database corruption, hardware failure)
2. Stop application containers
3. Restore database from latest backup
4. Verify data integrity
5. Restart application
6. Monitor for errors

### Testing
- **Frequency**: Quarterly disaster recovery drills
- **Process**: Restore backup to staging environment
- **Validation**: Run integration tests, verify data

---

**Last Updated**: 2026-02-11  
**Version**: Phase 2.0  
**Compliance Officer**: [To be assigned]
