"""
Observability module for metrics and logging.
"""

from app.observability.metrics import (
    request_count,
    request_duration,
    memory_count,
    memory_ingest_total,
    memory_retrieve_total,
    memory_delete_total,
    memory_expire_total,
    policy_violation_total,
    quota_usage,
    permission_denied_total,
    extraction_duration,
    extraction_total,
    error_total,
    system_info,
    RequestTimer,
    record_request,
    record_extraction,
    record_policy_violation,
    record_permission_denied,
    update_memory_count,
    update_quota_usage
)

from app.observability.logging import configure_logging, logger

__all__ = [
    'request_count',
    'request_duration',
    'memory_count',
    'memory_ingest_total',
    'memory_retrieve_total',
    'memory_delete_total',
    'memory_expire_total',
    'policy_violation_total',
    'quota_usage',
    'permission_denied_total',
    'extraction_duration',
    'extraction_total',
    'error_total',
    'system_info',
    'RequestTimer',
    'record_request',
    'record_extraction',
    'record_policy_violation',
    'record_permission_denied',
    'update_memory_count',
    'update_quota_usage',
    'configure_logging',
    'logger'
]
