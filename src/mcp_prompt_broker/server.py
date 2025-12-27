"""MCP server entrypoint and wiring for the prompt broker."""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any, Dict, List, Mapping, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Relativní importy v rámci balíčku
from .config.profiles import InstructionProfile, get_instruction_profiles, reload_instruction_profiles
from .metadata.parser import ParsedMetadata, analyze_prompt
from .router.profile_router import EnhancedMetadata, ProfileRouter, RoutingResult
from .profile_parser import (
    get_profile_loader,
    reload_profiles,
    get_profile_checklist,
    ProfileLoader,
    ParsedProfile,
)
from .metadata_registry import get_registry_summary


def _profile_to_dict(profile: InstructionProfile) -> Dict[str, object]:
    """Serialize an :class:`InstructionProfile` into JSON-safe structure."""

    return {
        "name": profile.name,
        "instructions": profile.instructions,
        "required": {key: sorted(value) for key, value in profile.required.items()},
        "weights": {key: dict(value) for key, value in profile.weights.items()},
        "default_score": profile.default_score,
        "fallback": profile.fallback,
    }


def _build_server(loader: ProfileLoader) -> Server:
    """Build and configure the MCP server with tools."""
    server = Server("mcp-prompt-broker")
    
    # Create router that references the loader's profiles
    def get_router() -> ProfileRouter:
        """Get router with current profiles from loader."""
        return ProfileRouter(loader.profiles)

    @server.list_tools()
    async def list_tools() -> List[types.Tool]:
        return [
            types.Tool(
                name="list_profiles",
                description="List available instruction profiles and their metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="get_profile",
                description=(
                    "Analyze a prompt, enrich it with metadata, and return the best "
                    "matching instruction profile."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "metadata": {
                            "type": "object",
                            "description": "Optional metadata overrides to steer routing.",
                        },
                    },
                    "required": ["prompt"],
                },
            ),
            # Alias for get_profile - improves discoverability for LLM tool selection
            types.Tool(
                name="resolve_prompt",
                description=(
                    "PRIMARY TOOL: Always call this FIRST before processing any user request. "
                    "Analyzes the user's prompt, detects domain/capability/complexity, "
                    "and returns optimal instructions for handling the request. "
                    "This is the main entry point for intelligent prompt routing."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The user's complete request text to analyze and route.",
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Optional metadata overrides (domain, capability, complexity).",
                        },
                    },
                    "required": ["prompt"],
                },
            ),
            types.Tool(
                name="reload_profiles",
                description=(
                    "Reload instruction profiles from markdown files. "
                    "Use this to hot-reload profiles without restarting the server. "
                    "Also updates the central metadata registry (profiles_metadata.json)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="get_checklist",
                description=(
                    "Get the checklist for a specific instruction profile. "
                    "Returns a list of checklist items from the profile's markdown file."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "profile_name": {
                            "type": "string",
                            "description": "Name of the profile to get the checklist for.",
                        },
                    },
                    "required": ["profile_name"],
                },
            ),
            types.Tool(
                name="get_registry_summary",
                description=(
                    "Get a summary of the central metadata registry. "
                    "Returns statistics about profiles, capabilities coverage, and domains."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="get_profile_metadata",
                description=(
                    "Get detailed metadata for a specific profile from the central registry. "
                    "Includes capabilities, domains, complexity level, and other inferred metadata."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "profile_name": {
                            "type": "string",
                            "description": "Name of the profile to get metadata for.",
                        },
                    },
                    "required": ["profile_name"],
                },
            ),
            types.Tool(
                name="find_profiles_by_capability",
                description=(
                    "Find all profiles that have a specific capability. "
                    "Use this to discover profiles suitable for specific tasks."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "capability": {
                            "type": "string",
                            "description": "The capability to search for (e.g., 'ideation', 'compliance', 'troubleshooting').",
                        },
                    },
                    "required": ["capability"],
                },
            ),
            types.Tool(
                name="find_profiles_by_domain",
                description=(
                    "Find all profiles that match a specific domain. "
                    "Use this to discover profiles suitable for specific domains."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain to search for (e.g., 'healthcare', 'engineering', 'creative').",
                        },
                    },
                    "required": ["domain"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> Any:
        if name == "list_profiles":
            return [types.TextContent(
                type="text",
                text=json.dumps([_profile_to_dict(profile) for profile in loader.profiles], indent=2)
            )]

        # Handle both get_profile and its alias resolve_prompt
        if name in ("get_profile", "resolve_prompt"):
            try:
                prompt = str(arguments.get("prompt", ""))
                overrides: Mapping[str, object] | None = arguments.get("metadata")
                parsed: ParsedMetadata = analyze_prompt(prompt)
                enhanced: EnhancedMetadata = parsed.to_enhanced_metadata(overrides)
                router = get_router()
                routing: RoutingResult = router.route(enhanced)
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "profile": _profile_to_dict(routing.profile),
                        "metadata": parsed.as_dict(),
                        "routing": {
                            "score": routing.score,
                            "consistency": routing.consistency,
                        },
                    }, indent=2)
                )]
            except (ValueError, LookupError) as exc:
                return [types.TextContent(type="text", text=f"Error: {str(exc)}")]

        if name == "reload_profiles":
            try:
                result = loader.reload()
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as exc:
                return [types.TextContent(type="text", text=f"Error reloading profiles: {str(exc)}")]

        if name == "get_checklist":
            try:
                profile_name = str(arguments.get("profile_name", ""))
                if not profile_name:
                    return [types.TextContent(type="text", text="Error: profile_name is required")]
                
                checklist = loader.get_checklist(profile_name)
                if checklist is None:
                    available = sorted(loader.parsed_profiles.keys())
                    return [types.TextContent(
                        type="text",
                        text=f"Error: Profile '{profile_name}' not found. Available profiles: {', '.join(available)}"
                    )]
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(checklist.as_dict(), indent=2)
                )]
            except Exception as exc:
                return [types.TextContent(type="text", text=f"Error getting checklist: {str(exc)}")]

        if name == "get_registry_summary":
            try:
                summary = get_registry_summary(loader.registry_manager)
                return [types.TextContent(
                    type="text",
                    text=json.dumps(summary, indent=2)
                )]
            except Exception as exc:
                return [types.TextContent(type="text", text=f"Error getting registry summary: {str(exc)}")]

        if name == "get_profile_metadata":
            try:
                profile_name = str(arguments.get("profile_name", ""))
                if not profile_name:
                    return [types.TextContent(type="text", text="Error: profile_name is required")]
                
                registry_manager = loader.registry_manager
                profile_metadata = registry_manager.registry.get_profile(profile_name)
                
                if profile_metadata is None:
                    available = sorted(registry_manager.registry.profiles.keys())
                    return [types.TextContent(
                        type="text",
                        text=f"Error: Profile '{profile_name}' not found in registry. Available: {', '.join(available)}"
                    )]
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(profile_metadata.as_dict(), indent=2)
                )]
            except Exception as exc:
                return [types.TextContent(type="text", text=f"Error getting profile metadata: {str(exc)}")]

        if name == "find_profiles_by_capability":
            try:
                capability = str(arguments.get("capability", "")).lower()
                if not capability:
                    return [types.TextContent(type="text", text="Error: capability is required")]
                
                registry_manager = loader.registry_manager
                matching = registry_manager.registry.get_profiles_by_capability(capability)
                
                result = {
                    "capability": capability,
                    "matches_count": len(matching),
                    "profiles": [
                        {
                            "name": p.name,
                            "short_description": p.short_description,
                            "complexity": p.complexity,
                            "capabilities": p.capabilities,
                        }
                        for p in sorted(matching, key=lambda x: x.name)
                    ],
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as exc:
                return [types.TextContent(type="text", text=f"Error finding profiles by capability: {str(exc)}")]

        if name == "find_profiles_by_domain":
            try:
                domain = str(arguments.get("domain", "")).lower()
                if not domain:
                    return [types.TextContent(type="text", text="Error: domain is required")]
                
                registry_manager = loader.registry_manager
                matching = registry_manager.registry.get_profiles_by_domain(domain)
                
                result = {
                    "domain": domain,
                    "matches_count": len(matching),
                    "profiles": [
                        {
                            "name": p.name,
                            "short_description": p.short_description,
                            "complexity": p.complexity,
                            "domains": p.domains,
                        }
                        for p in sorted(matching, key=lambda x: x.name)
                    ],
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as exc:
                return [types.TextContent(type="text", text=f"Error finding profiles by domain: {str(exc)}")]

        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def _run_server(server: Server) -> None:
    """Run the MCP server using stdio transport."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-prompt-broker",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run(argv: List[str] | None = None) -> int:
    """Parse arguments and run the MCP prompt broker server."""
    parser = argparse.ArgumentParser(description="Run the MCP prompt broker server.")
    parser.add_argument(
        "--profiles-dir",
        help="Path to directory containing profile markdown files.",
        default=None,
    )
    args = parser.parse_args(argv)

    # Initialize profile loader with hot-reload support
    from pathlib import Path
    profiles_dir = Path(args.profiles_dir) if args.profiles_dir else None
    loader = ProfileLoader(profiles_dir)
    
    # Initial load of profiles from markdown files
    reload_result = loader.reload()
    if reload_result.get("profiles_loaded", 0) == 0:
        print(f"Warning: No profiles loaded. Errors: {reload_result.get('errors', [])}")
    else:
        print(f"Loaded {reload_result['profiles_loaded']} profiles: {', '.join(reload_result['profile_names'])}")

    server = _build_server(loader)

    try:
        asyncio.run(_run_server(server))
    except KeyboardInterrupt:
        pass  # Graceful shutdown on Ctrl+C

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
