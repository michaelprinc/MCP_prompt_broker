import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import {
  parseMarkdownProfile,
  loadProfilesFromDirectory,
  profileToJSON,
} from "../src/parser.js";

describe("Parser", () => {
  let tempDir: string;

  beforeAll(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "mcp-test-"));
  });

  afterAll(() => {
    fs.rmSync(tempDir, { recursive: true });
  });

  describe("parseMarkdownProfile", () => {
    it("should parse a simple markdown file", () => {
      const testFile = path.join(tempDir, "test-profile.md");
      fs.writeFileSync(
        testFile,
        `# Test Profile

A simple test profile for testing.

## Section One

Content for section one.

## Section Two

Content for section two.
`
      );

      const profile = parseMarkdownProfile(testFile);

      expect(profile.id).toBe("test-profile");
      expect(profile.name).toBe("Test Profile");
      expect(profile.description).toBe("A simple test profile for testing.");
      expect(profile.sections).toHaveLength(3);
      expect(profile.sections[0]?.title).toBe("Test Profile");
      expect(profile.sections[1]?.title).toBe("Section One");
      expect(profile.sections[2]?.title).toBe("Section Two");
    });

    it("should extract checklist items correctly", () => {
      const testFile = path.join(tempDir, "checklist-profile.md");
      fs.writeFileSync(
        testFile,
        `# Checklist Profile

## Checklist

- [ ] Item one
- [x] Item two (completed)
- [ ] Item three
`
      );

      const profile = parseMarkdownProfile(testFile);

      expect(profile.checklist).toHaveLength(3);
      expect(profile.checklist[0]).toBe("[ ] Item one");
      expect(profile.checklist[1]).toBe("[x] Item two (completed)");
      expect(profile.checklist[2]).toBe("[ ] Item three");
    });

    it("should handle asterisk-style checklist items", () => {
      const testFile = path.join(tempDir, "asterisk-profile.md");
      fs.writeFileSync(
        testFile,
        `# Asterisk Profile

* [ ] Asterisk item one
* [X] Asterisk item two
`
      );

      const profile = parseMarkdownProfile(testFile);

      expect(profile.checklist).toHaveLength(2);
      expect(profile.checklist[0]).toBe("[ ] Asterisk item one");
      expect(profile.checklist[1]).toBe("[x] Asterisk item two");
    });

    it("should handle different header levels", () => {
      const testFile = path.join(tempDir, "levels-profile.md");
      fs.writeFileSync(
        testFile,
        `# Level 1

## Level 2

### Level 3

#### Level 4
`
      );

      const profile = parseMarkdownProfile(testFile);

      expect(profile.sections).toHaveLength(4);
      expect(profile.sections[0]?.level).toBe(1);
      expect(profile.sections[1]?.level).toBe(2);
      expect(profile.sections[2]?.level).toBe(3);
      expect(profile.sections[3]?.level).toBe(4);
    });
  });

  describe("loadProfilesFromDirectory", () => {
    it("should load all markdown files from directory", () => {
      const profilesDir = path.join(tempDir, "profiles");
      fs.mkdirSync(profilesDir);
      fs.writeFileSync(
        path.join(profilesDir, "profile-a.md"),
        "# Profile A\n\nProfile A content."
      );
      fs.writeFileSync(
        path.join(profilesDir, "profile-b.md"),
        "# Profile B\n\nProfile B content."
      );
      // Non-markdown file should be ignored
      fs.writeFileSync(
        path.join(profilesDir, "not-a-profile.txt"),
        "Not a profile"
      );

      const profiles = loadProfilesFromDirectory(profilesDir);

      expect(profiles.size).toBe(2);
      expect(profiles.has("profile-a")).toBe(true);
      expect(profiles.has("profile-b")).toBe(true);
    });

    it("should return empty map for non-existent directory", () => {
      const profiles = loadProfilesFromDirectory("/non/existent/path");
      expect(profiles.size).toBe(0);
    });
  });

  describe("profileToJSON", () => {
    it("should serialize profile to JSON correctly", () => {
      const testFile = path.join(tempDir, "json-profile.md");
      fs.writeFileSync(
        testFile,
        `# JSON Profile

## Description

A profile to test JSON serialization.

- [ ] Task one
`
      );

      const profile = parseMarkdownProfile(testFile);
      const json = profileToJSON(profile);

      expect(json).toHaveProperty("id", "json-profile");
      expect(json).toHaveProperty("name", "JSON Profile");
      expect(json).toHaveProperty("sections");
      expect(json).toHaveProperty("checklist");
      expect(json).toHaveProperty("lastModified");
    });
  });
});
