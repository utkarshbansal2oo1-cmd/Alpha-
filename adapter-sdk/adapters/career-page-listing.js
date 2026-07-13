/**
 * Company career/team-page listing adapter -- the SDK's one "multi"
 * example: a company "About/Team/Leadership" page usually lists several
 * people as repeated sibling cards (each with a name-shaped heading and a
 * title/role line beneath it). Unlike every other adapter here, this one
 * can return MANY candidates from a single page, so normalize() returns an
 * ARRAY of candidate-field objects rather than one object -- the registry
 * and candidate-schema's validate() both already support that shape (see
 * core/candidate-schema.js's array handling).
 *
 * Detection heuristic is structural, not site-specific: look for a
 * repeated group of siblings (>= 3) that each contain a short, name-shaped
 * heading. No assumption is made about class names beyond the same
 * generic "role/title"-ish fragment used by generic-html.js.
 */
const loadSdkModule = typeof require !== "undefined" ? require("./_sdk-import") : window.__AlphaSourceLoadSdkModule;
const { defineAdapter } = loadSdkModule("base-adapter");

const NAME_SHAPE_RE = /^[A-Z][a-zA-Z'.-]+(\s+[A-Z][a-zA-Z'.-]+){1,2}$/;

function findPersonCards(document) {
  // Candidate "card" headings: h2/h3/h4 (or any element carrying a
  // name/person-ish class) whose text looks like "First Last".
  const headingCandidates = Array.from(
    document.querySelectorAll('h2, h3, h4, [class*="name" i], [class*="person" i]')
  ).filter((el) => NAME_SHAPE_RE.test(el.textContent.trim()));

  // Group by parent so we don't double-count a heading matched by two
  // selectors, and so we can look at each card's surrounding context for
  // a role/title line.
  const seenParents = new Set();
  const cards = [];
  for (const heading of headingCandidates) {
    const card = heading.closest("li, article, div") || heading.parentElement;
    if (!card || seenParents.has(card)) continue;
    seenParents.add(card);
    cards.push({ card, heading });
  }
  return cards;
}

function roleNear(card, heading) {
  // A role/title line is usually the next sibling text node/element after
  // the name heading, within the same card.
  let el = heading.nextElementSibling;
  while (el) {
    const text = el.textContent?.trim();
    if (text && text.length < 80 && !NAME_SHAPE_RE.test(text)) return text;
    el = el.nextElementSibling;
  }
  const fallback = card.querySelector('[class*="title" i], [class*="role" i], [class*="position" i]');
  return fallback?.textContent?.trim() || null;
}

const careerPageListingAdapter = defineAdapter({
  name: "career-page-listing",
  priority: 2,
  inputKinds: ["dom"],
  multi: true,

  detect(input) {
    const cards = findPersonCards(input.payload);
    // Require at least 3 person-shaped cards so this doesn't fire on a
    // single-bio "About the founder" page (which the generic-html/JSON-LD
    // adapters already handle better as a single candidate).
    return cards.length >= 3 ? 0.6 : 0;
  },

  extract(input) {
    const document = input.payload;
    const cards = findPersonCards(document);
    const pageUrl = document.location?.href || input.meta?.url || null;

    return cards.map(({ card, heading }) => ({
      name: heading.textContent.trim(),
      role: roleNear(card, heading),
      public_profile_url: pageUrl,
    }));
  },

  normalize(rawList) {
    return rawList.map((raw) => ({
      name: raw.name,
      role: raw.role || undefined,
      headline: raw.role || undefined,
      current_company: undefined,
      skills: [],
      location: undefined,
      summary: undefined,
      education: [],
      public_profile_url: raw.public_profile_url || undefined,
      resume_link: undefined,
    }));
  },

  // Debug-mode only -- every card element this adapter treated as one
  // candidate, so the overlay can outline each one on the page.
  locateElements(input) {
    const cards = findPersonCards(input.payload);
    return cards.map(({ card }) => card);
  },
});

if (typeof module !== "undefined" && module.exports) {
  module.exports = { careerPageListingAdapter };
}
if (typeof window !== "undefined") {
  window.__AlphaSourceSDK = Object.assign(window.__AlphaSourceSDK || {}, {
    adapters: Object.assign((window.__AlphaSourceSDK && window.__AlphaSourceSDK.adapters) || {}, {
      careerPageListing: careerPageListingAdapter,
    }),
  });
}
