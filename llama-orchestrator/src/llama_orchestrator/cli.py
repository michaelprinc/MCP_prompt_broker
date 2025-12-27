"""
llama-orchestrator CLI - Typer-based command line interface.

Commands:
    up <name>           Start an instance
    down <name>         Stop an instance
    restart <name>      Restart an instance
    ps                  List all instances
    health <name>       Check instance health
    logs <name>         View instance logs
    describe <name>     Show full config + status
    dashboard           Live TUI dashboard
    config validate     Validate configuration
    daemon start        Start background daemon
"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from llama_orchestrator import __version__

# Initialize Typer app
app = typer.Typer(
    name="llama-orch",
    help="Docker-like CLI orchestration for llama.cpp server instances",
    add_completion=False,
    no_args_is_help=True,
)

# Sub-apps for grouped commands
config_app = typer.Typer(help="Configuration management")
daemon_app = typer.Typer(help="Daemon management")

app.add_typer(config_app, name="config")
app.add_typer(daemon_app, name="daemon")

# Rich console for pretty output
console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"llama-orchestrator v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """
    llama-orchestrator: Manage multiple llama.cpp server instances.
    """
    pass


# =============================================================================
# Instance Management Commands
# =============================================================================


@app.command()
def up(
    name: Annotated[str, typer.Argument(help="Instance name to start")],
    detach: Annotated[bool, typer.Option("--detach", "-d", help="Run in background")] = True,
) -> None:
    """
    Start a llama.cpp server instance.
    
    Example:
        llama-orch up gpt-oss
    """
    from llama_orchestrator.engine import (
        ProcessError,
        build_command,
        format_command,
        start_instance,
        validate_executable,
    )
    from rich.panel import Panel
    
    # Check executable
    exe_valid, exe_msg = validate_executable()
    if not exe_valid:
        console.print(Panel(
            f"[red]{exe_msg}[/red]\n\n"
            "Please ensure llama-server.exe is in the bin/ directory.",
            title="❌ Executable Not Found",
            border_style="red"
        ))
        raise typer.Exit(1)
    
    console.print(f"[green]Starting instance:[/green] {name}")
    
    try:
        state = start_instance(name)
        console.print(Panel(
            f"[green]Instance '{name}' started successfully![/green]\n\n"
            f"PID: {state.pid}\n"
            f"Status: {state.status.value}\n"
            f"Health: {state.health.value} (loading...)",
            title="✅ Instance Started",
            border_style="green"
        ))
        console.print("\n[dim]Check status with:[/dim] [cyan]llama-orch ps[/cyan]")
        console.print("[dim]View logs with:[/dim] [cyan]llama-orch logs " + name + "[/cyan]")
    except ProcessError as e:
        console.print(Panel(
            f"[red]Failed to start instance:[/red]\n{e.message}",
            title="❌ Start Failed",
            border_style="red"
        ))
        raise typer.Exit(1)


@app.command()
def down(
    name: Annotated[str, typer.Argument(help="Instance name to stop")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Force stop")] = False,
) -> None:
    """
    Stop a llama.cpp server instance.
    
    Example:
        llama-orch down gpt-oss
        llama-orch down gpt-oss --force
    """
    from llama_orchestrator.engine import ProcessError, stop_instance
    from rich.panel import Panel
    
    console.print(f"[red]Stopping instance:[/red] {name}")
    
    try:
        state = stop_instance(name, force=force)
        console.print(Panel(
            f"[green]Instance '{name}' stopped successfully![/green]\n\n"
            f"Status: {state.status.value}",
            title="✅ Instance Stopped",
            border_style="green"
        ))
    except ProcessError as e:
        console.print(Panel(
            f"[red]Failed to stop instance:[/red]\n{e.message}",
            title="❌ Stop Failed",
            border_style="red"
        ))
        raise typer.Exit(1)


@app.command()
def restart(
    name: Annotated[str, typer.Argument(help="Instance name to restart")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Force stop before restart")] = False,
) -> None:
    """
    Restart a llama.cpp server instance.
    
    Example:
        llama-orch restart gpt-oss
    """
    from llama_orchestrator.engine import ProcessError, restart_instance
    from rich.panel import Panel
    
    console.print(f"[blue]Restarting instance:[/blue] {name}")
    
    try:
        state = restart_instance(name, force=force)
        console.print(Panel(
            f"[green]Instance '{name}' restarted successfully![/green]\n\n"
            f"PID: {state.pid}\n"
            f"Restart count: {state.restart_count}",
            title="✅ Instance Restarted",
            border_style="green"
        ))
    except ProcessError as e:
        console.print(Panel(
            f"[red]Failed to restart instance:[/red]\n{e.message}",
            title="❌ Restart Failed",
            border_style="red"
        ))
        raise typer.Exit(1)


@app.command()
def ps(
    all_instances: Annotated[
        bool, typer.Option("--all", "-a", help="Show all instances including stopped")
    ] = False,
) -> None:
    """
    List all llama.cpp server instances.
    
    Example:
        llama-orch ps
        llama-orch ps --all
    """
    from llama_orchestrator.engine import InstanceStatus, list_instances
    
    instances = list_instances()
    
    if not instances:
        console.print("[dim]No instances configured.[/dim]")
        console.print("Use 'llama-orch init <name> --model <path>' to create one.")
        return
    
    # Filter if not showing all
    if not all_instances:
        instances = {
            k: v for k, v in instances.items() 
            if v.status != InstanceStatus.STOPPED
        }
        if not instances:
            console.print("[dim]No running instances.[/dim]")
            console.print("Use 'llama-orch ps --all' to show all instances.")
            return
    
    table = Table(title="llama-orchestrator Instances")
    
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("PID", style="magenta")
    table.add_column("Port", style="green")
    table.add_column("Backend", style="yellow")
    table.add_column("Status", style="bold")
    table.add_column("Health", style="bold")
    table.add_column("Uptime", style="dim")
    
    for name, state in sorted(instances.items()):
        # Try to get config for port/backend info
        port = "-"
        backend = "-"
        try:
            from llama_orchestrator.config import get_instance_config
            config = get_instance_config(name)
            port = str(config.server.port)
            backend = config.gpu.backend
        except Exception:
            pass
        
        # Status styling
        status_style = {
            InstanceStatus.RUNNING: "green",
            InstanceStatus.STARTING: "yellow",
            InstanceStatus.STOPPING: "yellow",
            InstanceStatus.STOPPED: "dim",
            InstanceStatus.ERROR: "red",
        }.get(state.status, "white")
        
        status_text = f"[{status_style}]{state.status_symbol} {state.status.value}[/{status_style}]"
        health_text = f"{state.health_symbol} {state.health.value}"
        
        table.add_row(
            name,
            str(state.pid) if state.pid else "-",
            port,
            backend,
            status_text,
            health_text,
            state.uptime_str,
        )
    
    console.print(table)


@app.command()
def health(
    name: Annotated[str, typer.Argument(help="Instance name to check")],
) -> None:
    """
    Check health status of an instance.
    
    Example:
        llama-orch health gpt-oss
    """
    console.print(f"[blue]Checking health:[/blue] {name}")
    # TODO: Implement in Phase 3
    console.print("[yellow]⚠ Not implemented yet (Phase 3)[/yellow]")


@app.command()
def logs(
    name: Annotated[str, typer.Argument(help="Instance name")],
    tail: Annotated[int, typer.Option("--tail", "-n", help="Number of lines")] = 100,
    follow: Annotated[bool, typer.Option("--follow", "-f", help="Follow log output")] = False,
    stderr: Annotated[bool, typer.Option("--stderr", help="Show stderr instead")] = False,
) -> None:
    """
    View logs of an instance.
    
    Example:
        llama-orch logs gpt-oss --tail 50
        llama-orch logs gpt-oss --follow
    """
    log_type = "stderr" if stderr else "stdout"
    console.print(f"[blue]Showing {log_type} logs for:[/blue] {name}")
    # TODO: Implement in Phase 4
    console.print("[yellow]⚠ Not implemented yet (Phase 4)[/yellow]")


@app.command()
def describe(
    name: Annotated[str, typer.Argument(help="Instance name")],
    output_json: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """
    Show detailed information about an instance.
    
    Example:
        llama-orch describe gpt-oss
        llama-orch describe gpt-oss --json
    """
    import json
    from llama_orchestrator.config import get_instance_config
    from llama_orchestrator.engine import load_state
    from rich.panel import Panel
    
    try:
        config = get_instance_config(name)
    except FileNotFoundError:
        console.print(f"[red]Instance '{name}' not found.[/red]")
        raise typer.Exit(1)
    
    state = load_state(name)
    
    if output_json:
        # JSON output
        output = {
            "name": name,
            "config": config.model_dump(),
            "state": {
                "pid": state.pid if state else None,
                "status": state.status.value if state else "unknown",
                "health": state.health.value if state else "unknown",
                "started_at": state.started_at.isoformat() if state and state.started_at else None,
                "restart_count": state.restart_count if state else 0,
            } if state else None,
        }
        console.print(json.dumps(output, indent=2, default=str))
    else:
        # Rich panel output
        status_text = state.status.value if state else "unknown"
        health_text = state.health.value if state else "unknown"
        pid_text = str(state.pid) if state and state.pid else "-"
        uptime_text = state.uptime_str if state else "-"
        
        info = f"""
