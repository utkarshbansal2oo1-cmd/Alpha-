/**
 * JSON-LD adapter -- parses schema.org "Person" data from
 * <script type="application/ld+json">. A refactor of Sprint 12's
 * generic-schema-org.js into the Sprint 13 SDK's lifecycle shape.
 * Registered above generic-html's priority since a structured, page-author
 * -provided record is more reliable than DOM-heuristic guessing.
 */
const loadSdkModule = typeof require !== "undefined" ? require("./_sdk-import") : window.__AlphaSourceLoadSdkModule;
const { defineAdapter } = loadSdkModule("base-adapter");

function findPersonJsonLd(document) {
  const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
  for (const script of scripts) {
    try {
      const data = JSON.parse(script.textContent);
      const candidates = Array.isArray(data) ? data : [data];
      for (const item of candidates) {
        if (item && (item["@type"] === "Person" || item["@type"]?.includes?.("Person"))) {
          return item;
        }
      }
    } catch (e) {
      continue;
    }
  }
  return null;
}

const jsonLdAdapter = defineAdapter({
  name: "json-ld-person",
  priority: 5,
  inputKinds: ["dom"],

  detect(input) {
    return findPersonJsonLd(input.payload) !== null ? 0.85 : 0;
  },

  extract(input) {
    const document = input.payload;
    const person = findPersonJsonLd(document) || {};
    const jobTitle = person.jobTitle || null;
    const worksFor =
      (typeof person.worksFor === "string" && person.worksFor) || person.worksFor?.name || null;
    const address =
      (typeof person.address === "string" && person.address) ||
      person.address?.addressLocality ||
      null;

    return {
      name: person.name || null,
      headline: jobTitle,
      role: jobTitle,
      current_company: worksFor,
      location: address,
      summary: person.description || null,
      public_profile_url: person.url || document.location?.href || input.meta?.url || null,
      skills: Array.isArray(person.knowsAbout)
        ? person.knowsAbout.filter((s) => typeof s === "string")
        : [],
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
});

if (typeof module !== "undefined" && module.exports) {
  module.exports = { jsonLdAdapter };
}
if (typeof window !== "undefined") {
  window.__AlphaSourceSDK = Object.assign(window.__AlphaSourceSDK || {}, {
    adapters: Object.assign((window.__AlphaSourceSDK && window.__AlphaSourceSDK.adapters) || {}, {
      jsonLd: jsonLdAdapter,
    }),
  });
}
