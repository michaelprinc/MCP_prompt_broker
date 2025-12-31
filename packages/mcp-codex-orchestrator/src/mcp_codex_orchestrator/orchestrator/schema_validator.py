"""
MCP Codex Orchestrator - Schema Validator

Validator pro Codex --output-schema výstupy.
"""

import json
from pathlib import Path
from typing import Any

import structlog
from jsonschema import Draft7Validator, ValidationError, validate

logger = structlog.get_logger(__name__)


class OutputValidationError(Exception):
    """Error validating output against schema."""
    
    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


class SchemaValidator:
    """Validator pro Codex --output-schema výstupy."""
    
    # Default schemas directory relative to package
    SCHEMAS_DIR = Path(__file__).parent.parent.parent.parent / "schemas"
    
    # Default output schema
    DEFAULT_SCHEMA: dict[str, Any] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "changed_files": {
                "type": "array",
                "items": {"type": "string"}
            },
            "commands_run": {
                "type": "array", 
                "items": {"type": "string"}
            },
            "tests_run": {
                "type": "object",
                "properties": {
                    "passed": {"type": "integer"},
                    "failed": {"type": "integer"},
                    "skipped": {"type": "integer"}
                }
            },
            "next_steps": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["summary", "changed_files"]
    }
    
    def __init__(self, schemas_dir: Path | None = None):
        """
        Initialize schema validator.
        
        Args:
            schemas_dir: Custom schemas directory (optional)
        """
        self.schemas_dir = Path(schemas_dir) if schemas_dir else self.SCHEMAS_DIR
        self._cache: dict[str, dict[str, Any]] = {}
    
    def get_schema_path(self, schema_name: str = "default") -> Path:
        """
        Get path to schema file.
        
        Args:
            schema_name: Name of the schema (without _output.json suffix)
            
        Returns:
            Path to schema file
        """
        return self.schemas_dir / f"{schema_name}_output.json"
    
    def load_schema(self, schema_name: str = "default") -> dict[str, Any]:
        """
        Load schema from file or cache.
        
        Args:
            schema_name: Name of the schema
            
        Returns:
            Schema dictionary
            
        Raises:
            FileNotFoundError: If schema file doesn't exist
        """
        if schema_name in self._cache:
            return self._cache[schema_name]
        
        schema_path = self.get_schema_path(schema_name)
        
        if not schema_path.exists():
            logger.warning(
                "Schema file not found, using default",
                schema_name=schema_name,
                path=str(schema_path)
            )
            return self.DEFAULT_SCHEMA
        
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        
        self._cache[schema_name] = schema
        logger.debug("Loaded schema", schema_name=schema_name, path=str(schema_path))
        
        return schema
    
    def validate_output(
        self, 
        output: dict[str, Any], 
        schema_name: str = "default"
    ) -> bool:
        """
        Validate output against schema.
        
        Args:
            output: Output dictionary to validate
            schema_name: Name of the schema to validate against
            
        Returns:
            True if valid
            
        Raises:
            OutputValidationError: If validation fails
        """
        schema = self.load_schema(schema_name)
        
        try:
            validate(instance=output, schema=schema)
            logger.debug("Output validation passed", schema_name=schema_name)
            return True
            
        except ValidationError as e:
            error_path = " -> ".join(str(p) for p in e.absolute_path)
            message = f"Validation failed at '{error_path}': {e.message}"
            
            logger.warning(
                "Output validation failed",
                schema_name=schema_name,
                error=message
            )
            
            raise OutputValidationError(message, errors=[message]) from e
    
    def validate_with_errors(
        self, 
        output: dict[str, Any], 
        schema_name: str = "default"
    ) -> tuple[bool, list[str]]:
        """
        Validate output and return all errors.
        
        Args:
            output: Output dictionary to validate
            schema_name: Name of the schema
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        schema = self.load_schema(schema_name)
        
        validator = Draft7Validator(schema)
        errors = list(validator.iter_errors(output))
        
        if not errors:
            return True, []
        
        error_messages = []
        for error in errors:
            path = " -> ".join(str(p) for p in error.absolute_path) or "root"
            error_messages.append(f"[{path}] {error.message}")
        
        return False, error_messages
    
    def get_available_schemas(self) -> list[str]:
        """
        Get list of available schema names.
        
        Returns:
            List of schema names (without _output.json suffix)
        """
        if not self.schemas_dir.exists():
            return ["default"]
        
        schemas = []
        for path in self.schemas_dir.glob("*_output.json"):
            name = path.stem.replace("_output", "")
            schemas.append(name)
        
        if "default" not in schemas:
            schemas.append("default")
        
        return sorted(schemas)
    
    def create_schema_file(
        self, 
        schema_name: str, 
        schema: dict[str, Any]
    ) -> Path:
        """
        Create a new schema file.
        
        Args:
            schema_name: Name of the schema
            schema: Schema dictionary
            
        Returns:
            Path to created schema file
        """
        self.schemas_dir.mkdir(parents=True, exist_ok=True)
        
        schema_path = self.get_schema_path(schema_name)
        
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)
        
        # Clear cache to pick up new schema
        self._cache.pop(schema_name, None)
        
        logger.info("Created schema file", schema_name=schema_name, path=str(schema_path))
        
        return schema_path


# Convenience functions

def validate_codex_output(
    output: dict[str, Any], 
    schema_name: str = "default"
) -> bool:
    """
    Validate Codex output against schema.
    
    Args:
        output: Output dictionary
        schema_name: Schema name
        
    Returns:
        True if valid
        
    Raises:
        OutputValidationError: If validation fails
    """
    validator = SchemaValidator()
    return validator.validate_output(output, schema_name)


def get_schema_for_task(task_type: str) -> str:
    """
    Get appropriate schema name for task type.
    
    Args:
        task_type: Type of task (e.g., "code_change", "analysis")
        
    Returns:
        Schema name to use
    """
    task_schema_map = {
        "code_change": "code_change",
        "implementation": "code_change",
        "refactor": "code_change",
        "analysis": "analysis_report",
        "review": "analysis_report",
        "audit": "analysis_report",
    }
    
    return task_schema_map.get(task_type.lower(), "default")
