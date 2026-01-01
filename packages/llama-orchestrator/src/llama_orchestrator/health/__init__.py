"""
Health monitoring module for llama-orchestrator.

Provides health checking, monitoring, and auto-restart functionality.
"""

from llama_orchestrator.health.checker import (
    HealthCheckResult,
    check_health,
    check_instance_health,
)
from llama_orchestrator.health.monitor import (
    HealthMonitor,
    start_monitoring,
    stop_monitoring,
)
from llama_orchestrator.health.ports import (
    PortInfo,
    check_port_available,
    find_free_port,
    get_port_info,
    get_port_owner,
    get_used_ports_by_instances,
    suggest_port_for_instance,
    validate_port_for_instance,
    wait_for_port,
    wait_for_port_release,
)

__all__ = [
    # Health checking
    "HealthCheckResult",
    "check_health",
    "check_instance_health",
    # Monitoring
    "HealthMonitor",
    "start_monitoring",
    "stop_monitoring",
    # Port management
    "PortInfo",
    "check_port_available",
    "find_free_port",
    "get_port_info",
    "get_port_owner",
    "get_used_ports_by_instances",
    "suggest_port_for_instance",
    "validate_port_for_instance",
    "wait_for_port",
    "wait_for_port_release",
]
