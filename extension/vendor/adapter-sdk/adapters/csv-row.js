/**
 * CSV-row adapter -- normalizes one already-parsed CSV/spreadsheet row
 * (a plain object of column-name -> value) into candidate fields. This
 * SDK does not ship a CSV *parser* (splitting raw CSV text into rows is a
 * solved problem handled upstream, e.g. by whatever imports a file); this
 * adapter's only job is mapping a row's arbitrary column names onto the
 * canonical candidate schema via a flexible alias table, since real-world
 * exports name columns inconsistently ("Full Name" vs "name" vs
 * "candidate_name").
 */
const loadSdkModule = typeof require !== "undefined" ? require("./_sdk-import") : window.__AlphaSourceLoadSdkModule;
const { defineAdapter } = loadSdkModule("base-adapter");

// Alias table: canonical field -> array of column-name patterns (matched
// case-insensitively, with spaces/underscores/hyphens normalized away).
// Add a new alias here to support a new spreadsheet export's naming
// convention -- no other file needs to change.
const FIELD_ALIASES = {
  name: ["name", "fullname", "candidatename", "full name"],
  role: ["role", "title", "jobtitle", "position", "currenttitle"],
  headline: ["headline", "tagline"],
  current_company: ["currentcompany", "company", "employer", "organization"],
  experience_years: ["experienceyears", "yearsofexperience", "experience", "totalexperience"],
  skills: ["skills", "skillset", "keyskills"],
  location: ["location", "city", "address"],
  summary: ["summary", "bio", "about", "notes"],
  public_profile_url: ["profileurl", "linkedinurl", "publicprofileurl", "profile"],
  resume_link: ["resumelink", "resumeurl", "cvlink"],
};

function normalizeKey(key) {
  return key.toLowerCase().replace(/[\s_-]/g, "");
}

function findValue(row, canonicalField) {
  const aliases = FIELD_ALIASES[canonicalField];
  const rowKeys = Object.keys(row || {});
  for (const rowKey of rowKeys) {
    const normalized = normalizeKey(rowKey);
    if (aliases.includes(normalized)) return row[rowKey];
  }
  return null;
}

function splitList(value) {
  if (Array.isArray(value)) return value;
  if (typeof value !== "string") return [];
  return value.split(/[,;|]/).map((s) => s.trim()).filter(Boolean);
}

const csvRowAdapter = defineAdapter({
  name: "csv-row",
  priority: 0,
  inputKinds: ["row"],

  detect(input) {
    const row = input.payload;
    if (!row || typeof row !== "object" || Array.isArray(row)) return 0;
    return findValue(row, "name") ? 0.75 : 0;
  },

  extract(input) {
    const row = input.payload;
    return {
      name: findValue(row, "name"),
      role: findValue(row, "role"),
      headline: findValue(row, "headline"),
      current_company: findValue(row, "current_company"),
      experience_years: findValue(row, "experience_years"),
      skills: findValue(row, "skills"),
      location: findValue(row, "location"),
      summary: findValue(row, "summary"),
      public_profile_url: findValue(row, "public_profile_url"),
      resume_link: findValue(row, "resume_link"),
    };
  },

  normalize(raw) {
    const experienceRaw = raw.experience_years;
    const experienceYears =
      experienceRaw !== null && experienceRaw !== undefined && experienceRaw !== ""
        ? parseFloat(String(experienceRaw).replace(/[^0-9.]/g, ""))
        : undefined;

    return {
      name: raw.name,
      role: raw.role || undefined,
      headline: raw.headline || undefined,
      current_company: raw.current_company || undefined,
      skills: splitList(raw.skills),
      location: raw.location || undefined,
      summary: raw.summary || undefined,
      education: [],
      public_profile_url: raw.public_profile_url || undefined,
      resume_link: raw.resume_link || undefined,
      experience_years: Number.isFinite(experienceYears) ? experienceYears : undefined,
    };
  },
});

if (typeof module !== "undefined" && module.exports) {
  module.exports = { csvRowAdapter, FIELD_ALIASES };
}
if (typeof window !== "undefined") {
  window.__AlphaSourceSDK = Object.assign(window.__AlphaSourceSDK || {}, {
    adapters: Object.assign((window.__AlphaSourceSDK && window.__AlphaSourceSDK.adapters) || {}, {
      csvRow: csvRowAdapter,
    }),
  });
}
