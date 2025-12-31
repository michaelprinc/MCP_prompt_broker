"""
Daemon service for llama-orchestrator.

Runs as a background process to monitor instances and trigger auto-restarts.
"""

from __future__ import annotations

import atexit
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from llama_orchestrator.config import discover_instances, get_state_dir
from llama_orchestrator.engine.state import InstanceStatus, load_state
from llama_orchestrator.health import HealthMonitor, start_monitoring, stop_monitoring

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def get_pid_file() -> Path:
    """Get path to the daemon PID file."""
    return get_state_dir() / "daemon.pid"


def get_log_file() -> Path:
    """Get path to the daemon log file."""
    return get_state_dir() / "daemon.log"


@dataclass
class DaemonStatus:
    """Status information for the daemon."""
    
    running: bool
    pid: int | None = None
    uptime: float | None = None
    instances_monitored: int = 0
    health_checks_performed: int = 0


class DaemonService:
    """
    Background daemon service for llama-orchestrator.
    
    Monitors all instances and triggers auto-restarts based on health policy.
    """
    
    def __init__(self, check_interval: float = 10.0):
        self.check_interval = check_interval
        self._running = False
        self._start_time: float | None = None
        self._health_checks = 0
        self._monitor: HealthMonitor | None = None
    
    def start(self, foreground: bool = False) -> None:
        """
        Start the daemon service.
        
        Args:
            foreground: If True, run in foreground (blocking).
                       If False, daemonize and run in background.
        """
        if is_daemon_running():
            logger.warning("Daemon is already running")
            return
        
        if foreground:
            self._run_foreground()
        else:
            self._daemonize()
    
    def _run_foreground(self) -> None:
        """Run the daemon in foreground mode."""
        self._setup()
        self._running = True
        self._start_time = time.time()
        
        # Write PID file
        self._write_pid_file()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        # Register cleanup
        atexit.register(self._cleanup)
        
        logger.info("Daemon started in foreground mode")
        
        try:
            self._main_loop()
        finally:
            self._cleanup()
    
    def _daemonize(self) -> None:
        """Daemonize the process (Unix-style double-fork, Windows compatibility)."""
        import subprocess
        
        # On Windows, we can't do traditional daemonization
        # Instead, start a new process with CREATE_NO_WINDOW flag
        if sys.platform == "win32":
            # Start as a detached subprocess
            python = sys.executable
            script = Path(__file__).parent / "_daemon_main.py"
            
            # Write a simple entry point script
            script_content = '''
import sys
sys.path.insert(0, r"{}")
from llama_orchestrator.daemon.service import DaemonService
daemon = DaemonService()
daemon._run_foreground()
'''.format(str(Path(__file__).parent.parent.parent))
            
            script.write_text(script_content)
            
            # Start detached process
            CREATE_NO_WINDOW = 0x08000000
            DETACHED_PROCESS = 0x00000008
            
            subprocess.Popen(
                [python, str(script)],
                creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            
            logger.info("Daemon started in background")
        else:
            # Unix double-fork
            try:
                pid = os.fork()
                if pid > 0:
                    # Parent exits
                    return
            except OSError as e:
                logger.error(f"First fork failed: {e}")
                raise
            
            # Child continues
            os.setsid()
            
            try:
                pid = os.fork()
                if pid > 0:
                    # First child exits
                    os._exit(0)
            except OSError as e:
                logger.error(f"Second fork failed: {e}")
                raise
            
            # Grandchild continues as daemon
            self._run_foreground()
    
    def _setup(self) -> None:
        """Setup logging and other initialization."""
        # Setup file logging
        log_file = get_log_file()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        
        root_logger = logging.getLogger("llama_orchestrator")
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)
    
    def _write_pid_file(self) -> None:
        """Write the current PID to the PID file."""
        pid_file = get_pid_file()
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()))
    
    def _remove_pid_file(self) -> None:
        """Remove the PID file."""
        pid_file = get_pid_file()
        if pid_file.exists():
            pid_file.unlink()
    
    def _handle_signal(self, signum, frame) -> None:
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self._running = False
    
    def _cleanup(self) -> None:
        """Cleanup on exit."""
        logger.info("Daemon cleanup...")
        stop_monitoring()
        self._remove_pid_file()
    
    def _main_loop(self) -> None:
        """Main daemon loop."""
        # Start health monitoring
        self._monitor = start_monitoring(
            interval=self.check_interval,
            on_health_change=self._on_health_change,
            on_restart=self._on_restart,
        )
        
        logger.info(f"Health monitoring started (interval: {self.check_interval}s)")
        
        while self._running:
            try:
                # Log status periodically
                instances = list(discover_instances())
                running = sum(
                    1 for name, _ in instances
                    if (state := load_state(name)) and state.status == InstanceStatus.RUNNING
                )
                
                logger.debug(f"Monitoring {len(instances)} instances ({running} running)")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in daemon loop: {e}")
                time.sleep(1)
    
    def _on_health_change(self, name: str, old_status, new_status) -> None:
        """Callback for health status changes."""
        logger.info(f"Instance '{name}' health changed: {old_status.value} -> {new_status.value}")
        self._health_checks += 1
    
    def _on_restart(self, name: str, attempt: int) -> None:
        """Callback for instance restarts."""
        logger.info(f"Instance '{name}' restarted (attempt {attempt})")
    
    def stop(self) -> None:
        """Request daemon to stop."""
        self._running = False


def is_daemon_running() -> bool:
    """Check if the daemon is currently running."""
    pid_file = get_pid_file()
    
    if not pid_file.exists():
        return False
    
    try:
        pid = int(pid_file.read_text().strip())
    except (ValueError, IOError):
        return False
    
    # Check if process is running
    try:
        if sys.platform == "win32":
            import subprocess
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except (OSError, subprocess.SubprocessError):
        # Process not running, clean up stale PID file
        pid_file.unlink()
        return False


def get_daemon_status() -> DaemonStatus:
    """Get the current daemon status."""
    pid_file = get_pid_file()
    
    if not is_daemon_running():
        return DaemonStatus(running=False)
    
    try:
        pid = int(pid_file.read_text().strip())
    except (ValueError, IOError):
        return DaemonStatus(running=False)
    
    # Count monitored instances
    instances = list(discover_instances())
    running_count = sum(
        1 for name, _ in instances
        if (state := load_state(name)) and state.status == InstanceStatus.RUNNING
    )
    
    return DaemonStatus(
        running=True,
        pid=pid,
        instances_monitored=running_count,
    )


def start_daemon(foreground: bool = False) -> bool:
    """
    Start the daemon service.
    
    Args:
        foreground: Run in foreground mode
        
    Returns:
        True if daemon started successfully
    """
    if is_daemon_running():
        logger.warning("Daemon is already running")
        return False
    
    daemon = DaemonService()
    daemon.start(foreground=foreground)
    return True


def stop_daemon() -> bool:
    """
    Stop the daemon service.
    
    Returns:
        True if daemon was stopped
    """
    pid_file = get_pid_file()
    
    if not is_daemon_running():
        return False
    
    try:
        pid = int(pid_file.read_text().strip())
    except (ValueError, IOError):
        return False
    
    # Send termination signal
    try:
        if sys.platform == "win32":
            import subprocess
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True)
        else:
            os.kill(pid, signal.SIGTERM)
        
        # Wait for process to exit
        for _ in range(50):  # Wait up to 5 seconds
            if not is_daemon_running():
                return True
            time.sleep(0.1)
        
        # Force kill if still running
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True)
        else:
            os.kill(pid, signal.SIGKILL)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to stop daemon: {e}")
        return False
