# Shared Utilities

This directory is reserved for shared code that can be used across multiple packages in the workspace.

## Current Status

**Empty** - No shared utilities have been extracted yet.

## Future Contents

When common patterns emerge across packages, they will be placed here:

- Common data models
- Shared logging utilities  
- Cross-package configuration
- Utility functions

## Usage

Packages can depend on shared utilities by adding them to their dependencies:

```toml
[project]
dependencies = [
    "mcp-prompt-broker-shared",  # future
]
```
