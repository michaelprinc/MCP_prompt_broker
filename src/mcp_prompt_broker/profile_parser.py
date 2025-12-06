"""Parser for markdown-based instruction profiles with hot reload support."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

import yaml

from .config.profiles import InstructionProfile
from .metadata_registry import (
    MetadataRegistryManager,
    get_registry_manager,
    save_metadata_registry,
)


@dataclass(frozen=True)
class ProfileChecklist:
    """Represents a checklist extracted from a profile markdown file."""
    
    profile_name: str
    items: tuple[str, ...]
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "profile_name": self.profile_name,
            "items": list(self.items),
            "count": len(self.items),
        }


@dataclass
class ParsedProfile:
    """Complete parsed profile from markdown file."""
    
    profile: InstructionProfile
    checklist: ProfileChecklist
    source_path: Path
    raw_instructions: str
    yaml_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "name": self.profile.name,
            "instructions": self.profile.instructions,
            "required": {k: sorted(v) for k, v in self.profile.required.items()},
            "weights": {k: dict(v) for k, v in self.profile.weights.items()},
            "default_score": self.profile.default_score,
            "fallback": self.profile.fallback,
            "checklist": self.checklist.as_dict(),
            "source": str(self.source_path.name),
        }


class ProfileParseError(Exception):
    """Raised when a profile markdown file cannot be parsed."""
    pass


def _parse_yaml_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter and remaining content from markdown.
    
    Expected format:
    ---
    key: value
    ---
    # Rest of markdown
    """
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(pattern, content, re.DOTALL)
    
    if not match:
        raise ProfileParseError("Missing YAML frontmatter (---)")
    
    yaml_content = match.group(1)
    markdown_content = match.group(2)
    
    try:
        metadata = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError as e:
        raise ProfileParseError(f"Invalid YAML frontmatter: {e}")
    
    return metadata, markdown_content


def _extract_section(content: str, header: str) -> Optional[str]:
    """Extract content under a specific markdown header (## Header)."""
    pattern = rf"^##\s+{re.escape(header)}\s*\n(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else None


def _extract_checklist_items(content: str) -> List[str]:
    """Extract checklist items from markdown content.
    
    Supports:
    - [ ] Unchecked item
    - [x] Checked item
    - Regular list items (- item)
    """
    items: List[str] = []
    
    # Match checkbox items: - [ ] or - [x]
    checkbox_pattern = r"^-\s*\[[ xX]\]\s*(.+)$"
    for match in re.finditer(checkbox_pattern, content, re.MULTILINE):
        items.append(match.group(1).strip())
    
    # If no checkbox items, try regular list items
    if not items:
        list_pattern = r"^-\s+(.+)$"
        for match in re.finditer(list_pattern, content, re.MULTILINE):
            item = match.group(1).strip()
            # Skip items that look like metadata
            if not item.startswith("[") and ":" not in item[:20]:
                items.append(item)
    
    return items


def _parse_required(data: Any) -> Mapping[str, Iterable[str]]:
    """Parse required field from YAML into proper format."""
    if not data:
        return {}
    
    result: Dict[str, Set[str]] = {}
    for key, values in data.items():
        if isinstance(values, list):
            result[key] = set(values)
        elif isinstance(values, str):
            result[key] = {values}
        else:
            result[key] = set()
    
    return result


def _parse_weights(data: Any) -> Mapping[str, Mapping[str, int]]:
    """Parse weights field from YAML into proper format."""
    if not data:
        return {}
    
    result: Dict[str, Dict[str, int]] = {}
    for key, value_weights in data.items():
        if isinstance(value_weights, dict):
            result[key] = {str(k): int(v) for k, v in value_weights.items()}
    
    return result


def parse_profile_markdown(file_path: Path) -> ParsedProfile:
    """Parse a single profile markdown file.
    
    Args:
        file_path: Path to the markdown file.
        
    Returns:
        ParsedProfile with all extracted data.
        
    Raises:
        ProfileParseError: If the file cannot be parsed.
    """
    if not file_path.exists():
        raise ProfileParseError(f"Profile file not found: {file_path}")
    
    content = file_path.read_text(encoding="utf-8")
    
    # Parse YAML frontmatter
    metadata, markdown = _parse_yaml_frontmatter(content)
    
    # Extract required fields
    name = metadata.get("name")
    if not name:
        raise ProfileParseError(f"Missing 'name' in frontmatter: {file_path}")
    
    # Extract instructions section
    instructions = _extract_section(markdown, "Instructions")
    if not instructions:
        # Fallback: use short_instructions from metadata
        instructions = metadata.get("short_instructions", "")
    if not instructions:
        raise ProfileParseError(f"Missing '## Instructions' section: {file_path}")
    
    # Extract checklist section
    checklist_content = _extract_section(markdown, "Checklist")
    checklist_items = _extract_checklist_items(checklist_content) if checklist_content else []
    
    # Build profile
    profile = InstructionProfile(
        name=str(name),
        instructions=instructions,
        required=_parse_required(metadata.get("required")),
        weights=_parse_weights(metadata.get("weights")),
        default_score=int(metadata.get("default_score", 0)),
        fallback=bool(metadata.get("fallback", False)),
    )
    
    checklist = ProfileChecklist(
        profile_name=str(name),
        items=tuple(checklist_items),
    )
    
    return ParsedProfile(
        profile=profile,
        checklist=checklist,
        source_path=file_path,
        raw_instructions=instructions,
        yaml_metadata=metadata,  # Store for registry
    )


