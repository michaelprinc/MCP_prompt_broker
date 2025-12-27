"""
Engine module for llama-orchestrator.

Provides process management, state persistence, and command building.
"""

from llama_orchestrator.engine.command import (
    build_command,
    build_env,
    format_command,
    resolve_model_path,
    validate_executable,
)
from llama_orchestrator.engine.process import (
    ProcessError,
    get_instance_status,
    get_log_files,
    is_process_running,
    list_instances,
    restart_instance,
    start_instance,
    stop_instance,
)
from llama_orchestrator.engine.state import (
    HealthStatus,
    InstanceState,
    InstanceStatus,
    delete_state,
    get_health_history,
    init_db,
    load_all_states,
    load_state,
    record_health_check,
    save_state,
)

__all__ = [
    # Command
    "build_command",
    "build_env",
    "format_command",
    "resolve_model_path",
    "validate_executable",
    # Process
    "ProcessError",
    "start_instance",
    "stop_instance",
    "restart_instance",
    "get_instance_status",
    "list_instances",
    "get_log_files",
    "is_process_running",
    # State
    "InstanceState",
    "InstanceStatus",
    "HealthStatus",
    "init_db",
    "save_state",
    "load_state",
    "load_all_states",
    "delete_state",
    "record_health_check",
    "get_health_history",
]
