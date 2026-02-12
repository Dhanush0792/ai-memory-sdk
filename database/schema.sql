-- ============================================================================
-- Memory Infrastructure Phase 2 - Enterprise Database Schema
-- ============================================================================
-- Version: 2.0
-- Description: Enterprise-grade schema with RBAC, policies, TTL, and encryption
-- ============================================================================

-- ============================================================================
-- CORE MEMORIES TABLE (Enhanced from V1.1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS memories (
    -- Primary identifier
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Multi-tenancy support
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    
    -- Structured triple storage
    subject VARCHAR(500) NOT NULL,
    predicate VARCHAR(255) NOT NULL,
    object TEXT NOT NULL,
    
    -- Metadata
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    source VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Phase 2: Scoped Memory
    scope VARCHAR(50) NOT NULL DEFAULT 'user' 
        CHECK (scope IN ('user', 'team', 'organization', 'global')),
    
    -- Phase 2: TTL Support
    expires_at TIMESTAMP,
    
    -- Phase 2: Encryption Support
    encrypted BOOLEAN NOT NULL DEFAULT false,
    encryption_key_version INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Core indexes
CREATE INDEX IF NOT EXISTS idx_memories_tenant_id ON memories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_subject ON memories(subject);
CREATE INDEX IF NOT EXISTS idx_memories_predicate ON memories(predicate);
CREATE INDEX IF NOT EXISTS idx_memories_is_active ON memories(is_active);
CREATE INDEX IF NOT EXISTS idx_memories_tenant_user ON memories(tenant_id, user_id);

-- Phase 2 indexes
CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope);
CREATE INDEX IF NOT EXISTS idx_memories_expires_at ON memories(expires_at) 
    WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_tenant_expires ON memories(tenant_id, expires_at) 
    WHERE is_active = true;

-- Unique constraint for active memories
CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_unique_active 
    ON memories(tenant_id, user_id, subject, predicate) 
    WHERE is_active = true;

-- Text search indexes
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_memories_predicate_trgm ON memories USING gin(predicate gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_memories_object_trgm ON memories USING gin(object gin_trgm_ops);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_memories_updated_at 
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- AUDIT LOGGING TABLE (V1.1)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    action_type VARCHAR(50) NOT NULL CHECK (action_type IN ('INGEST', 'UPDATE', 'DELETE', 'RETRIEVE', 'EXPIRE', 'HEALTH')),
    memory_id UUID,
    api_key_hash VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    
    -- Phase 2: RBAC context
    role_name VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_type ON audit_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_success ON audit_logs(success);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_timestamp ON audit_logs(tenant_id, timestamp DESC);

-- ============================================================================
-- POLICY ENGINE (Phase 2)
-- ============================================================================

CREATE TABLE IF NOT EXISTS tenant_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- Quota policies
    max_memories_per_user INTEGER NOT NULL DEFAULT 10000,
    max_memories_per_tenant INTEGER NOT NULL DEFAULT 100000,
    
    -- TTL policies
    memory_ttl_days INTEGER,  -- NULL = no expiry
    auto_expire_enabled BOOLEAN NOT NULL DEFAULT true,
    
    -- Quality policies
    min_confidence_threshold FLOAT NOT NULL DEFAULT 0.0 
        CHECK (min_confidence_threshold >= 0 AND min_confidence_threshold <= 1),
    
    -- Predicate whitelist (NULL = allow all)
    allowed_predicates TEXT[],
    
    -- Rate limiting (per-tenant overrides)
    rate_limit_per_minute INTEGER DEFAULT 100,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    
    -- Tier information
    tier VARCHAR(50) DEFAULT 'standard' CHECK (tier IN ('free', 'standard', 'enterprise'))
);

CREATE INDEX IF NOT EXISTS idx_tenant_policies_tenant_id ON tenant_policies(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_policies_tier ON tenant_policies(tier);

-- Auto-update timestamp trigger for policies
CREATE TRIGGER update_tenant_policies_updated_at 
    BEFORE UPDATE ON tenant_policies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- RBAC SYSTEM (Phase 2)
-- ============================================================================

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    role_name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Permissions (denormalized for performance)
    can_ingest BOOLEAN NOT NULL DEFAULT false,
    can_retrieve BOOLEAN NOT NULL DEFAULT false,
    can_delete BOOLEAN NOT NULL DEFAULT false,
    can_admin BOOLEAN NOT NULL DEFAULT false,
    
    -- Scope permissions
    max_scope VARCHAR(50) DEFAULT 'user' 
        CHECK (max_scope IN ('user', 'team', 'organization', 'global')),
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_system_role BOOLEAN NOT NULL DEFAULT false,
    
    UNIQUE(tenant_id, role_name)
);

CREATE INDEX IF NOT EXISTS idx_roles_tenant_id ON roles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_roles_system ON roles(is_system_role);

CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    
    -- Assignment metadata
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    assigned_by VARCHAR(255),
    expires_at TIMESTAMP,  -- Optional role expiration
    
    UNIQUE(tenant_id, user_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_user_roles_tenant_user ON user_roles(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_expires ON user_roles(expires_at) 
    WHERE expires_at IS NOT NULL;

-- ============================================================================
-- ENCRYPTION KEY MANAGEMENT (Phase 2)
-- ============================================================================

CREATE TABLE IF NOT EXISTS encryption_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    key_version INTEGER NOT NULL,
    
    -- Key metadata (actual key stored in secure key management system)
    key_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash for verification
    algorithm VARCHAR(50) NOT NULL DEFAULT 'AES-256-GCM',
    
    -- Status
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    rotated_at TIMESTAMP,
    expires_at TIMESTAMP,
    
    UNIQUE(tenant_id, key_version)
);

CREATE INDEX IF NOT EXISTS idx_encryption_keys_tenant_active ON encryption_keys(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_encryption_keys_expires ON encryption_keys(expires_at) 
    WHERE expires_at IS NOT NULL;

-- ============================================================================
-- TEAM MANAGEMENT (Phase 2 - for scoped memory)
-- ============================================================================

CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    team_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    
    UNIQUE(tenant_id, team_name)
);

CREATE INDEX IF NOT EXISTS idx_teams_tenant_id ON teams(tenant_id);

CREATE TABLE IF NOT EXISTS team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    
    -- Membership metadata
    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    role VARCHAR(50) DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
    
    UNIQUE(team_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_team_members_team_id ON team_members(team_id);
CREATE INDEX IF NOT EXISTS idx_team_members_user_id ON team_members(tenant_id, user_id);

-- ============================================================================
-- SYSTEM METRICS (Phase 2 - for observability)
-- ============================================================================

CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    
    -- Dimensions
    tenant_id VARCHAR(255),
    user_id VARCHAR(255),
    
    -- Labels (for Prometheus-style metrics)
    labels JSONB,
    
    -- Timestamp
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_system_metrics_tenant ON system_metrics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_system_metrics_recorded ON system_metrics(recorded_at DESC);

-- ============================================================================
-- DEFAULT DATA INSERTION
-- ============================================================================

-- Insert default policy for 'default' tenant
INSERT INTO tenant_policies (tenant_id, tier, max_memories_per_user, max_memories_per_tenant, memory_ttl_days)
VALUES ('default', 'standard', 10000, 100000, 365)
ON CONFLICT (tenant_id) DO NOTHING;

-- Insert system roles for 'default' tenant
INSERT INTO roles (tenant_id, role_name, description, can_ingest, can_retrieve, can_delete, can_admin, max_scope, is_system_role)
VALUES 
    ('default', 'admin', 'Full administrative access', true, true, true, true, 'global', true),
    ('default', 'user', 'Standard user access', true, true, false, false, 'team', true),
    ('default', 'readonly', 'Read-only access', false, true, false, false, 'user', true),
    ('default', 'service', 'Service account access', true, true, true, false, 'organization', true)
ON CONFLICT (tenant_id, role_name) DO NOTHING;

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active memories with policy context
CREATE OR REPLACE VIEW active_memories_with_policy AS
SELECT 
    m.*,
    p.memory_ttl_days,
    p.min_confidence_threshold,
    CASE 
        WHEN m.expires_at IS NOT NULL AND m.expires_at <= CURRENT_TIMESTAMP THEN true
        ELSE false
    END as is_expired
FROM memories m
LEFT JOIN tenant_policies p ON m.tenant_id = p.tenant_id
WHERE m.is_active = true;

-- User permissions view
CREATE OR REPLACE VIEW user_permissions AS
SELECT 
    ur.tenant_id,
    ur.user_id,
    r.role_name,
    r.can_ingest,
    r.can_retrieve,
    r.can_delete,
    r.can_admin,
    r.max_scope
FROM user_roles ur
JOIN roles r ON ur.role_id = r.id
WHERE (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP);

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE memories IS 'Core memory storage with versioning, scoping, and TTL support';
COMMENT ON TABLE tenant_policies IS 'Per-tenant configuration for quotas, TTL, and quality thresholds';
COMMENT ON TABLE roles IS 'Role definitions with granular permissions';
COMMENT ON TABLE user_roles IS 'User-to-role assignments with optional expiration';
COMMENT ON TABLE encryption_keys IS 'Encryption key metadata for field-level encryption';
COMMENT ON TABLE teams IS 'Team definitions for scoped memory access';
COMMENT ON TABLE audit_logs IS 'Comprehensive audit trail for all operations';

COMMENT ON COLUMN memories.scope IS 'Access scope: user (private), team, organization, or global';
COMMENT ON COLUMN memories.expires_at IS 'Automatic expiration timestamp (NULL = no expiry)';
COMMENT ON COLUMN memories.encrypted IS 'Whether object field is encrypted';
COMMENT ON COLUMN tenant_policies.allowed_predicates IS 'Whitelist of allowed predicates (NULL = allow all)';
COMMENT ON COLUMN roles.max_scope IS 'Maximum scope this role can access';