class ProfileLoader:
    """Manages loading and hot-reloading of profiles from markdown files."""
    
    def __init__(self, profiles_dir: Optional[Path] = None):
        """Initialize the loader.
        
        Args:
            profiles_dir: Directory containing profile markdown files.
                         Defaults to copilot-profiles/ in the package.
        """
        if profiles_dir is None:
            profiles_dir = Path(__file__).parent / "copilot-profiles"
        
        self._profiles_dir = profiles_dir
        self._parsed_profiles: Dict[str, ParsedProfile] = {}
        self._load_errors: List[str] = []
        self._registry_manager = get_registry_manager()
    
    @property
    def profiles_dir(self) -> Path:
        """Return the profiles directory path."""
        return self._profiles_dir
    
    @property
    def profiles(self) -> Sequence[InstructionProfile]:
        """Return loaded instruction profiles."""
        return [p.profile for p in self._parsed_profiles.values()]
    
    @property
    def parsed_profiles(self) -> Mapping[str, ParsedProfile]:
        """Return all parsed profiles with full metadata."""
        return dict(self._parsed_profiles)
    
    @property
    def load_errors(self) -> Sequence[str]:
        """Return any errors from the last load operation."""
        return list(self._load_errors)
    
    def reload(self) -> Dict[str, Any]:
        """Reload all profiles from markdown files.
        
        Also updates the central metadata registry and saves it to JSON.
        
        Returns:
            Summary of the reload operation.
        """
        self._parsed_profiles.clear()
        self._load_errors.clear()
        self._registry_manager.clear()
        
        if not self._profiles_dir.exists():
            self._load_errors.append(f"Profiles directory not found: {self._profiles_dir}")
            return self._get_reload_summary()
        
        md_files = list(self._profiles_dir.glob("*.md"))
        
        for md_file in md_files:
            try:
                parsed = parse_profile_markdown(md_file)
                self._parsed_profiles[parsed.profile.name] = parsed
                
                # Update central metadata registry
                self._update_registry_from_profile(parsed)
                
            except ProfileParseError as e:
                self._load_errors.append(str(e))
            except Exception as e:
                self._load_errors.append(f"Unexpected error parsing {md_file}: {e}")
        
        # Save the registry to JSON file
        registry_result = {}
        try:
            registry_result = self._registry_manager.save()
        except Exception as e:
            self._load_errors.append(f"Error saving metadata registry: {e}")
        
        return self._get_reload_summary(registry_result)
    
    def _update_registry_from_profile(self, parsed: ParsedProfile) -> None:
        """Update the metadata registry with data from a parsed profile."""
        profile = parsed.profile
        yaml_meta = parsed.yaml_metadata
        
        # Get short description from various sources
        short_desc = (
            yaml_meta.get("short_description") or 
            yaml_meta.get("short_instructions") or 
            ""
        )
        
        self._registry_manager.update_from_parsed_profile(
            name=profile.name,
            short_description=short_desc,
            source_file=parsed.source_path.name,
            default_score=profile.default_score,
            fallback=profile.fallback,
            required=dict(profile.required),
            weights=dict(profile.weights),
            instructions=parsed.raw_instructions,
            checklist_count=len(parsed.checklist.items),
            file_path=parsed.source_path,
            yaml_metadata=yaml_meta,
        )
    
    def _get_reload_summary(self, registry_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a summary of the last reload operation."""
        summary = {
            "success": len(self._load_errors) == 0,
            "profiles_loaded": len(self._parsed_profiles),
            "profile_names": sorted(self._parsed_profiles.keys()),
            "errors": self._load_errors,
            "profiles_dir": str(self._profiles_dir),
        }
        
        if registry_result:
            summary["registry"] = registry_result
        
        return summary
    
    def get_checklist(self, profile_name: str) -> Optional[ProfileChecklist]:
        """Get the checklist for a specific profile.
        
        Args:
            profile_name: Name of the profile.
            
        Returns:
            ProfileChecklist if found, None otherwise.
        """
        parsed = self._parsed_profiles.get(profile_name)
        return parsed.checklist if parsed else None
    
    def get_all_checklists(self) -> Dict[str, ProfileChecklist]:
        """Get all checklists indexed by profile name."""
        return {name: p.checklist for name, p in self._parsed_profiles.items()}


# Global loader instance for hot reload support
_global_loader: Optional[ProfileLoader] = None


def get_profile_loader() -> ProfileLoader:
    """Get or create the global profile loader."""
    global _global_loader
    if _global_loader is None:
        _global_loader = ProfileLoader()
        _global_loader.reload()
    return _global_loader


def reload_profiles() -> Dict[str, Any]:
    """Reload all profiles from markdown files.
    
    Returns:
        Summary of the reload operation.
    """
    loader = get_profile_loader()
    return loader.reload()


def get_loaded_profiles() -> Sequence[InstructionProfile]:
    """Get all currently loaded instruction profiles."""
    return get_profile_loader().profiles


def get_profile_checklist(profile_name: str) -> Optional[ProfileChecklist]:
    """Get the checklist for a specific profile."""
    return get_profile_loader().get_checklist(profile_name)
