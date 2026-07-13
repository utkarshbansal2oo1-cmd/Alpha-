/**
 * Generic HTML adapter -- the SDK's fallback for DOM inputs. Uses only
 * widely-adopted, platform-agnostic conventions (Open Graph meta tags,
 * page <title>, common class-name *fragments* like "headline"/"company"/
 * "location"/"skill") rather than any single site's markup. Registered at
 * a low, below-default priority so any more specific adapter (a future
 * site adapter, or the JSON-LD adapter when present) wins first refusal.
 *
 * This is a refactor of Sprint 12's content-scripts/adapters/
 * generic-heuristic.js into the Sprint 13 SDK's lifecycle shape -- same
 * detection heuristic, now expressed as detect()/extract()/normalize().
 */
const loadSdkModule = typeof require !== "undefined" ? require("./_sdk-import") : window.__AlphaSourceLoadSdkModule;
const { defineAdapter } = loadSdkModule("base-adapter");

function meta(document, name) {
  const el =
    document.querySelector(`meta[property="${name}"]`) ||
    document.querySelector(`meta[name="${name}"]`);
  return el ? el.getAttribute("content") : null;
}

function firstMatch(document, selectors) {
  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (el && el.textContent?.trim()) return el.textContent.trim();
  }
  return null;
}

function firstMatchEl(document, selectors) {
  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (el && el.textContent?.trim()) return [el];
  }
  return [];
}

function looksLikeProfilePage(document) {
  const ogType = meta(document, "og:type");
  if (ogType === "profile") return 0.7;

  const title = meta(document, "og:title") || document.title || "";
  const hasNameShapedTitle = /^[A-Z][a-z]+\s+[A-Z][a-z]+/.test(title.trim());
  const hasHeadlineIsh = firstMatch(document, [
    '[class*="headline" i]',
    '[class*="job-title" i]',
    '[class*="position" i]',
  ]);
  if (hasNameShapedTitle && (hasHeadlineIsh || meta(document, "og:description"))) {
    return 0.45; // deliberately below the JSON-LD adapter's confidence
  }
  return 0;
}

const genericHtmlAdapter = defineAdapter({
  name: "generic-html",
  priority: -10, // fallback: runs after any more specific adapter
  inputKinds: ["dom"],

  detect(input) {
    return looksLikeProfilePage(input.payload);
  },

  extract(input) {
    const document = input.payload;
    const title = meta(document, "og:title") || document.title || "";
    const headline = firstMatch(document, [
      '[class*="headline" i]',
      '[class*="job-title" i]',
      '[class*="position" i]',
    ]);
    const company = firstMatch(document, [
      '[class*="company" i]',
      '[class*="employer" i]',
      '[class*="organization" i]',
    ]);
    const location = firstMatch(document, [
      '[class*="location" i]',
      '[class*="address" i]',
    ]);
    const skillEls = Array.from(document.querySelectorAll('[class*="skill" i]'))
      .map((el) => el.textContent?.trim())
      .filter((t) => t && t.length < 40);

    return {
      name: title.trim() || null,
      headline: headline || null,
      role: headline || null,
      current_company: company || null,
      location: location || null,
      summary: meta(document, "og:description") || null,
      public_profile_url: document.location?.href || input.meta?.url || null,
      skills: Array.from(new Set(skillEls)).slice(0, 25),
    };
  },

  normalize(raw) {
    return {
      name: raw.name,
      role: raw.role || undefined,
      headline: raw.headline || undefined,
      current_company: raw.current_company || undefined,
      skills: raw.skills || [],
      location: raw.location || undefined,
      summary: raw.summary || undefined,
      education: [],
      public_profile_url: raw.public_profile_url || undefined,
      resume_link: undefined,
    };
  },

  // Debug-mode only (see adapter-sdk/debug/inspector.js) -- the elements
  // this adapter actually read from, so the overlay can highlight them.
  locateElements(input) {
    const document = input.payload;
    return [
      ...firstMatchEl(document, ['[class*="headline" i]', '[class*="job-title" i]', '[class*="position" i]']),
      ...firstMatchEl(document, ['[class*="company" i]', '[class*="employer" i]', '[class*="organization" i]']),
      ...firstMatchEl(document, ['[class*="location" i]', '[class*="address" i]']),
      ...Array.from(document.querySelectorAll('[class*="skill" i]')),
    ].filter(Boolean);
  },
});

if (typeof module !== "undefined" && module.exports) {
  module.exports = { genericHtmlAdapter };
}
if (typeof window !== "undefined") {
  window.__AlphaSourceSDK = Object.assign(window.__AlphaSourceSDK || {}, {
    adapters: Object.assign((window.__AlphaSourceSDK && window.__AlphaSourceSDK.adapters) || {}, {
      genericHtml: genericHtmlAdapter,
    }),
  });
}
