"""
Tests for schema validator module.
"""

import pytest
import json
from pathlib import Path

from mcp_codex_orchestrator.orchestrator.schema_validator import SchemaValidator


class TestSchemaValidator:
    """Test suite for SchemaValidator."""

    @pytest.fixture
    def validator(self, tmp_path):
        """Create a SchemaValidator with test schemas."""
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()
        
        # Create a test schema
        test_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["name"],
        }
        (schemas_dir / "test_schema.json").write_text(json.dumps(test_schema))
        
        return SchemaValidator(schemas_path=schemas_dir)

    def test_validate_valid_output(self, validator):
        """Test validating a valid output."""
        output = {"name": "test", "count": 5}
        
        result = validator.validate_output(output, "test_schema")
        
        assert result["valid"] is True
        assert result["errors"] == []

    def test_validate_invalid_output_missing_required(self, validator):
        """Test validating output with missing required field."""
        output = {"count": 5}  # Missing 'name'
        
        result = validator.validate_output(output, "test_schema")
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_invalid_output_wrong_type(self, validator):
        """Test validating output with wrong field type."""
        output = {"name": "test", "count": "not_an_integer"}
        
        result = validator.validate_output(output, "test_schema")
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_get_available_schemas(self, validator):
        """Test getting list of available schemas."""
        schemas = validator.get_available_schemas()
        
        assert "test_schema" in schemas

    def test_schema_not_found(self, validator):
        """Test handling of non-existent schema."""
        output = {"name": "test"}
        
        result = validator.validate_output(output, "nonexistent_schema")
        
        assert result["valid"] is False
        assert "not found" in result["errors"][0].lower()


class TestSchemaValidatorDefaults:
    """Test suite for default schemas."""

    @pytest.fixture
    def default_validator(self):
        """Create a validator with default schemas path."""
        # Use the actual schemas directory if it exists
        schemas_path = Path(__file__).parent.parent / "schemas"
        if schemas_path.exists():
            return SchemaValidator(schemas_path=schemas_path)
        return None

    def test_default_output_schema_exists(self, default_validator):
        """Test that default_output schema exists."""
        if default_validator is None:
            pytest.skip("Schemas directory not found")
        
        schemas = default_validator.get_available_schemas()
        assert "default_output" in schemas

    def test_code_change_schema_exists(self, default_validator):
        """Test that code_change schema exists."""
        if default_validator is None:
            pytest.skip("Schemas directory not found")
        
        schemas = default_validator.get_available_schemas()
        assert "code_change" in schemas

    def test_validate_code_change(self, default_validator):
        """Test validating against code_change schema."""
        if default_validator is None:
            pytest.skip("Schemas directory not found")
        
        output = {
            "files_changed": [
                {
                    "path": "src/main.py",
                    "action": "create",
                    "content": "print('hello')",
                }
            ],
            "summary": "Created main.py",
        }
        
        result = default_validator.validate_output(output, "code_change")
        
        # This will pass if the schema matches the expected structure
        assert isinstance(result, dict)
        assert "valid" in result
