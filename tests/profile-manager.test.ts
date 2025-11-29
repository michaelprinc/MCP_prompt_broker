import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { jest } from "@jest/globals";
import { ProfileManager } from "../src/profile-manager.js";

describe("ProfileManager", () => {
  let tempDir: string;
  let profileManager: ProfileManager;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "mcp-manager-test-"));
    profileManager = new ProfileManager(tempDir);
  });

  afterEach(async () => {
    await profileManager.shutdown();
    fs.rmSync(tempDir, { recursive: true });
  });

  describe("initialization", () => {
    it("should initialize with empty directory", async () => {
      await profileManager.initialize();
      const profiles = profileManager.listProfiles();
      expect(profiles).toHaveLength(0);
    });

    it("should load existing profiles on initialization", async () => {
      fs.writeFileSync(
        path.join(tempDir, "test-profile.md"),
        `# Test Profile

Test description.

## Checklist

- [ ] Task 1
- [ ] Task 2
`
      );

      await profileManager.initialize();
      const profiles = profileManager.listProfiles();

      expect(profiles).toHaveLength(1);
      expect(profiles[0]?.id).toBe("test-profile");
      expect(profiles[0]?.name).toBe("Test Profile");
      expect(profiles[0]?.checklistCount).toBe(2);
    });
  });

  describe("getProfile", () => {
    it("should return undefined for non-existent profile", async () => {
      await profileManager.initialize();
      const profile = profileManager.getProfile("non-existent");
      expect(profile).toBeUndefined();
    });

    it("should return profile metadata for existing profile", async () => {
      fs.writeFileSync(
        path.join(tempDir, "existing-profile.md"),
        `# Existing Profile

Some content.
`
      );

      await profileManager.initialize();
      const profile = profileManager.getProfile("existing-profile");

      expect(profile).toBeDefined();
      expect(profile?.name).toBe("Existing Profile");
    });
  });

  describe("getProfileContent", () => {
    it("should return null for non-existent profile", async () => {
      await profileManager.initialize();
      const content = profileManager.getProfileContent("non-existent");
      expect(content).toBeNull();
    });

    it("should return raw markdown content for existing profile", async () => {
      const markdown = `# Content Profile

This is the raw markdown content.
`;
      fs.writeFileSync(path.join(tempDir, "content-profile.md"), markdown);

      await profileManager.initialize();
      const content = profileManager.getProfileContent("content-profile");

      expect(content).toBe(markdown);
    });
  });

  describe("getProfileChecklist", () => {
    it("should return null for non-existent profile", async () => {
      await profileManager.initialize();
      const checklist = profileManager.getProfileChecklist("non-existent");
      expect(checklist).toBeNull();
    });

    it("should return checklist items for existing profile", async () => {
      fs.writeFileSync(
        path.join(tempDir, "checklist-profile.md"),
        `# Checklist Profile

- [ ] First task
- [x] Second task (done)
- [ ] Third task
`
      );

      await profileManager.initialize();
      const checklist = profileManager.getProfileChecklist("checklist-profile");

      expect(checklist).toHaveLength(3);
      expect(checklist?.[0]).toBe("[ ] First task");
      expect(checklist?.[1]).toBe("[x] Second task (done)");
    });

    it("should return empty array for profile without checklist", async () => {
      fs.writeFileSync(
        path.join(tempDir, "no-checklist.md"),
        `# No Checklist

Just regular content without checklist.
`
      );

      await profileManager.initialize();
      const checklist = profileManager.getProfileChecklist("no-checklist");

      expect(checklist).toEqual([]);
    });
  });

  describe("reloadProfiles", () => {
    it("should reload profiles from directory", async () => {
      await profileManager.initialize();
      expect(profileManager.listProfiles()).toHaveLength(0);

      // Add a profile after initialization
      fs.writeFileSync(
        path.join(tempDir, "new-profile.md"),
        `# New Profile

New profile content.
`
      );

      await profileManager.reloadProfiles();
      const profiles = profileManager.listProfiles();

      expect(profiles).toHaveLength(1);
      expect(profiles[0]?.id).toBe("new-profile");
    });

    it("should emit profiles-reloaded event", async () => {
      await profileManager.initialize();

      const reloadedHandler = jest.fn();
      profileManager.on("profiles-reloaded", reloadedHandler);

      await profileManager.reloadProfiles();

      expect(reloadedHandler).toHaveBeenCalledWith(expect.any(Array));
    });
  });

  describe("metadata file", () => {
    it("should create metadata.json file on initialization", async () => {
      fs.writeFileSync(
        path.join(tempDir, "test.md"),
        "# Test\n\nContent."
      );

      await profileManager.initialize();

      const metadataPath = path.join(tempDir, "metadata.json");
      expect(fs.existsSync(metadataPath)).toBe(true);

      const metadata = JSON.parse(fs.readFileSync(metadataPath, "utf-8"));
      expect(metadata.profileCount).toBe(1);
      expect(metadata.profiles).toHaveLength(1);
    });
  });

  describe("listProfiles", () => {
    it("should return summary information for all profiles", async () => {
      fs.writeFileSync(
        path.join(tempDir, "profile-one.md"),
        `# Profile One

Description one.

## Section

- [ ] Task
`
      );
      fs.writeFileSync(
        path.join(tempDir, "profile-two.md"),
        `# Profile Two

Description two.

## Section A

## Section B
`
      );

      await profileManager.initialize();
      const profiles = profileManager.listProfiles();

      expect(profiles).toHaveLength(2);

      const profile1 = profiles.find((p) => p.id === "profile-one");
      expect(profile1?.name).toBe("Profile One");
      expect(profile1?.checklistCount).toBe(1);

      const profile2 = profiles.find((p) => p.id === "profile-two");
      expect(profile2?.name).toBe("Profile Two");
      expect(profile2?.checklistCount).toBe(0);
    });
  });
});
