# Codex CLI Container
# Lightweight container for running OpenAI Codex CLI

FROM node:20-slim

# Set labels
LABEL maintainer="MCP Prompt Broker Team"
LABEL description="OpenAI Codex CLI runner for MCP Orchestrator"
LABEL version="1.0"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Codex CLI globally
RUN npm install -g @openai/codex

# Use existing 'node' user (UID 1000) from base image for security
# Create directories for mounts with proper ownership
# Also create .codex directory for auth.json (ChatGPT Plus authentication)
RUN mkdir -p /workspace /runs /home/node/.codex && \
    chown -R node:node /workspace /runs /home/node/.codex

# Switch to non-root user
USER node

# Set CODEX_HOME for authentication
ENV CODEX_HOME=/home/node/.codex

# Set working directory
WORKDIR /workspace

# Default environment variables
ENV CODEX_QUIET_MODE=1
ENV NODE_ENV=production

# Entrypoint is the codex CLI
ENTRYPOINT ["codex"]

# Default command (can be overridden)
CMD ["--help"]
