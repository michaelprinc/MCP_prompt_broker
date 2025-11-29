# MCP Prompt Broker

An MCP (Model Context Protocol) server that manages and serves instruction profiles from markdown files. Features hot-reload capability for seamless updates without server restart.

## Features

- **Hot-reload**: Automatically detects changes to instruction profiles
- **Markdown parsing**: Extracts metadata, sections, and checklists from `.md` files
- **Metadata caching**: Parses profiles into JSON format for fast access
- **Scalable**: Designed to handle many profiles efficiently

## Installation

```bash
npm install
npm run build
```

## Usage

### Running the Server

```bash
npm start
```

Or with a custom profiles directory:

```bash
PROFILES_DIR=/path/to/profiles npm start
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `list_profiles` | List all available instruction profiles with their metadata |
| `get_profile_content` | Get the full markdown content of a specific profile |
| `get_profile_checklist` | Get the checklist items from a specific profile |
| `get_profile_metadata` | Get detailed metadata about a profile including sections |
| `reload_profiles` | Manually trigger a reload of all profiles |

## Profile Format

Profiles are markdown files placed in the `copilot-profiles` directory. They follow a structured format:

```markdown
# Profile Name

Brief description of the profile.

## Section Heading

Section content...

## Checklist

- [ ] Unchecked item
- [x] Checked item
```

### Parsed Metadata

Each profile is parsed into:

- **id**: Derived from filename (lowercase, spaces replaced with hyphens)
- **name**: Extracted from H1 heading
- **description**: First paragraph after title
- **sections**: All markdown sections with their content
- **checklist**: All checkbox items (`- [ ]` or `- [x]`)
- **lastModified**: File modification timestamp

## Project Structure

```
├── src/
│   ├── index.ts          # MCP server entry point
│   ├── parser.ts         # Markdown parsing utilities
│   └── profile-manager.ts # Profile loading and hot-reload
├── copilot-profiles/     # Instruction profile markdown files
├── tests/                # Test files
└── dist/                 # Compiled JavaScript (generated)
```

## Development

```bash
# Build the project
npm run build

# Run in development mode (watch)
npm run dev

# Run tests
npm test

# Lint (type-check)
npm run lint
```

## MCP Client Configuration

Add this server to your MCP client configuration:

```json
{
  "mcpServers": {
    "prompt-broker": {
      "command": "node",
      "args": ["/path/to/dist/index.js"],
      "env": {
        "PROFILES_DIR": "/optional/custom/path"
      }
    }
  }
}
```

## License

ISC