[bold cyan]Configuration[/bold cyan]
  Model:        {config.model.path}
  Context:      {config.model.context_size}
  Batch size:   {config.model.batch_size}
  
  Port:         {config.server.port}
  Host:         {config.server.host}
  Threads:      {config.model.threads}
  
  GPU Backend:  {config.gpu.backend}
  GPU Device:   {config.gpu.device_id}
  GPU Layers:   {config.gpu.layers}
  
[bold cyan]Runtime Status[/bold cyan]
  Status:       {status_text}
  Health:       {health_text}
  PID:          {pid_text}
  Uptime:       {uptime_text}
  Restarts:     {state.restart_count if state else 0}

[bold cyan]Paths[/bold cyan]
  Config:       instances/{name}/config.json
  Stdout:       {config.logs.stdout}
  Stderr:       {config.logs.stderr}
"""
        console.print(Panel(info.strip(), title=f"Instance: {name}", border_style="blue"))


@app.command()
def dashboard() -> None:
    """
    Launch live TUI dashboard.
    
    Example:
        llama-orch dashboard
    """
    console.print("[blue]Launching dashboard...[/blue]")
    # TODO: Implement in Phase 4
    console.print("[yellow]⚠ Not implemented yet (Phase 4)[/yellow]")


@app.command()
def init(
    name: Annotated[str, typer.Argument(help="Instance name to create")],
    model: Annotated[Path, typer.Option("--model", "-m", help="Path to GGUF model")],
    port: Annotated[int, typer.Option("--port", "-p", help="Server port")] = 8001,
    backend: Annotated[str, typer.Option("--backend", "-b", help="GPU backend")] = "vulkan",
    device: Annotated[int, typer.Option("--device", "-d", help="GPU device ID")] = 0,
    layers: Annotated[int, typer.Option("--layers", "-l", help="GPU layers to offload")] = 0,
    context: Annotated[int, typer.Option("--context", "-c", help="Context size")] = 4096,
    threads: Annotated[int, typer.Option("--threads", "-t", help="CPU threads")] = 8,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing config")] = False,
) -> None:
    """
    Initialize a new instance configuration.
    
    Example:
        llama-orch init gpt-oss --model ../models/gpt-oss.gguf --port 8001
        llama-orch init my-model -m models/model.gguf -p 8002 -b vulkan -d 1 -l 30
    """
    from llama_orchestrator.config import (
        GpuConfig,
        InstanceConfig,
        ModelConfig,
        ServerConfig,
        get_instances_dir,
        save_config,
    )
    from rich.panel import Panel
    
    instances_dir = get_instances_dir()
    instance_dir = instances_dir / name
    config_path = instance_dir / "config.json"
    
    # Check if already exists
    if config_path.exists() and not force:
        console.print(f"[red]Instance '{name}' already exists.[/red]")
        console.print(f"Use --force to overwrite, or choose a different name.")
        raise typer.Exit(1)
    
    # Validate backend
    valid_backends = ("cpu", "vulkan", "cuda", "metal", "hip")
    if backend not in valid_backends:
        console.print(f"[red]Invalid backend '{backend}'.[/red]")
        console.print(f"Valid options: {', '.join(valid_backends)}")
        raise typer.Exit(1)
    
    # Create config
    try:
        config = InstanceConfig(
            name=name,
            model=ModelConfig(
                path=model,
                context_size=context,
                threads=threads,
            ),
            server=ServerConfig(
                port=port,
            ),
            gpu=GpuConfig(
                backend=backend,  # type: ignore
                device_id=device,
                layers=layers,
            ),
        )
    except Exception as e:
        console.print(f"[red]Invalid configuration: {e}[/red]")
        raise typer.Exit(1)
    
    # Save config
    saved_path = save_config(config)
    
    console.print(Panel(
        f"[green]Instance '{name}' created successfully![/green]\n\n"
        f"Config: {saved_path}\n"
        f"Model: {model}\n"
        f"Port: {port}\n"
        f"Backend: {backend}" + (f" (device {device}, {layers} layers)" if backend != "cpu" else ""),
        title="✅ Instance Created",
        border_style="green"
    ))
    
    console.print("\n[dim]Next steps:[/dim]")
    console.print(f"  1. Review config: [cyan]llama-orch describe {name}[/cyan]")
    console.print(f"  2. Validate: [cyan]llama-orch config validate[/cyan]")
    console.print(f"  3. Start: [cyan]llama-orch up {name}[/cyan]")


# =============================================================================
# Config Commands
# =============================================================================


@config_app.command("validate")
def config_validate(
    path: Annotated[
        Optional[Path], 
        typer.Argument(help="Config file path (optional)")
    ] = None,
    check_runtime: Annotated[
        bool, typer.Option("--runtime", "-r", help="Check runtime conditions (port availability)")
    ] = False,
) -> None:
    """
    Validate instance configuration.
    
    Example:
        llama-orch config validate
        llama-orch config validate instances/gpt-oss/config.json
        llama-orch config validate --runtime
    """
    from llama_orchestrator.config import (
        ConfigLoadError,
        load_config,
        validate_all_instances,
        validate_instance,
    )
    from rich.panel import Panel
    
    if path:
        console.print(f"[blue]Validating config:[/blue] {path}")
        try:
            config = load_config(path)
            result = validate_instance(config, check_runtime=check_runtime)
        except ConfigLoadError as e:
            console.print(Panel(
                f"[red]Failed to load config:[/red]\n{e.message}",
                title="❌ Validation Failed",
                border_style="red"
            ))
            raise typer.Exit(1)
    else:
        console.print("[blue]Validating all instance configs...[/blue]")
        result = validate_all_instances(check_runtime=check_runtime)
    
    # Print results
    if result.issues:
        for issue in result.issues:
            console.print(str(issue))
    
    if result.is_valid:
        console.print("\n[green]✅ Validation passed[/green]")
        if result.warning_count > 0:
            console.print(f"[yellow]   ({result.warning_count} warnings)[/yellow]")
    else:
        console.print(f"\n[red]❌ Validation failed ({result.error_count} errors)[/red]")
        raise typer.Exit(1)


@config_app.command("lint")
def config_lint(
    output_json: Annotated[
        bool, typer.Option("--json", help="Output as JSON")
    ] = False,
) -> None:
    """
    Run full validation (lint) on all configurations.
    
    Includes additional best practice checks beyond basic validation.
    
    Example:
        llama-orch config lint
        llama-orch config lint --json
    """
    import json
    
    from llama_orchestrator.config import (
        ConfigLoadError,
        ValidationResult,
        lint_config,
        load_all_instances,
    )
    from rich.panel import Panel
    from rich.table import Table
    
    console.print("[blue]Linting all configurations...[/blue]\n")
    
    result = ValidationResult()
    
    try:
        configs = load_all_instances()
    except ConfigLoadError as e:
        console.print(Panel(
            f"[red]Failed to load configs:[/red]\n{e.message}",
            title="❌ Lint Failed",
            border_style="red"
        ))
        raise typer.Exit(1)
    
    if not configs:
        console.print("[yellow]No instances configured.[/yellow]")
        console.print("Use 'llama-orch init <name> --model <path>' to create one.")
        return
    
    # Lint each config
    for name, config in configs.items():
        console.print(f"[dim]Linting {name}...[/dim]")
        instance_result = lint_config(config)
        result.merge(instance_result)
    
    console.print()
    
    if output_json:
        issues_data = [
            {
                "instance": i.instance,
                "field": i.field,
                "severity": i.severity,
                "message": i.message,
                "suggestion": i.suggestion,
            }
            for i in result.issues
        ]
        console.print(json.dumps({"issues": issues_data, "valid": result.is_valid}, indent=2))
    else:
        if result.issues:
            table = Table(title="Lint Results")
            table.add_column("Severity", style="bold")
            table.add_column("Instance", style="cyan")
            table.add_column("Field", style="yellow")
            table.add_column("Message")
            
            for issue in result.issues:
                severity_style = {
                    "error": "red",
                    "warning": "yellow", 
                    "info": "blue"
                }[issue.severity]
                table.add_row(
                    f"[{severity_style}]{issue.severity.upper()}[/{severity_style}]",
                    issue.instance,
                    issue.field,
                    issue.message
                )
            
            console.print(table)
        
        console.print()
        if result.is_valid:
            console.print(f"[green]✅ Lint passed[/green] ({len(configs)} instances checked)")
            if result.warning_count > 0:
                console.print(f"[yellow]   {result.warning_count} warnings[/yellow]")
        else:
            console.print(f"[red]❌ Lint failed ({result.error_count} errors, {result.warning_count} warnings)[/red]")
            raise typer.Exit(1)


# =============================================================================
# Daemon Commands
# =============================================================================


@daemon_app.command("start")
def daemon_start(
    foreground: Annotated[bool, typer.Option("--foreground", "-f", help="Run in foreground")] = False,
) -> None:
    """
    Start the orchestrator daemon.
    
    Example:
        llama-orch daemon start
        llama-orch daemon start --foreground
    """
    mode = "foreground" if foreground else "background"
    console.print(f"[green]Starting daemon ({mode})...[/green]")
    # TODO: Implement in Phase 5
    console.print("[yellow]⚠ Not implemented yet (Phase 5)[/yellow]")


@daemon_app.command("stop")
def daemon_stop() -> None:
    """
    Stop the orchestrator daemon.
    
    Example:
        llama-orch daemon stop
    """
    console.print("[red]Stopping daemon...[/red]")
    # TODO: Implement in Phase 5
    console.print("[yellow]⚠ Not implemented yet (Phase 5)[/yellow]")


@daemon_app.command("status")
def daemon_status() -> None:
    """
    Show daemon status.
    
    Example:
        llama-orch daemon status
    """
    console.print("[blue]Daemon status:[/blue]")
    # TODO: Implement in Phase 5
    console.print("[yellow]⚠ Not implemented yet (Phase 5)[/yellow]")


if __name__ == "__main__":
    app()
