"""Tests for the profile parser and loader functionality."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.mcp_prompt_broker.profile_parser import (
    ProfileLoader,
    ProfileParseError,
    parse_profile_markdown,
    _parse_yaml_frontmatter,
    _extract_section,
    _extract_checklist_items,
)


class TestYamlFrontmatter:
    """Tests for YAML frontmatter parsing."""

    def test_valid_frontmatter_extracted(self) -> None:
        content = """---
name: test_profile
default_score: 5
---

## Instructions

Test instructions here.
"""
        metadata, markdown = _parse_yaml_frontmatter(content)
        assert metadata["name"] == "test_profile"
        assert metadata["default_score"] == 5
        assert "## Instructions" in markdown

    def test_missing_frontmatter_raises_error(self) -> None:
        content = "# Just Markdown\n\nNo frontmatter here."
        with pytest.raises(ProfileParseError, match="Missing YAML frontmatter"):
            _parse_yaml_frontmatter(content)

    def test_invalid_yaml_raises_error(self) -> None:
        content = """---
name: [invalid yaml
---

## Content
"""
        with pytest.raises(ProfileParseError, match="Invalid YAML"):
            _parse_yaml_frontmatter(content)


class TestSectionExtraction:
    """Tests for markdown section extraction."""

    def test_extract_instructions_section(self) -> None:
        content = """## Instructions

This is the instruction content.
With multiple lines.

## Checklist

- [ ] Item 1
"""
        instructions = _extract_section(content, "Instructions")
        assert instructions is not None
        assert "This is the instruction content" in instructions
        assert "Checklist" not in instructions

    def test_missing_section_returns_none(self) -> None:
        content = "## Other Section\n\nContent here."
        result = _extract_section(content, "Instructions")
        assert result is None


class TestChecklistExtraction:
    """Tests for checklist item extraction."""

    def test_checkbox_items_extracted(self) -> None:
        content = """
- [ ] First unchecked item
- [x] Checked item
- [ ] Another unchecked
"""
        items = _extract_checklist_items(content)
        assert len(items) == 3
        assert "First unchecked item" in items
        assert "Checked item" in items

    def test_regular_list_items_as_fallback(self) -> None:
        content = """
- First item
- Second item
- Third item
"""
        items = _extract_checklist_items(content)
        assert len(items) == 3
        assert "First item" in items


class TestProfileParsing:
    """Tests for complete profile parsing."""

    def test_parse_valid_profile(self, tmp_path: Path) -> None:
        profile_content = """---
name: test_profile
short_instructions: Short desc
default_score: 3
fallback: false
required:
  domain:
    - engineering
    - it
weights:
  domain:
    engineering: 2
---

## Instructions

Complete test instructions.

## Checklist

- [ ] Check item 1
- [ ] Check item 2
"""
        profile_file = tmp_path / "test_profile.md"
        profile_file.write_text(profile_content, encoding="utf-8")

        parsed = parse_profile_markdown(profile_file)
        
        assert parsed.profile.name == "test_profile"
        assert parsed.profile.default_score == 3
        assert parsed.profile.fallback is False
        assert "engineering" in parsed.profile.required.get("domain", set())
        assert parsed.profile.weights.get("domain", {}).get("engineering") == 2
        assert "Complete test instructions" in parsed.profile.instructions
        assert len(parsed.checklist.items) == 2

    def test_missing_name_raises_error(self, tmp_path: Path) -> None:
        profile_content = """---
default_score: 1
---

## Instructions

Some instructions.
"""
        profile_file = tmp_path / "invalid.md"
        profile_file.write_text(profile_content, encoding="utf-8")

        with pytest.raises(ProfileParseError, match="Missing 'name'"):
            parse_profile_markdown(profile_file)

    def test_file_not_found_raises_error(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "nonexistent.md"
        with pytest.raises(ProfileParseError, match="not found"):
            parse_profile_markdown(nonexistent)


class TestProfileLoader:
    """Tests for the ProfileLoader class."""

    def test_loader_loads_profiles_from_directory(self, tmp_path: Path) -> None:
        # Create test profiles
        profile1 = """---
name: profile_one
default_score: 1
---

## Instructions

Instructions for profile one.

## Checklist

- [ ] Item A
"""
        profile2 = """---
name: profile_two
default_score: 2
fallback: true
---

## Instructions

Instructions for profile two.
"""
        (tmp_path / "profile_one.md").write_text(profile1, encoding="utf-8")
        (tmp_path / "profile_two.md").write_text(profile2, encoding="utf-8")

        loader = ProfileLoader(tmp_path)
        result = loader.reload()

        assert result["success"] is True
        assert result["profiles_loaded"] == 2
        assert "profile_one" in result["profile_names"]
        assert "profile_two" in result["profile_names"]
        assert len(loader.profiles) == 2

    def test_loader_handles_invalid_files_gracefully(self, tmp_path: Path) -> None:
        # Create one valid and one invalid profile
        valid = """---
name: valid_profile
---

## Instructions

Valid instructions.
"""
        invalid = "Just plain text without frontmatter"
        
        (tmp_path / "valid.md").write_text(valid, encoding="utf-8")
        (tmp_path / "invalid.md").write_text(invalid, encoding="utf-8")

        loader = ProfileLoader(tmp_path)
        result = loader.reload()

        assert result["profiles_loaded"] == 1
        assert len(result["errors"]) == 1
        assert "valid_profile" in result["profile_names"]

    def test_get_checklist_returns_correct_items(self, tmp_path: Path) -> None:
        profile = """---
name: checklist_test
---

## Instructions

Test instructions.

## Checklist

- [ ] First task
- [ ] Second task
- [ ] Third task
"""
        (tmp_path / "checklist_test.md").write_text(profile, encoding="utf-8")

        loader = ProfileLoader(tmp_path)
        loader.reload()
        
        checklist = loader.get_checklist("checklist_test")
        assert checklist is not None
        assert checklist.profile_name == "checklist_test"
        assert len(checklist.items) == 3

    def test_get_checklist_returns_none_for_unknown_profile(self, tmp_path: Path) -> None:
        loader = ProfileLoader(tmp_path)
        loader.reload()
        
        checklist = loader.get_checklist("nonexistent")
        assert checklist is None

    def test_reload_clears_previous_profiles(self, tmp_path: Path) -> None:
        profile = """---
name: original
---

## Instructions

Original instructions.
"""
        (tmp_path / "original.md").write_text(profile, encoding="utf-8")

        loader = ProfileLoader(tmp_path)
        loader.reload()
        assert "original" in [p.name for p in loader.profiles]

        # Remove the file and add a new one
        (tmp_path / "original.md").unlink()
        new_profile = """---
name: replacement
---

## Instructions

Replacement instructions.
"""
        (tmp_path / "replacement.md").write_text(new_profile, encoding="utf-8")

        loader.reload()
        profile_names = [p.name for p in loader.profiles]
        assert "original" not in profile_names
        assert "replacement" in profile_names


class TestActualProfiles:
    """Tests for the actual profile markdown files."""

    def test_actual_profiles_load_successfully(self) -> None:
        loader = ProfileLoader()
        result = loader.reload()
        
        assert result["success"] is True
        assert result["profiles_loaded"] >= 4
        assert "privacy_sensitive" in result["profile_names"]
        assert "creative_brainstorm" in result["profile_names"]
        assert "technical_support" in result["profile_names"]
        assert "general_default" in result["profile_names"]

    def test_all_profiles_have_checklists(self) -> None:
        loader = ProfileLoader()
        loader.reload()
        
        for name in loader.parsed_profiles.keys():
            checklist = loader.get_checklist(name)
            assert checklist is not None, f"Profile {name} should have a checklist"
            assert len(checklist.items) > 0, f"Profile {name} should have checklist items"

    def test_all_profiles_have_instructions(self) -> None:
        loader = ProfileLoader()
        loader.reload()
        
        for profile in loader.profiles:
            assert profile.instructions, f"Profile {profile.name} should have instructions"
            assert len(profile.instructions) > 50, f"Profile {profile.name} should have substantial instructions"
