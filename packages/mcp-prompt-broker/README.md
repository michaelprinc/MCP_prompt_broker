# MCP Prompt Broker

**Intelligent instruction routing for AI agents using the Model Context Protocol**

## Overview

MCP Prompt Broker is a Python-based Model Context Protocol (MCP) server that dynamically selects the optimal instruction profile for user prompts. It enables AI assistants like GitHub Copilot to automatically apply context-specific guidance.

## Installation

```bash
pip install -e .
```

With semantic search support:
```bash
pip install -e ".[semantic]"
```

## Usage

Run as MCP server:
```bash
python -m mcp_prompt_broker
```

## Features

- **Intelligent Routing**: Metadata extraction and rule-based scoring
- **Profile Management**: Markdown-based profiles with hot reload support
- **MCP Integration**: Standard MCP tools for VS Code Copilot Chat
- **Quality Assurance**: Checklists per profile with capability inference

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
