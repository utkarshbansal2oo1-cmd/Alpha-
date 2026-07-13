# Sprint 6 — Executive Demo Polish: Report

Scope respected throughout: no backend modules added, no changes to `backend/app/query_understanding`, `backend/app/search_planner`, `backend/app/knowledge`, or `backend/app/candidate_repository`. This sprint touched `marketing/` only.

## 1. Summary of improvements

- **Guided Demo Mode** (Task 8): a second, fully deterministic mode alongside the existing Live Pipeline mode. Four pre-loaded example queries resolve instantly against a local 50-candidate dataset with zero network calls — nothing to time out, rate-limit, or return an empty/broken result live in front of executives. Live Pipeline mode (the real `/api/search` call) is kept as a toggle for technical audiences.
- **AI Thinking sequence** (Task 2): replaced the 3-label loading state with the full 5-stage sequence you specified (Understanding → Role identified → Expanding → Skills expanded → Building strategy → Plan created → Searching → Candidates discovered → Generating recommendations), each stage with a checkmark, 350–450ms per stage in Guided mode (inside your 300–500ms spec), still gated on the real API response in Live mode.
- **50 realistic candidate profiles** (Task 3): generated programmatically (not hand-copied from real people), spanning all 18 companies you listed, with realistic experience (2.5–14 yrs), career progression (1–3 prior employers with plausible tenure), education (IIT/NIT/BITS/IIIT/IISc), notice periods, certifications, languages, and 2–3 project bullets each.
- **Candidate Profile Drawer** (Task 4): a glass side panel — profile header, notice period, Why Matched, skills, experience timeline, education, projects, certifications, languages, and a resume-preview placeholder that's honest about what's real. Opens on click or keyboard (Enter/Space) from any candidate card, closes on Escape or backdrop click.
- **Micro-interactions** (Task 5): candidate cards now have cursor-tracked glow (matching the feature cards' existing interaction, not a new pattern), hover-lift, and a "View full profile →" affordance that appears on hover; all primary/ghost buttons and nav links got visible focus rings.
- **Accessibility pass** (Task 6): the architecture diagram's hover-only interaction (mouse-only, previously) now also responds to keyboard focus with `tabIndex`/`aria-label` per node; every interactive element (buttons, links, cards, diagram nodes, drawer close button) has a `focus-visible` outline; the drawer is a proper `role="dialog" aria-modal`.
- **Performance** (Task 7): section-level code-splitting was already in place from Sprint 5 and is preserved — see bundle sizes below.

## 2. Screens changed

Only one section required substantive rework: **Live Product Demo** (`LiveDemo.jsx`) — now has a mode toggle, guided example chips, the 5-stage thinking sequence, and drawer integration. `CandidateCard.jsx` gained click/keyboard interactivity and cursor glow. New: `CandidateDrawer.jsx`, `ThinkingSequence.jsx`, `data/candidates.js`, `data/demoScenarios.js`. Small accessibility-only edits: `Nav.jsx`, `GlowButton.jsx`, `GhostButton.jsx`, `EnterpriseArchitecture.jsx`. All other sections (Hero, Problem, Journey, HowItThinks, FeatureShowcase, Vision, Footer) were reviewed and found already consistent with the design system — no changes needed there; nothing in this sprint touched them cosmetically.

## 3. Animations improved

- Thinking sequence: staggered checkmark reveal, `AnimatePresence popLayout` so stages stack cleanly as they complete, spring-based checkmark pop-in.
- Candidate drawer: backdrop fade (250ms) + panel slide-in from the right (400ms, custom ease matching the rest of the site's `[0.16,1,0.3,1]` curve) — consistent with the animation plan's "no bouncing, no exaggerated effects" rule.
- Candidate cards: added `whileHover={{ y: -3 }}` lift (previously static on hover) and cursor-glow, matching `GlassCard`'s existing interaction so the whole site now uses one consistent hover language, not two.

## 4. Performance

Production build (native filesystem — this workspace's Windows-mounted path has a known bus-error issue with esbuild's native binary; builds are run in a scratch native-fs copy and the resulting `dist`/lockfile are what's authoritative):

```
dist/index.html                                   0.72 kB
dist/assets/index-*.css                          22.40 kB  gzip  5.13 kB
dist/assets/useCursorGlow-*.js                    0.91 kB  gzip  0.52 kB
dist/assets/Footer-*.js                           1.13 kB  gzip  0.58 kB
dist/assets/Vision-*.js                           1.84 kB  gzip  0.98 kB
dist/assets/HowItThinks-*.js                      2.16 kB  gzip  1.09 kB
dist/assets/EnterpriseArchitecture-*.js           3.43 kB  gzip  1.69 kB
dist/assets/FeatureShowcase-*.js                  5.08 kB  gzip  2.12 kB
dist/assets/LiveDemo-*.js                        67.41 kB  gzip 12.86 kB
dist/assets/framer-motion-*.js                  122.91 kB  gzip 40.60 kB
dist/assets/index-*.js                          151.02 kB  gzip 48.98 kB
built in 5.61s
```

`LiveDemo`'s chunk grew from ~10kB to ~67kB this sprint because the 50-candidate dataset (`candidates.js`, ~69kB source) is bundled into it — it's still lazy-loaded (only fetched once the user scrolls to/interacts with the demo section), so it does not affect first paint. If this dataset needs to grow further, moving it to a fetched JSON file instead of a bundled JS module would be the next optimization — flagging rather than doing unilaterally since it's a build-architecture change beyond "polish."

**Lighthouse**: this sandbox has no Chrome/Chromium binary available (`which chromium/google-chrome` returned nothing, and installing a full headless Chrome plus `lighthouse` was judged out of scope for a polish sprint), so I could not run and report real Lighthouse numbers — reporting a fabricated score would violate factual-accuracy expectations. What I can state factually: the build has no render-blocking scripts (Vite's default `type="module"` + code-split chunks), no unoptimized images (the site uses zero raster images — everything is CSS/SVG/canvas per the "no stock illustrations" requirement), and semantic HTML with a `<title>` and meta description already in `index.html`. **Recommend running `npx lighthouse http://localhost:4173 --view` locally** (or in CI) after `npm run build && npm run preview` to get real numbers before the executive demo — I'd rather tell you how to get an accurate number than invent one.

## 5. Accessibility report

Fixed this sprint:
- All primary/ghost buttons and nav links: added `focus-visible` rings (previously invisible on keyboard tab).
- Architecture diagram nodes: were mouse-only (`onMouseEnter`/`onMouseLeave`); now also keyboard-operable (`tabIndex`, `onFocus`/`onBlur`, `aria-label` carrying the full description so a screen reader user gets the same info a sighted hovering user does).
- Candidate cards: now real interactive elements (`role="button"`, `tabIndex`, Enter/Space handling, `aria-label`), not divs with an invisible click handler.
- Candidate drawer: `role="dialog"`, `aria-modal="true"`, `aria-label`, closes on Escape, background scroll locked while open.

Not addressed this sprint (flagging, not fixing silently): no skip-to-content link; the nav's link list is hidden entirely below `md` breakpoint with no mobile menu button as a replacement (a mobile visitor loses in-page navigation, though the primary CTA remains reachable) — this is a real gap, but building a mobile nav menu is a small feature addition, and I stayed inside "polish existing screens" rather than adding a new UI pattern without your sign-off.

## 6. Final Lighthouse scores

Not available — no Chrome binary in this environment (see Performance section above for what I verified structurally instead, and the exact command to get real numbers).

## 7. Demo instructions

```
cd marketing
npm install
npm run dev              # http://localhost:5174
```
For the executive presentation itself: open the site, scroll to **Live Product Demo**, and leave the toggle on **Guided Demo** (default) — click any of the four pre-loaded scenario chips for a deterministic, network-free run every time. Use **Live Pipeline** only if you specifically want to demonstrate the real backend to a technical stakeholder (requires the FastAPI backend running on `:8000`, and accepts the small risk of a slow/cold LLM call in front of the room).

Click any candidate card in either mode to open the full profile drawer (Escape or click outside to close).
