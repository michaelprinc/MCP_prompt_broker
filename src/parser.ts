import * as fs from "fs";
import * as path from "path";

/**
 * Represents a section extracted from a markdown file
 */
export interface ProfileSection {
  title: string;
  level: number;
  content: string;
}

/**
 * Represents metadata and content of a profile
 */
export interface ProfileMetadata {
  id: string;
  name: string;
  description: string;
  filePath: string;
  sections: ProfileSection[];
  checklist: string[];
  lastModified: Date;
  rawContent: string;
}

/**
 * Parses a markdown file and extracts metadata and sections
 */
export function parseMarkdownProfile(filePath: string): ProfileMetadata {
  const content = fs.readFileSync(filePath, "utf-8");
  const fileName = path.basename(filePath, ".md");
  const stats = fs.statSync(filePath);

  const sections = extractSections(content);
  const checklist = extractChecklist(content);
  const description = extractDescription(content, sections);

  return {
    id: fileName.toLowerCase().replace(/\s+/g, "-"),
    name: extractTitle(content) || fileName,
    description,
    filePath,
    sections,
    checklist,
    lastModified: stats.mtime,
    rawContent: content,
  };
}

/**
 * Extracts the main title from markdown content
 */
function extractTitle(content: string): string {
  const titleMatch = content.match(/^#\s+(.+)$/m);
  return titleMatch?.[1]?.trim() ?? "";
}

/**
 * Extracts description from content (first paragraph or section description)
 */
function extractDescription(
  content: string,
  sections: ProfileSection[]
): string {
  // Look for content after title but before first section
  const lines = content.split("\n");
  let description = "";
  let foundTitle = false;

  for (const line of lines) {
    if (line.startsWith("# ")) {
      foundTitle = true;
      continue;
    }
    if (foundTitle && line.startsWith("#")) {
      break;
    }
    if (foundTitle && line.trim()) {
      description += line.trim() + " ";
    }
  }

  return description.trim() || (sections[0]?.content.slice(0, 200) || "");
}

/**
 * Extracts all sections from markdown content
 */
function extractSections(content: string): ProfileSection[] {
  const sections: ProfileSection[] = [];
  const lines = content.split("\n");
  let currentSection: ProfileSection | null = null;
  let contentLines: string[] = [];

  for (const line of lines) {
    const headerMatch = line.match(/^(#{1,6})\s+(.+)$/);

    if (headerMatch) {
      // Save previous section
      if (currentSection) {
        currentSection.content = contentLines.join("\n").trim();
        sections.push(currentSection);
      }

      // Start new section
      currentSection = {
        title: headerMatch[2]?.trim() ?? "",
        level: headerMatch[1]?.length ?? 1,
        content: "",
      };
      contentLines = [];
    } else if (currentSection) {
      contentLines.push(line);
    }
  }

  // Save last section
  if (currentSection) {
    currentSection.content = contentLines.join("\n").trim();
    sections.push(currentSection);
  }

  return sections;
}

/**
 * Extracts checklist items from markdown content
 */
function extractChecklist(content: string): string[] {
  const checklistItems: string[] = [];
  const checklistRegex = /^[-*]\s*\[([ xX])\]\s*(.+)$/gm;

  let match;
  while ((match = checklistRegex.exec(content)) !== null) {
    const checkMark = match[1];
    const text = match[2];
    if (checkMark !== undefined && text !== undefined) {
      const isChecked = checkMark.toLowerCase() === "x";
      checklistItems.push(`[${isChecked ? "x" : " "}] ${text.trim()}`);
    }
  }

  return checklistItems;
}

/**
 * Loads all profiles from a directory
 */
export function loadProfilesFromDirectory(
  directory: string
): Map<string, ProfileMetadata> {
  const profiles = new Map<string, ProfileMetadata>();

  if (!fs.existsSync(directory)) {
    return profiles;
  }

  const files = fs.readdirSync(directory);

  for (const file of files) {
    if (file.endsWith(".md")) {
      const filePath = path.join(directory, file);
      try {
        const profile = parseMarkdownProfile(filePath);
        profiles.set(profile.id, profile);
      } catch (error) {
        console.error(`Error parsing profile ${file}:`, error);
      }
    }
  }

  return profiles;
}

/**
 * Serializes profile metadata to JSON (for caching/persistence)
 */
export function profileToJSON(profile: ProfileMetadata): object {
  return {
    id: profile.id,
    name: profile.name,
    description: profile.description,
    filePath: profile.filePath,
    sections: profile.sections,
    checklist: profile.checklist,
    lastModified: profile.lastModified.toISOString(),
  };
}
