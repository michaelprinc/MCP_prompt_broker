"""
State management for llama-orchestrator.

Uses SQLite to persist instance state (PID, status, health, etc.)
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from llama_orchestrator.config import get_state_dir

if TYPE_CHECKING:
    pass


class InstanceStatus(Enum):
    """Status of an instance."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class HealthStatus(Enum):
    """Health status of a running instance."""
    UNKNOWN = "unknown"
    LOADING = "loading"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    ERROR = "error"


@dataclass
class InstanceState:
    """Runtime state of an instance."""
    
    name: str
    pid: int | None = None
    status: InstanceStatus = InstanceStatus.STOPPED
    health: HealthStatus = HealthStatus.UNKNOWN
    start_time: float | None = None
    last_health_check: float | None = None
    restart_count: int = 0
    config_hash: str = ""
    error_message: str = ""
    
    @property
    def uptime(self) -> float | None:
        """Get uptime in seconds, or None if not running."""
        if self.start_time is None:
            return None
        return time.time() - self.start_time
    
    @property
    def uptime_str(self) -> str:
        """Get formatted uptime string."""
        uptime = self.uptime
        if uptime is None:
            return "-"
        
        if uptime < 60:
            return f"{int(uptime)}s"
        elif uptime < 3600:
            return f"{int(uptime // 60)}m {int(uptime % 60)}s"
        else:
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    @property
    def status_symbol(self) -> str:
        """Get status indicator symbol."""
        return {
            InstanceStatus.STOPPED: "○",
            InstanceStatus.STARTING: "◐",
            InstanceStatus.RUNNING: "●",
            InstanceStatus.STOPPING: "◑",
            InstanceStatus.ERROR: "✗",
        }.get(self.status, "?")
    
    @property
    def health_symbol(self) -> str:
        """Get health indicator symbol."""
        return {
            HealthStatus.UNKNOWN: "?",
            HealthStatus.LOADING: "◐",
            HealthStatus.HEALTHY: "●",
            HealthStatus.UNHEALTHY: "◑",
            HealthStatus.ERROR: "✗",
        }.get(self.health, "?")


def get_db_path() -> Path:
    """Get the path to the state database."""
    return get_state_dir() / "state.sqlite"


@contextmanager
def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Get a database connection with proper cleanup."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database schema."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS instances (
                name TEXT PRIMARY KEY,
                pid INTEGER,
                status TEXT NOT NULL DEFAULT 'stopped',
                health TEXT NOT NULL DEFAULT 'unknown',
                start_time REAL,
                last_health_check REAL,
                restart_count INTEGER NOT NULL DEFAULT 0,
                config_hash TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                updated_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS health_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instance_name TEXT NOT NULL,
                health TEXT NOT NULL,
                response_time_ms REAL,
                error_message TEXT,
                checked_at REAL NOT NULL DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (instance_name) REFERENCES instances(name) ON DELETE CASCADE
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_history_instance 
            ON health_history(instance_name, checked_at DESC)
        """)
        
        conn.commit()


def save_state(state: InstanceState) -> None:
    """Save instance state to database."""
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO instances (
                name, pid, status, health, start_time, 
                last_health_check, restart_count, config_hash, error_message, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                pid = excluded.pid,
                status = excluded.status,
                health = excluded.health,
                start_time = excluded.start_time,
                last_health_check = excluded.last_health_check,
                restart_count = excluded.restart_count,
                config_hash = excluded.config_hash,
                error_message = excluded.error_message,
                updated_at = excluded.updated_at
        """, (
            state.name,
            state.pid,
            state.status.value,
            state.health.value,
            state.start_time,
            state.last_health_check,
            state.restart_count,
            state.config_hash,
            state.error_message,
            time.time(),
        ))
        conn.commit()


def load_state(name: str) -> InstanceState | None:
    """Load instance state from database."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM instances WHERE name = ?", (name,)
        ).fetchone()
        
        if row is None:
            return None
        
        return InstanceState(
            name=row["name"],
            pid=row["pid"],
            status=InstanceStatus(row["status"]),
            health=HealthStatus(row["health"]),
            start_time=row["start_time"],
            last_health_check=row["last_health_check"],
            restart_count=row["restart_count"],
            config_hash=row["config_hash"],
            error_message=row["error_message"],
        )


def load_all_states() -> dict[str, InstanceState]:
    """Load all instance states from database."""
    states = {}
    
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM instances ORDER BY name").fetchall()
        
        for row in rows:
            states[row["name"]] = InstanceState(
                name=row["name"],
                pid=row["pid"],
                status=InstanceStatus(row["status"]),
                health=HealthStatus(row["health"]),
                start_time=row["start_time"],
                last_health_check=row["last_health_check"],
                restart_count=row["restart_count"],
                config_hash=row["config_hash"],
                error_message=row["error_message"],
            )
    
    return states


def delete_state(name: str) -> bool:
    """Delete instance state from database."""
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM instances WHERE name = ?", (name,))
        conn.commit()
        return cursor.rowcount > 0


def record_health_check(
    name: str, 
    health: HealthStatus, 
    response_time_ms: float | None = None,
    error_message: str = "",
) -> None:
    """Record a health check result."""
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO health_history (instance_name, health, response_time_ms, error_message)
            VALUES (?, ?, ?, ?)
        """, (name, health.value, response_time_ms, error_message))
        
        # Also update the main instance state
        conn.execute("""
            UPDATE instances 
            SET health = ?, last_health_check = ?, updated_at = ?
            WHERE name = ?
        """, (health.value, time.time(), time.time(), name))
        
        conn.commit()


def get_health_history(name: str, limit: int = 10) -> list[dict]:
    """Get recent health check history for an instance."""
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT health, response_time_ms, error_message, checked_at
            FROM health_history
            WHERE instance_name = ?
            ORDER BY checked_at DESC
            LIMIT ?
        """, (name, limit)).fetchall()
        
        return [dict(row) for row in rows]


# Initialize database on module import
init_db()
