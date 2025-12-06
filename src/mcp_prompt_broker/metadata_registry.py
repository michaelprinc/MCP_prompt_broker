"""Centralized metadata registry for profile management.

This module provides a central registry for all profile metadata,
stored in a JSON file that is automatically updated on hot reload.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

# Keywords for automatic capability inference
CAPABILITY_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "ideation": ("brainstorm", "ideation", "creative", "ideas", "divergent"),
    "divergent_thinking": ("divergent", "scamper", "lateral", "unconventional"),
    "meta_cognition": ("meta-cognit", "self-reflect", "reasoning chain", "chain-of-thought"),
    "chain_of_thought": ("chain-of-thought", "step by step", "reasoning", "thinking"),
    "cross_domain": ("cross-domain", "pollination", "biomimicry", "adjacent"),
    "privacy_protection": ("privacy", "redact", "pii", "sensitive", "confidential"),
    "compliance": ("gdpr", "hipaa", "pci", "compliance", "regulation"),
    "zero_trust": ("zero-trust", "zero trust", "defense-in-depth"),
    "troubleshooting": ("troubleshoot", "diagnos", "debug", "root cause"),
    "incident_response": ("incident", "outage", "severity", "escalat"),
    "systematic_analysis": ("systematic", "layered", "structured", "methodic"),
    "adaptive_communication": ("adaptive", "audience", "tone", "context"),
    "verification": ("verif", "validat", "check", "confirm"),
    "quality_assurance": ("quality", "accuracy", "clarity", "complete"),
}

# Keywords for domain inference
DOMAIN_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    "healthcare": ("healthcare", "medical", "patient", "hipaa", "phi"),
    "finance": ("finance", "payment", "credit", "pci", "sox", "banking"),
    "legal": ("legal", "contract", "compliance", "regulation", "law"),
    "engineering": ("engineering", "code", "debug", "deploy", "api"),
    "security": ("security", "exploit", "breach", "vulnerability"),
    "creative": ("creative", "brainstorm", "design", "innovation"),
    "general": ("general", "default", "adaptive", "balanced"),
}


@dataclass
class ProfileMetadata:
    """Metadata for a single profile."""
    
    name: str
    short_description: str
    source_file: str
    default_score: int
    fallback: bool
    complexity: str  # "standard" or "complex"
    extends: Optional[str]
    required: Dict[str, List[str]]
    weights: Dict[str, Dict[str, int]]
    capabilities: List[str]
    domains: List[str]
    checklist_count: int
    instructions_length: int
    last_modified: str
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "name": self.name,
            "short_description": self.short_description,
            "source_file": self.source_file,
            "default_score": self.default_score,
            "fallback": self.fallback,
            "complexity": self.complexity,
            "extends": self.extends,
            "required": self.required,
            "weights": self.weights,
            "capabilities": self.capabilities,
            "domains": self.domains,
            "checklist_count": self.checklist_count,
            "instructions_length": self.instructions_length,
            "last_modified": self.last_modified,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileMetadata":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            short_description=data.get("short_description", ""),
            source_file=data.get("source_file", ""),
            default_score=data.get("default_score", 0),
            fallback=data.get("fallback", False),
            complexity=data.get("complexity", "standard"),
            extends=data.get("extends"),
            required=data.get("required", {}),
            weights=data.get("weights", {}),
            capabilities=data.get("capabilities", []),
            domains=data.get("domains", []),
            checklist_count=data.get("checklist_count", 0),
            instructions_length=data.get("instructions_length", 0),
            last_modified=data.get("last_modified", ""),
        )


@dataclass
class RegistryStatistics:
    """Statistics about the profile registry."""
    
    total_profiles: int
    complex_profiles: int
    standard_profiles: int
    fallback_profile: Optional[str]
    capabilities_coverage: Dict[str, int]
    domains_coverage: Dict[str, int]
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "total_profiles": self.total_profiles,
            "complex_profiles": self.complex_profiles,
            "standard_profiles": self.standard_profiles,
            "fallback_profile": self.fallback_profile,
            "capabilities_coverage": self.capabilities_coverage,
            "domains_coverage": self.domains_coverage,
        }


@dataclass
class MetadataRegistry:
    """Central registry for all profile metadata."""
    
    version: str = "1.0"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    profiles: Dict[str, ProfileMetadata] = field(default_factory=dict)
    statistics: Optional[RegistryStatistics] = None
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "profiles": {name: p.as_dict() for name, p in self.profiles.items()},
            "statistics": self.statistics.as_dict() if self.statistics else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetadataRegistry":
        """Create from dictionary."""
        profiles = {
            name: ProfileMetadata.from_dict(p_data)
            for name, p_data in data.get("profiles", {}).items()
        }
        
        stats_data = data.get("statistics")
        statistics = None
        if stats_data:
            statistics = RegistryStatistics(
                total_profiles=stats_data.get("total_profiles", 0),
                complex_profiles=stats_data.get("complex_profiles", 0),
                standard_profiles=stats_data.get("standard_profiles", 0),
                fallback_profile=stats_data.get("fallback_profile"),
                capabilities_coverage=stats_data.get("capabilities_coverage", {}),
                domains_coverage=stats_data.get("domains_coverage", {}),
            )
        
        return cls(
            version=data.get("version", "1.0"),
            generated_at=data.get("generated_at", ""),
            profiles=profiles,
            statistics=statistics,
        )
    
    def add_profile(self, metadata: ProfileMetadata) -> None:
        """Add or update a profile in the registry."""
        self.profiles[metadata.name] = metadata
    
    def remove_profile(self, name: str) -> bool:
        """Remove a profile from the registry."""
        if name in self.profiles:
            del self.profiles[name]
            return True
        return False
    
    def get_profile(self, name: str) -> Optional[ProfileMetadata]:
        """Get profile metadata by name."""
        return self.profiles.get(name)
    
    def get_profiles_by_capability(self, capability: str) -> List[ProfileMetadata]:
        """Get all profiles with a specific capability."""
        return [p for p in self.profiles.values() if capability in p.capabilities]
    
    def get_profiles_by_domain(self, domain: str) -> List[ProfileMetadata]:
        """Get all profiles matching a domain."""
        return [p for p in self.profiles.values() if domain in p.domains]
    
    def get_complex_profiles(self) -> List[ProfileMetadata]:
        """Get all complex profiles."""
        return [p for p in self.profiles.values() if p.complexity == "complex"]
    
    def get_standard_profiles(self) -> List[ProfileMetadata]:
        """Get all standard (non-complex) profiles."""
        return [p for p in self.profiles.values() if p.complexity == "standard"]
    
    def compute_statistics(self) -> RegistryStatistics:
        """Compute statistics about the registry."""
        complex_profiles = [p for p in self.profiles.values() if p.complexity == "complex"]
        standard_profiles = [p for p in self.profiles.values() if p.complexity == "standard"]
        fallback = next((p.name for p in self.profiles.values() if p.fallback), None)
        
        # Compute capability coverage
        capabilities_coverage: Dict[str, int] = {}
        for profile in self.profiles.values():
            for cap in profile.capabilities:
                capabilities_coverage[cap] = capabilities_coverage.get(cap, 0) + 1
        
        # Compute domain coverage
        domains_coverage: Dict[str, int] = {}
        for profile in self.profiles.values():
            for domain in profile.domains:
                domains_coverage[domain] = domains_coverage.get(domain, 0) + 1
        
        self.statistics = RegistryStatistics(
            total_profiles=len(self.profiles),
            complex_profiles=len(complex_profiles),
            standard_profiles=len(standard_profiles),
            fallback_profile=fallback,
            capabilities_coverage=capabilities_coverage,
            domains_coverage=domains_coverage,
        )
        
        return self.statistics


def infer_capabilities(instructions: str) -> List[str]:
    """Infer capabilities from instruction text."""
    normalized = instructions.lower()
    capabilities: Set[str] = set()
    
    for capability, keywords in CAPABILITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                capabilities.add(capability)
                break
    
    return sorted(capabilities)


def infer_domains(instructions: str, required: Dict[str, Any], weights: Dict[str, Any]) -> List[str]:
    """Infer domains from instruction text and metadata."""
    domains: Set[str] = set()
    normalized = instructions.lower()
    
    # Check instruction text
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                domains.add(domain)
                break
    
    # Check required domains
    if "domain" in required:
        for domain in required["domain"]:
            domains.add(domain)
    
    # Check weight domains
    if "domain" in weights:
        for domain in weights["domain"].keys():
            domains.add(domain)
    
    return sorted(domains)


def infer_complexity(filename: str, name: str) -> str:
    """Infer complexity level from filename or name."""
    if "_complex" in filename.lower() or "_complex" in name.lower():
        return "complex"
    return "standard"


def extract_extends(metadata: Dict[str, Any]) -> Optional[str]:
    """Extract 'extends' field from YAML metadata."""
    return metadata.get("extends")


def get_file_modified_time(file_path: Path) -> str:
    """Get file modification time as ISO string."""
    try:
        mtime = file_path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


class MetadataRegistryManager:
    """Manages the central metadata registry file."""
    
    DEFAULT_FILENAME = "profiles_metadata.json"
    
    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize the registry manager.
        
        Args:
            registry_path: Path to the registry JSON file.
                          Defaults to copilot-profiles/profiles_metadata.json.
        """
        if registry_path is None:
            registry_path = Path(__file__).parent / "copilot-profiles" / self.DEFAULT_FILENAME
        
        self._registry_path = registry_path
        self._registry: Optional[MetadataRegistry] = None
    
    @property
    def registry_path(self) -> Path:
        """Return the registry file path."""
        return self._registry_path
    
    @property
    def registry(self) -> MetadataRegistry:
        """Return the current registry, loading if necessary."""
        if self._registry is None:
            self._registry = self.load()
        return self._registry
    
    def load(self) -> MetadataRegistry:
        """Load the registry from the JSON file."""
        if self._registry_path.exists():
            try:
                with open(self._registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._registry = MetadataRegistry.from_dict(data)
                return self._registry
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                # If file is corrupted, create new registry
                pass
        
        # Create new empty registry
        self._registry = MetadataRegistry()
        return self._registry
    
    def save(self) -> Dict[str, Any]:
        """Save the registry to the JSON file.
        
        Returns:
            Summary of the save operation.
        """
        if self._registry is None:
            self._registry = MetadataRegistry()
        
        # Update generation timestamp
        self._registry.generated_at = datetime.now(timezone.utc).isoformat()
        
        # Compute statistics before saving
        self._registry.compute_statistics()
        
        # Ensure directory exists
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write JSON file with pretty formatting
        with open(self._registry_path, "w", encoding="utf-8") as f:
            json.dump(self._registry.as_dict(), f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "path": str(self._registry_path),
            "profiles_count": len(self._registry.profiles),
            "generated_at": self._registry.generated_at,
        }
    
    def update_from_parsed_profile(
        self,
        name: str,
        short_description: str,
        source_file: str,
        default_score: int,
        fallback: bool,
        required: Dict[str, Any],
        weights: Dict[str, Any],
        instructions: str,
        checklist_count: int,
        file_path: Path,
        yaml_metadata: Optional[Dict[str, Any]] = None,
    ) -> ProfileMetadata:
        """Update registry with data from a parsed profile.
        
        Args:
            name: Profile name
            short_description: Short description from YAML
            source_file: Source markdown filename
            default_score: Default routing score
            fallback: Whether this is a fallback profile
            required: Required metadata constraints
            weights: Scoring weights
            instructions: Full instruction text
            checklist_count: Number of checklist items
            file_path: Path to the source file
            yaml_metadata: Full YAML frontmatter metadata
            
        Returns:
            The created or updated ProfileMetadata.
        """
        if self._registry is None:
            self._registry = self.load()
        
        yaml_metadata = yaml_metadata or {}
        
        # Convert required to serializable format
        required_dict: Dict[str, List[str]] = {}
        for key, values in required.items():
            if isinstance(values, (set, frozenset, list, tuple)):
                required_dict[key] = sorted(str(v) for v in values)
            else:
                required_dict[key] = [str(values)]
        
        # Convert weights to serializable format
        weights_dict: Dict[str, Dict[str, int]] = {}
        for key, values in weights.items():
            if isinstance(values, dict):
                weights_dict[key] = {str(k): int(v) for k, v in values.items()}
        
        metadata = ProfileMetadata(
            name=name,
            short_description=short_description or yaml_metadata.get("short_instructions", ""),
            source_file=source_file,
            default_score=default_score,
            fallback=fallback,
            complexity=infer_complexity(source_file, name),
            extends=extract_extends(yaml_metadata),
            required=required_dict,
            weights=weights_dict,
            capabilities=infer_capabilities(instructions),
            domains=infer_domains(instructions, required_dict, weights_dict),
            checklist_count=checklist_count,
            instructions_length=len(instructions),
            last_modified=get_file_modified_time(file_path),
        )
        
        self._registry.add_profile(metadata)
        return metadata
    
    def clear(self) -> None:
        """Clear all profiles from the registry."""
        if self._registry:
            self._registry.profiles.clear()
            self._registry.statistics = None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the registry for MCP tools."""
        registry = self.registry
        stats = registry.statistics or registry.compute_statistics()
        
        return {
            "version": registry.version,
            "generated_at": registry.generated_at,
            "statistics": stats.as_dict(),
            "profiles": [
                {
                    "name": p.name,
                    "short_description": p.short_description,
                    "complexity": p.complexity,
                    "capabilities": p.capabilities,
                    "domains": p.domains,
                    "default_score": p.default_score,
                    "fallback": p.fallback,
                }
                for p in sorted(registry.profiles.values(), key=lambda x: x.name)
            ],
        }


# Global registry manager instance
_global_registry_manager: Optional[MetadataRegistryManager] = None


def get_registry_manager() -> MetadataRegistryManager:
    """Get or create the global registry manager."""
    global _global_registry_manager
    if _global_registry_manager is None:
        _global_registry_manager = MetadataRegistryManager()
    return _global_registry_manager


def get_metadata_registry() -> MetadataRegistry:
    """Get the current metadata registry."""
    return get_registry_manager().registry


def save_metadata_registry() -> Dict[str, Any]:
    """Save the current registry to disk."""
    return get_registry_manager().save()


def get_registry_summary() -> Dict[str, Any]:
    """Get a summary of the registry for MCP tools."""
    return get_registry_manager().get_summary()
