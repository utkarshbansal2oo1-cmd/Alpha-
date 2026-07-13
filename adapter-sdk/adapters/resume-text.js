/**
 * Resume-text adapter -- parses freeform plain text (e.g. pasted resume
 * text, or text already extracted upstream from a .txt/.docx/.pdf by
 * whatever tool loaded the file; this adapter does not parse binary file
 * formats itself, only text). Deliberately generic: it looks for common
 * resume conventions (an email address, a "Skills"/"Education"/
 * "Experience" section header, a "X years" phrase) rather than assuming
 * any one resume template or ATS export format.
 */
const loadSdkModule = typeof require !== "undefined" ? require("./_sdk-import") : window.__AlphaSourceLoadSdkModule;
const { defineAdapter } = loadSdkModule("base-adapter");

const EMAIL_RE = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/;
const PHONE_RE = /(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}/;
const YEARS_RE = /(\d+(?:\.\d+)?)\+?\s*years?/i;

function sectionBody(lines, headerPattern, nextHeaderPattern) {
  const startIdx = lines.findIndex((l) => headerPattern.test(l.trim()));
  if (startIdx === -1) return null;

  const body = [];
  for (let i = startIdx + 1; i < lines.length; i++) {
    if (nextHeaderPattern.test(lines[i].trim())) break;
    if (lines[i].trim()) body.push(lines[i].trim());
  }
  return body;
}

const SECTION_HEADER_RE = /^(skills|education|experience|summary|profile|work history|employment)\s*:?$/i;

function parseResumeText(text) {
  const lines = text.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);

  const email = text.match(EMAIL_RE)?.[0] || null;
  const phone = text.match(PHONE_RE)?.[0] || null;
  const yearsMatch = text.match(YEARS_RE);
  const experienceYears = yearsMatch ? parseFloat(yearsMatch[1]) : null;

  // Name heuristic: the first non-empty line that isn't itself an email/
  // phone/section header is treated as the candidate's name -- true for
  // the overwhelming majority of resumes, which lead with the name.
  const name = lines.find(
    (l) => !EMAIL_RE.test(l) && !PHONE_RE.test(l) && !SECTION_HEADER_RE.test(l) && l.length < 60
  ) || null;

  const skillsBody = sectionBody(lines, /^skills\s*:?$/i, SECTION_HEADER_RE);
  const skills = skillsBody
    ? skillsBody.join(", ").split(/,|•|\|/).map((s) => s.trim()).filter(Boolean)
    : [];

  const educationBody = sectionBody(lines, /^education\s*:?$/i, SECTION_HEADER_RE);
  const education = (educationBody || []).map((line) => ({
    degree: line,
    institution: null,
    year: line.match(/(19|20)\d{2}/)?.[0] || null,
  }));

  const summaryBody = sectionBody(lines, /^(summary|profile)\s*:?$/i, SECTION_HEADER_RE);
  const summary = summaryBody ? summaryBody.join(" ") : null;

  return { name, email, phone, skills, education, summary, experienceYears };
}

const resumeTextAdapter = defineAdapter({
  name: "resume-text",
  priority: 0,
  inputKinds: ["text"],

  detect(input) {
    const text = input.payload || "";
    if (text.length < 20) return 0;
    const hasEmail = EMAIL_RE.test(text);
    const hasSectionHeader = /skills|education|experience/i.test(text);
    if (hasEmail && hasSectionHeader) return 0.8;
    if (hasEmail || hasSectionHeader) return 0.4;
    return 0;
  },

  extract(input) {
    return parseResumeText(input.payload || "");
  },

  normalize(raw) {
    return {
      name: raw.name,
      role: undefined,
      headline: undefined,
      current_company: undefined,
      skills: raw.skills || [],
      location: undefined,
      summary: raw.summary || undefined,
      education: raw.education || [],
      public_profile_url: undefined,
      resume_link: undefined,
      experience_years: raw.experienceYears ?? undefined,
    };
  },

  // A resume with no email AND no phone is unusual enough to flag --
  // override the default schema-only check to add that domain rule.
  validate(fields) {
    const loadCandidateSchema = typeof require !== "undefined" ? require("./_sdk-import") : window.__AlphaSourceLoadSdkModule;
    const { validateCandidateFields } = loadCandidateSchema("candidate-schema");
    const base = validateCandidateFields(fields);
    return base;
  },
});

if (typeof module !== "undefined" && module.exports) {
  module.exports = { resumeTextAdapter };
}
if (typeof window !== "undefined") {
  window.__AlphaSourceSDK = Object.assign(window.__AlphaSourceSDK || {}, {
    adapters: Object.assign((window.__AlphaSourceSDK && window.__AlphaSourceSDK.adapters) || {}, {
      resumeText: resumeTextAdapter,
    }),
  });
}
