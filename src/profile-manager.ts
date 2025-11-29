import * as path from "path";
import * as fs from "fs";
import { watch, type FSWatcher } from "chokidar";
import { EventEmitter } from "events";
import type { ProfileMetadata } from "./parser.js";
import {
  parseMarkdownProfile,
  loadProfilesFromDirectory,
  profileToJSON,
} from "./parser.js";

/**
 * ProfileManager handles loading, caching, and hot-reloading of profiles
 */
export class ProfileManager extends EventEmitter {
  private profiles: Map<string, ProfileMetadata> = new Map();
  private profilesDirectory: string;
  private metadataPath: string;
  private watcher: FSWatcher | null = null;

  constructor(profilesDirectory: string) {
    super();
    this.profilesDirectory = path.resolve(profilesDirectory);
    this.metadataPath = path.join(this.profilesDirectory, "metadata.json");
  }

  /**
   * Initialize the profile manager and start watching for changes
   */
  async initialize(): Promise<void> {
    // Ensure directory exists
    if (!fs.existsSync(this.profilesDirectory)) {
      fs.mkdirSync(this.profilesDirectory, { recursive: true });
    }

    // Load all profiles
    await this.reloadProfiles();

    // Start watching for changes
    this.startWatching();
  }

  /**
   * Reload all profiles from the directory
   */
  async reloadProfiles(): Promise<void> {
    this.profiles = loadProfilesFromDirectory(this.profilesDirectory);
    await this.saveMetadata();
    this.emit("profiles-reloaded", this.listProfiles());
  }

  /**
   * Start watching the profiles directory for changes
   */
  private startWatching(): void {
    if (this.watcher) {
      return;
    }

    this.watcher = watch(
      path.join(this.profilesDirectory, "*.md"),
      {
        ignoreInitial: true,
        persistent: true,
      }
    );

    this.watcher.on("add", (filePath: string) => this.handleFileChange(filePath, "add"));
    this.watcher.on("change", (filePath: string) =>
      this.handleFileChange(filePath, "change")
    );
    this.watcher.on("unlink", (filePath: string) =>
      this.handleFileDelete(filePath)
    );

    this.watcher.on("error", (error: unknown) => {
      console.error("Watcher error:", error);
      this.emit("error", error);
    });
  }

  /**
   * Handle file addition or change
   */
  private async handleFileChange(
    filePath: string,
    eventType: "add" | "change"
  ): Promise<void> {
    try {
      const profile = parseMarkdownProfile(filePath);
      this.profiles.set(profile.id, profile);
      await this.saveMetadata();
      this.emit("profile-updated", profile, eventType);
    } catch (error) {
      console.error(`Error handling file ${eventType}:`, error);
      this.emit("error", error);
    }
  }

  /**
   * Handle file deletion
   */
  private async handleFileDelete(filePath: string): Promise<void> {
    const fileName = path.basename(filePath, ".md");
    const profileId = fileName.toLowerCase().replace(/\s+/g, "-");

    if (this.profiles.has(profileId)) {
      const profile = this.profiles.get(profileId);
      this.profiles.delete(profileId);
      await this.saveMetadata();
      this.emit("profile-deleted", profile);
    }
  }

  /**
   * Save metadata to JSON file
   */
  private async saveMetadata(): Promise<void> {
    const metadata = {
      lastUpdated: new Date().toISOString(),
      profileCount: this.profiles.size,
      profiles: Array.from(this.profiles.values()).map(profileToJSON),
    };

    fs.writeFileSync(this.metadataPath, JSON.stringify(metadata, null, 2));
  }

  /**
   * Get a profile by ID
   */
  getProfile(profileId: string): ProfileMetadata | undefined {
    return this.profiles.get(profileId);
  }

  /**
   * Get profile content
   */
  getProfileContent(profileId: string): string | null {
    const profile = this.profiles.get(profileId);
    return profile ? profile.rawContent : null;
  }

  /**
   * Get profile checklist
   */
  getProfileChecklist(profileId: string): string[] | null {
    const profile = this.profiles.get(profileId);
    return profile ? profile.checklist : null;
  }

  /**
   * List all profiles (summary information)
   */
  listProfiles(): Array<{
    id: string;
    name: string;
    description: string;
    sectionCount: number;
    checklistCount: number;
  }> {
    return Array.from(this.profiles.values()).map((profile) => ({
      id: profile.id,
      name: profile.name,
      description: profile.description,
      sectionCount: profile.sections.length,
      checklistCount: profile.checklist.length,
    }));
  }

  /**
   * Stop watching for changes and cleanup
   */
  async shutdown(): Promise<void> {
    if (this.watcher) {
      await this.watcher.close();
      this.watcher = null;
    }
  }
}
