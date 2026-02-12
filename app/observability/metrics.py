"""
Prometheus metrics for observability.
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Dict
import time


# ============================================================================
# REQUEST METRICS
# ============================================================================

request_count = Counter(
    'memory_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status_code', 'tenant_id']
)

request_duration = Histogram(
    'memory_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# ============================================================================
# BUSINESS METRICS
# ============================================================================

memory_count = Gauge(
    'memory_total_active',
    'Total number of active memories',
    ['tenant_id']
)

memory_ingest_total = Counter(
    'memory_ingest_total',
    'Total memories ingested',
    ['tenant_id', 'status']
)

memory_retrieve_total = Counter(
    'memory_retrieve_total',
    'Total memory retrievals',
    ['tenant_id']
)

memory_delete_total = Counter(
    'memory_delete_total',
    'Total memory deletions',
    ['tenant_id']
)

memory_expire_total = Counter(
    'memory_expire_total',
    'Total memories expired by TTL',
    ['tenant_id']
)

# ============================================================================
# POLICY METRICS
# ============================================================================

policy_violation_total = Counter(
    'policy_violation_total',
    'Total policy violations',
    ['tenant_id', 'policy_type']
)

quota_usage = Gauge(
    'quota_usage_percent',
    'Quota usage percentage',
    ['tenant_id', 'quota_type']
)

# ============================================================================
# RBAC METRICS
# ============================================================================

permission_denied_total = Counter(
    'permission_denied_total',
    'Total permission denials',
    ['tenant_id', 'permission_type']
)

# ============================================================================
# EXTRACTION METRICS
# ============================================================================

extraction_duration = Histogram(
    'extraction_duration_seconds',
    'LLM extraction duration',
    ['provider', 'model'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

extraction_total = Counter(
    'extraction_total',
    'Total extractions',
    ['provider', 'model', 'status']
)

extraction_triples_count = Histogram(
    'extraction_triples_count',
    'Number of triples extracted',
    ['provider'],
    buckets=(0, 1, 2, 5, 10, 20, 50)
)

# ============================================================================
# CHAT METRICS
# ============================================================================

chat_request_total = Counter(
    'chat_request_total',
    'Total chat requests',
    ['tenant_id']
)

chat_latency_seconds = Histogram(
    'chat_latency_seconds',
    'Chat request latency',
    ['tenant_id'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

chat_memory_injected_total = Counter(
    'chat_memory_injected_total',
    'Total chats with memory context injected',
    ['tenant_id']
)

chat_error_total = Counter(
    'chat_error_total',
    'Total chat errors',
    ['error_type']
)

# ============================================================================
# GEMINI-SPECIFIC METRICS
# ============================================================================

# Circuit breaker metrics
gemini_circuit_open_total = Counter(
    'gemini_circuit_open_total',
    'Total times Gemini circuit breaker opened'
)

gemini_failure_total = Counter(
    'gemini_failure_total',
    'Total Gemini API failures'
)

# JSON parsing metrics
gemini_json_parse_failures_total = Counter(
    'gemini_json_parse_failures_total',
    'Total Gemini JSON parsing failures'
)

# Extraction quality metrics
gemini_extraction_triple_count_histogram = Histogram(
    'gemini_extraction_triple_count',
    'Number of triples extracted by Gemini',
    buckets=(0, 1, 2, 5, 10, 20, 50)
)

gemini_extraction_confidence_avg = Gauge(
    'gemini_extraction_confidence_avg',
    'Average confidence of Gemini extractions',
    ['provider']
)

# LLM call latency (provider-agnostic)
llm_call_latency_seconds = Histogram(
    'llm_call_latency_seconds',
    'LLM call latency in seconds',
    ['provider', 'type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

# Context truncation metric
chat_context_truncated_total = Counter(
    'chat_context_truncated_total',
    'Total times chat context was truncated',
    ['provider']
)

# Provider fallback metric
provider_fallback_total = Counter(
    'provider_fallback_total',
    'Total provider fallbacks',
    ['from_provider', 'to_provider']
)

# ============================================================================
# ERROR METRICS
# ============================================================================

error_total = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'endpoint']
)

# ============================================================================
# SYSTEM INFO
# ============================================================================

system_info = Info(
    'memory_system',
    'System information'
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

class RequestTimer:
    """Context manager for timing requests."""
    
    def __init__(self, method: str, endpoint: str):
        self.method = method
        self.endpoint = endpoint
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        request_duration.labels(
            method=self.method,
            endpoint=self.endpoint
        ).observe(duration)


def record_request(method: str, endpoint: str, status_code: int, tenant_id: str = "unknown"):
    """Record a request."""
    request_count.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code),
        tenant_id=tenant_id
    ).inc()


def record_extraction(provider: str, model: str, status: str, duration: float, triple_count: int):
    """Record an extraction operation."""
    extraction_total.labels(
        provider=provider,
        model=model,
        status=status
    ).inc()
    
    extraction_duration.labels(
        provider=provider,
        model=model
    ).observe(duration)
    
    extraction_triples_count.labels(
        provider=provider
    ).observe(triple_count)


def record_policy_violation(tenant_id: str, policy_type: str):
    """Record a policy violation."""
    policy_violation_total.labels(
        tenant_id=tenant_id,
        policy_type=policy_type
    ).inc()


def record_permission_denied(tenant_id: str, permission_type: str):
    """Record a permission denial."""
    permission_denied_total.labels(
        tenant_id=tenant_id,
        permission_type=permission_type
    ).inc()


def update_memory_count(tenant_id: str, count: int):
    """Update memory count gauge."""
    memory_count.labels(tenant_id=tenant_id).set(count)


def update_quota_usage(tenant_id: str, quota_type: str, usage_percent: float):
    """Update quota usage gauge."""
    quota_usage.labels(
        tenant_id=tenant_id,
        quota_type=quota_type
    ).set(usage_percent)
