import { Github, Sparkles, FileSpreadsheet, FileText, Building2, Database, Chrome } from "lucide-react";

// Sprint 36: frontend-side mirror of app/discovery/source_groups.py's
// display-name/icon lookup. Deliberately tiny and presentation-only, same
// as the backend module -- this never affects which candidates are shown,
// how they're matched, or how they're ranked, only how a source badge or
// section header looks. An unrecognized source (a brand-new connector
// with no entry here yet) still renders with a sensible generic label and
// icon instead of breaking, mirroring get_source_group_info()'s fallback.
const ICONS_BY_KEY = {
  github: Github,
  greenhouse: Building2,
  sparkles: Sparkles,
  browser: Chrome,
  "file-spreadsheet": FileSpreadsheet,
  "file-text": FileText,
  building: Building2,
  database: Database,
};

// Sprint 36 product requirement: seed_data must never be labeled "Seed"
// to a recruiter -- this label list is the single place that's enforced
// on the frontend, matching the backend's source_groups.py entry.
const SOURCE_LABELS = {
  github: "GitHub",
  greenhouse_ats: "Greenhouse",
  seed_data: "Suggested Profile",
  browser_extension: "Browser Extension",
  csv_import: "CSV Import",
  resume_import: "Resume Database",
  hrms: "Internal ATS",
};

const SOURCE_ICON_KEYS = {
  github: "github",
  greenhouse_ats: "greenhouse",
  seed_data: "sparkles",
  browser_extension: "browser",
  csv_import: "file-spreadsheet",
  resume_import: "file-text",
  hrms: "building",
};

// group.icon on a backend SourceGroup is already one of the icon-key
// strings above -- section headers use this directly.
export function getIconForKey(iconKey) {
  return ICONS_BY_KEY[iconKey] || Database;
}

function titleCase(source) {
  return source.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// A candidate object only ever carries `.source` (e.g. "github",
// "seed_data") -- this is what CandidateCard uses so every card, in every
// context (grouped grid, flat fallback grid, detail drawer, export),
// shows the same provenance badge regardless of which Source Group
// section it happens to be rendered inside.
export function getSourceBadge(source) {
  if (!source) return { label: null, Icon: null };
  const label = SOURCE_LABELS[source] || titleCase(source);
  const Icon = getIconForKey(SOURCE_ICON_KEYS[source] || "database");
  return { label, Icon };
}
