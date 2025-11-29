#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import * as path from "path";
import { ProfileManager } from "./profile-manager.js";

// Default profiles directory
const DEFAULT_PROFILES_DIR = path.join(process.cwd(), "copilot-profiles");

async function main(): Promise<void> {
  const profilesDir = process.env.PROFILES_DIR || DEFAULT_PROFILES_DIR;

  // Initialize profile manager
  const profileManager = new ProfileManager(profilesDir);
  await profileManager.initialize();

  // Create MCP server
  const server = new McpServer({
    name: "prompt-broker",
    version: "1.0.0",
  });

  // Tool: list_profiles - List all available profiles
  server.tool(
    "list_profiles",
    "List all available instruction profiles with their metadata",
    {},
    async () => {
      const profiles = profileManager.listProfiles();
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(profiles, null, 2),
          },
        ],
      };
    }
  );

  // Tool: get_profile_content - Get full content of a profile
  server.tool(
    "get_profile_content",
    "Get the full markdown content of a specific instruction profile",
    {
      profile_id: z.string().describe("The ID of the profile to retrieve"),
    },
    async ({ profile_id }) => {
      const content = profileManager.getProfileContent(profile_id);

      if (!content) {
        return {
          content: [
            {
              type: "text",
              text: `Profile '${profile_id}' not found. Use list_profiles to see available profiles.`,
            },
          ],
          isError: true,
        };
      }

      return {
        content: [
          {
            type: "text",
            text: content,
          },
        ],
      };
    }
  );

  // Tool: get_profile_checklist - Get the checklist section from a profile
  server.tool(
    "get_profile_checklist",
    "Get the checklist items from a specific instruction profile",
    {
      profile_id: z.string().describe("The ID of the profile to get checklist from"),
    },
    async ({ profile_id }) => {
      const checklist = profileManager.getProfileChecklist(profile_id);

      if (!checklist) {
        return {
          content: [
            {
              type: "text",
              text: `Profile '${profile_id}' not found. Use list_profiles to see available profiles.`,
            },
          ],
          isError: true,
        };
      }

      if (checklist.length === 0) {
        return {
          content: [
            {
              type: "text",
              text: `Profile '${profile_id}' does not have any checklist items.`,
            },
          ],
        };
      }

      return {
        content: [
          {
            type: "text",
            text: checklist.join("\n"),
          },
        ],
      };
    }
  );

  // Tool: reload_profiles - Manually trigger a reload of all profiles
  server.tool(
    "reload_profiles",
    "Reload all instruction profiles from the profiles directory. Use this to manually refresh profiles without restarting the server.",
    {},
    async () => {
      await profileManager.reloadProfiles();
      const profiles = profileManager.listProfiles();

      return {
        content: [
          {
            type: "text",
            text: `Successfully reloaded ${profiles.length} profiles.\n\n${JSON.stringify(profiles, null, 2)}`,
          },
        ],
      };
    }
  );

  // Tool: get_profile_metadata - Get detailed metadata of a profile
  server.tool(
    "get_profile_metadata",
    "Get detailed metadata about a specific instruction profile including sections",
    {
      profile_id: z.string().describe("The ID of the profile to retrieve metadata for"),
    },
    async ({ profile_id }) => {
      const profile = profileManager.getProfile(profile_id);

      if (!profile) {
        return {
          content: [
            {
              type: "text",
              text: `Profile '${profile_id}' not found. Use list_profiles to see available profiles.`,
            },
          ],
          isError: true,
        };
      }

      const metadata = {
        id: profile.id,
        name: profile.name,
        description: profile.description,
        filePath: profile.filePath,
        lastModified: profile.lastModified.toISOString(),
        sections: profile.sections.map((s) => ({
          title: s.title,
          level: s.level,
          contentLength: s.content.length,
        })),
        checklistCount: profile.checklist.length,
      };

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(metadata, null, 2),
          },
        ],
      };
    }
  );

  // Set up event handlers for hot-reload notifications
  profileManager.on("profile-updated", (profile, eventType) => {
    console.error(
      `[Hot Reload] Profile ${eventType}: ${profile.name} (${profile.id})`
    );
  });

  profileManager.on("profile-deleted", (profile) => {
    console.error(`[Hot Reload] Profile deleted: ${profile.name}`);
  });

  profileManager.on("profiles-reloaded", (profiles) => {
    console.error(`[Hot Reload] All profiles reloaded: ${profiles.length} profiles`);
  });

  // Handle shutdown
  process.on("SIGINT", async () => {
    await profileManager.shutdown();
    process.exit(0);
  });

  process.on("SIGTERM", async () => {
    await profileManager.shutdown();
    process.exit(0);
  });

  // Start the server
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error(`MCP Prompt Broker started. Watching: ${profilesDir}`);
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
