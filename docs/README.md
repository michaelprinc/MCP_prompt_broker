# GitHub Agents Directory

This directory contains custom agent definitions for GitHub Copilot Chat.

## Companion Agent

The **Companion** agent is automatically installed here during the installation process (`install.ps1`).

Files installed:
- `companion-instructions.md` - Detailed instructions for the Companion agent
- `companion-agent.json` - Agent definition and metadata (reference)

## Usage

After running `install.ps1`, the Companion agent is available in GitHub Copilot Chat:

```
@companion <your request>
```

## Manual Installation

If you need to manually reference the agent instructions in VS Code settings:

```json
{
  "github.copilot.chat.codeGeneration.instructions": [
    {
      "text": "file:///<absolute-path>/.github/agents/companion-instructions.md"
    }
  ]
}
```

## Documentation

See [User Guide](../../docs/USER_GUIDE.md#companion-custom-agent) for detailed usage instructions.
