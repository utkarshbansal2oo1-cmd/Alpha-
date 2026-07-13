# AlphaSource AI — Marketing Site Design System
Design-only deliverable. No code yet, per brief. Scope: the public marketing/launch site (a new surface, separate from the recruiter product UI already built in `frontend/`). Positioning: enterprise AI infrastructure, not a recruiting tool.

Naming decision, confirmed: lockup is **AlphaSource AI**, with **Powered by AlphaRecrewt** as a small caption beneath the logo — everywhere the wordmark appears (nav, hero, footer), not just the hero. Reasoning: "AlphaSource" alone reads as a company name; "AlphaSource AI" reads as a product category the way "GitHub Copilot" or "Notion AI" do — it tells a CXO what it *is* in the name itself, before they've read a word of copy.

---

## 1. Design System

### 1.1 Design principles (the 5 rules everything below must obey)
1. **Negative space is the luxury signal.** Every section in the Stripe/Linear/Apple reference set spends 40 to 60 percent of viewport height on empty space. Density reads as "startup trying to justify its price." Space reads as "we don't need to convince you."
2. **One idea per screen.** Never show a feature list and an animation and a CTA competing for attention in the same viewport. Scroll is the pacing mechanism.
3. **Motion explains, it doesn't decorate.** Every animation must map to a real system behavior (data flowing, AI reasoning, a plan being built). If an animation can't be explained in one sentence of "this represents X," cut it.
4. **Depth over color.** The premium feeling in this palette comes from glass layers, blur, and glow — not from saturation. Accent colors are used at low opacity almost everywhere; full-saturation accent is reserved for a handful of focal moments (the live demo's "AI understood" reveal, primary CTA hover).
5. **Real product, not a mockup screenshot.** Section 4 embeds the actual working app (already built, tested, 110 passing tests) — this is the single biggest trust signal available and the entire site should be paced to build anticipation toward it.

### 1.2 Layout system
- 12-column grid, max content width 1280px, gutters 32px desktop / 20px mobile.
- Vertical rhythm: sections are 100vh (hero, demo) or auto-height with min 720px (feature/architecture sections), separated by 160px of breathing room — never a hard border between sections; transitions are gradient-fade or scroll-triggered reveal.
- Section background alternates between three "depth planes" (see Color System 3.3) so the page has visible strata without ever using a horizontal rule.

### 1.3 Elevation / glassmorphism spec
- **Plane 0 (base):** `#050816`, no blur, the canvas everything sits on.
- **Plane 1 (ambient panels):** `background: rgba(255,255,255,0.02)`, `backdrop-filter: blur(20px)`, `border: 1px solid rgba(255,255,255,0.06)`. Used for large section containers.
- **Plane 2 (cards):** `background: rgba(255,255,255,0.04)`, `backdrop-filter: blur(24px)`, `border: 1px solid rgba(255,255,255,0.08)`, subtle inner glow on hover via a radial gradient mask following cursor position.
- **Plane 3 (focal / demo container):** `background: rgba(255,255,255,0.06)`, 1px border with a gradient (blue→purple→cyan at 15% opacity), soft outer glow (`box-shadow: 0 0 80px rgba(59,130,246,0.08)`). Reserved for the live demo and hero headline card only — using this everywhere would flatten its impact.

---

## 2. Component Hierarchy

```
App (marketing site — new, separate from recruiter product frontend/)
├── Nav (sticky, glass, condenses on scroll)
│   ├── Logo lockup: "AlphaSource AI" + "Powered by AlphaRecrewt" caption
│   ├── NavLinks (Product, Architecture, Vision, Enterprise)
│   └── CTA (Request Access — ghost button, not filled; filled is reserved for hero)
│
├── Hero
│   ├── NeuralNetworkBackground (canvas/SVG, animated nodes + connection lines)
│   ├── HeadlineBlock (staggered word-reveal animation)
│   ├── SubheadBlock
│   ├── CTAGroup (Live Demo — primary glow button; Watch Architecture — ghost button, scrolls to §3)
│   └── ScrollIndicator (single animated chevron, fades out after first scroll)
│
├── ProblemComparison
│   ├── TraditionalPath (vertical node chain, desaturated, "heavy" motion — nodes drop with weight/friction)
│   └── AlphaSourcePath (vertical node chain, accent-lit, "light" motion — nodes arrive with ease, faster)
│   (both animate in parallel on scroll-into-view, so the contrast in motion quality IS the argument)
│
├── HowItThinks (pipeline visualization)
│   └── PipelineNode × 6 (Recruiter Query → AI Understanding → Knowledge Intelligence →
│       Search Planner → Candidate Intelligence → Explainable Results)
│       — connected by an animated flow-line (a pulse of light travels node-to-node on scroll)
│
├── LiveDemo  ← centerpiece
│   ├── DemoFrame (Plane 3 container, embeds the real AlphaSource React app)
│   ├── SearchInput (same component as product, restyled to match marketing chrome)
│   ├── AIUnderstoodReveal (animated panel — reuses real product data/logic)
│   ├── CandidateCardsReveal (staggered card entrance)
│   └── WhyMatchedReveal (inline expansion, reuses real "Why Matched" logic)
│
├── FeatureShowcase
│   └── FeatureCard × 6 (AI Query Understanding, Knowledge Intelligence, Explainable AI,
│       Enterprise Ready, Multi-source Search, AlphaRecrewt Integration)
│       — 3×2 grid desktop, glow-on-hover via cursor-tracked radial gradient
│
├── EnterpriseArchitecture
│   └── ArchitectureDiagram (custom SVG, interactive)
│       — hover any node → connected edges highlight + description panel slides in
│
├── Vision / Roadmap
│   ├── TodayMarker (MVP — solid, lit)
│   └── TomorrowTrack (AlphaRecrewt Integration, Resume Intelligence, AI Ranking,
│       LinkedIn / ATS / GitHub — rendered as a horizontal timeline, dimmer/outlined nodes,
│       "coming" state communicated through opacity and dashed connectors, not text badges)
│
└── Footer
    ├── Logo lockup (repeated, smaller)
    ├── Minimal link columns (Product / Company / Legal)
    └── Closing line: tagline restated, no CTA (the CTA moment already happened in hero + demo)
```

### 2.2 Why the Live Demo reuses real product code, not a mockup
The recruiter product (`frontend/src`) already has working `searchCandidates`, the "AI understood" panel, and "Why Matched" logic, all tested. The marketing site should import and restyle those components rather than rebuild fake versions — this is both less work and more honest (an exec who opens dev tools sees a real network call, not a canned JSON demo). This is a design decision worth flagging before implementation: it means the marketing site needs the backend reachable (or a lightweight demo-mode API), which is a build decision for the approval step, not a redesign of anything already frozen.

---

## 3. Page Wireframe (text-form, section by section)

**Hero (100vh)**
```
[nav - fixed, transparent→glass on scroll]

        (neural network canvas fills entire viewport, low opacity, behind everything)

              AlphaSource AI
              Powered by AlphaRecrewt              <- small, letter-spaced caption

     Stop Searching.
     Start Hiring Intelligently.                   <- massive, two-line headline

     Describe the candidate you need.
     AI understands your intent.
     Finds the best talent.
     Explains every recommendation.                <- 4-line subhead, thin weight, muted

        [ Live Demo ]      [ Watch Architecture ]

                    ⌄ scroll
```

**Problem (auto height, ~900px)**
```
        The old way costs you the best candidates.

  Traditional Hiring                    AlphaSource
  LinkedIn                              Recruiter
    ↓                                     ↓
  Naukri                                AI Understanding
    ↓                                     ↓
  ATS                                   Talent Intelligence
    ↓                                     ↓
  Excel                                 Best Candidates
    ↓
  Manual Filtering
    ↓
  Interviews
    ↓
  Hiring
```
(left column: 7 nodes, heavy/gray, slow drop-in; right column: 4 nodes, lit, fast ease-in — visually the right side finishes animating well before the left side, reinforcing "faster" without a single word of copy claiming it)

**How AlphaSource Thinks (auto height, ~800px)**
```
        How AlphaSource Thinks

  ○ Recruiter Query
  │  (pulse travels down)
  ○ AI Understanding
  │
  ○ Knowledge Intelligence
  │
  ○ Search Planner
  │
  ○ Candidate Intelligence
  │
  ○ Explainable Results
```

**Live Demo (100vh, centerpiece)**
```
        Try it. Right now.

  ┌────────────────────────────────────────┐
  │  [ search box, glass, glowing focus ]   │
  │                                          │
  │  AI Understood:  Role · Skills · ...    │  <- fades in after search
  │  ┌────────┐ ┌────────┐ ┌────────┐       │
  │  │Candidate│ │Candidate│ │Candidate│     │  <- staggered card entrance
  │  │Why match│ │Why match│ │Why match│     │
  │  └────────┘ └────────┘ └────────┘       │
  └────────────────────────────────────────┘
```

**Feature Showcase (auto height)**
```
        Built for how enterprises actually hire.

  [AI Query Understanding]  [Knowledge Intelligence]  [Explainable AI]
  [Enterprise Ready]        [Multi-source Search]     [AlphaRecrewt Integration]
```

**Enterprise Architecture (auto height, ~900px)**
```
        A system, not a script.

        [interactive SVG diagram — hover a node, its description
         slides in to the right, connected edges glow]
```

**Vision (auto height, ~700px)**
```
        Where this goes.

  ● Today (MVP)  ─ ─ ○ AlphaRecrewt   ─ ─ ○ Resume        ─ ─ ○ LinkedIn / ATS / GitHub
                        Integration          Intelligence         AI Ranking
```

**Footer**
```
  AlphaSource AI
  Powered by AlphaRecrewt

  Product   Company   Legal

  Stop searching. Start hiring intelligently.
```

---

## 4. Animation Plan (Framer Motion)

| Element | Trigger | Behavior | Duration/Easing |
|---|---|---|---|
| Nav | scroll > 40px | background opacity 0→0.8, blur 0→20px | 300ms ease-out |
| Hero headline | mount | words split + staggered `y: 20→0, opacity: 0→1` | 60ms stagger, 600ms ease-out per word |
| Hero neural network | continuous | nodes drift on slow randomized paths, connection lines fade in/out as nodes pass near each other | infinite, 8-20s per node loop, no easing (linear, so it never feels like it's "arriving") |
| Hero CTA glow (primary) | hover | radial gradient glow expands behind button | 200ms ease-out |
| Scroll indicator | mount → first scroll | gentle bounce, then fade out permanently | loop until scroll event |
| Problem section nodes | scroll into view (viewport 60%) | left column: `y:-10→0` with slight overshoot spring (heavy feel); right column: `y:-10→0` linear ease (light feel) | left: spring damping 8; right: 250ms ease-out, both column staggered top-to-bottom |
| Pipeline nodes (§3) | scroll into view | node scale 0.8→1 + opacity, then a light pulse travels down the connecting line to the next node | node: 400ms; pulse: 800ms per segment, sequential |
| Live demo container | scroll into view | container fades/scales in first (establishes the "frame"), then is ready for real interaction — no animation on the embedded app itself beyond what the product already does | 500ms ease-out |
| AI Understood reveal | after search resolves | slide down + fade, existing product transition, unchanged | per existing product code |
| Candidate cards | after AI Understood settles | staggered fade+slide-up, 80ms per card | existing product pattern, kept |
| Feature cards | scroll into view | fade+slide-up staggered by grid position (row by row) | 400ms, 100ms stagger |
| Feature card | hover | cursor-tracked radial glow via CSS custom properties updated on mousemove; card border brightens | glow: instant follow; border: 200ms |
| Architecture diagram | hover node | connected edges: stroke-opacity 0.2→1; description panel: slide-in from right, 20px→0 | 250ms ease-out |
| Roadmap nodes | scroll into view | "today" node: solid fill animates in with a confirming pulse (this is real, done); "tomorrow" nodes: fade to 40% opacity, dashed line draws left-to-right via stroke-dashoffset | today: 400ms; roadmap line: 1200ms ease-in-out |
| Section transitions (all) | scroll | fade + 40px translate-y on enter, no exit animation (avoid flicker) | 500-700ms depending on section size |

**Explicitly avoided:** parallax on text (readability risk), particle explosions, autoplay video, scroll-jacking (locking scroll to play an animation) — these read as "trying too hard" and violate principle 3 (motion must explain, not decorate). Regular parallax is used *only* on the hero background layer (moves slower than foreground content by ~30%), nowhere else.

---

## 5. Color System

**Base**
- `--bg-base: #050816` — primary background, plane 0
- `--bg-plane-1: rgba(255,255,255,0.02)` 
- `--bg-plane-2: rgba(255,255,255,0.04)`
- `--bg-plane-3: rgba(255,255,255,0.06)`

**Accent (used at low opacity for backgrounds/borders, full saturation only for focal glows and primary CTA)**
- `--accent-blue: #3B82F6` (electric blue)
- `--accent-purple: #8B5CF6`
- `--accent-cyan: #22D3EE`
- Primary gradient: `linear-gradient(135deg, #3B82F6 0%, #8B5CF6 50%, #22D3EE 100%)` — used on: primary CTA background, active pipeline pulse, hero headline's single accent word (if any), progress/today marker in roadmap. Never used as a full-section background — always a thin border, a glow, or a small focal element.

**Text**
- `--text-primary: #F8FAFC` (near-white, not pure white — pure white against #050816 is harsh)
- `--text-secondary: #94A3B8`
- `--text-tertiary: #64748B` (captions, "Powered by AlphaRecrewt" line)

**Semantic (borrowed sparingly from product UI, not decorative)**
- Success/match: `#34D399` (used only inside the live demo's "Why Matched" reveal, consistent with the existing product's `emerald` styling — don't introduce a second success color)

**Contrast note:** `--text-secondary` on `--bg-base` is ~4.6:1 (WCAG AA for normal text), `--text-tertiary` is ~3.3:1 — acceptable for captions/labels only, not body copy. This matters for an enterprise buyer audience that includes accessibility-conscious procurement teams.

---

## 6. Typography System

- **Typeface:** a single grotesque-style sans (e.g., Inter or a licensed alternative like Söhne/General Sans — final pick is a build-time decision, not a design-system decision) for everything. No serif, no second display face — Linear/Vercel/Arc all commit to one typeface family precisely because switching fonts mid-page is the fastest way to look template-based.
- **Scale** (desktop / mobile):
  - Hero headline: 88px/1.05 / 44px/1.1, weight 700, tracking -2%
  - Section headline: 56px/1.1 / 32px/1.15, weight 700, tracking -1.5%
  - Subhead / body-large: 22px/1.5 / 18px/1.5, weight 400, `--text-secondary`
  - Body: 16px/1.6, weight 400
  - Caption ("Powered by AlphaRecrewt", labels): 13px/1.4, weight 500, tracking +8%, uppercase, `--text-tertiary`
- **Rule:** never more than 2 font weights visible in a single viewport (e.g., 700 headline + 400 body). A third weight (500, for captions/nav) is allowed only because captions are visually separated from the primary reading flow.

---

## 7. Illustration Concepts (all custom SVG/canvas, zero stock assets, nothing recruitment-themed)

1. **Neural Network Hero Background** — nodes are abstract circles (not "candidate avatars" or people icons — this is the single most important rule: no headshots, no resume icons, no briefcase icons anywhere on this site). Connection lines drawn with animated SVG `stroke-dashoffset` so they appear to "grow" between nodes. Occasional lines pulse brighter to suggest active reasoning.
2. **Pipeline Nodes (§3)** — each node is a minimal geometric glyph, not an icon-library icon: e.g., "AI Understanding" is a node with a subtly rotating inner ring (suggesting parsing/comprehension), "Knowledge Intelligence" is a node with 3 smaller satellite nodes orbiting it (suggesting the taxonomy/expansion graph — this is a direct, honest visual metaphor for what the Knowledge Engine actually does, not decoration).
3. **Problem Comparison Chains** — traditional side uses straight, rigid, right-angled connector lines (bureaucratic feel); AlphaSource side uses smooth bezier curves (fluid, intelligent feel). Same shape language, different line quality — a subtle, confident way to argue "this is better" visually.
4. **Architecture Diagram (§6)** — an isometric-flavored (not literal 3D) system diagram: recruiter input on the left, four processing modules as glass cards in the middle (Query Understanding, Knowledge Engine, Search Planner, Candidate Repository — the exact four real modules, not invented ones), output on the right. This is the one illustration that should map 1:1 to the real, already-built system, since technical buyers (CTOs, engineering leaders in the audience) will recognize honesty vs. hand-waving here.
5. **Roadmap Track** — a single horizontal line with nodes; "today" node rendered solid and slightly larger; future nodes rendered as outlined circles at reduced opacity, connected by a dashed (not solid) line to visually encode "not yet real" without needing a text badge.

---

## 8. UX Reasoning (why this structure, for this audience)

- **Leads with outcome, not mechanism** (hero headline is "Stop Searching. Start Hiring Intelligently," not "AI-powered candidate search platform") — CXOs and investors buy outcomes; the mechanism (Knowledge Engine, Search Planner) is earned in §3 and §6 only after the outcome has landed.
- **The Problem section (§2) is placed before any feature explanation** because executives (unlike individual recruiters) need the cost of the status quo stated explicitly before they'll value a solution — this is a standard enterprise-sales narrative arc (problem → mechanism → proof → features → architecture credibility → vision), not a generic template; the order is deliberate.
- **Live Demo is positioned dead center (§4 of 8)**, not at the end — by the time a visitor reaches it they've absorbed the problem and the mechanism, so the demo confirms rather than introduces. Placing it last (a common SaaS-site mistake) risks losing skimmers before they ever interact with the one thing that actually proves the product works.
- **Enterprise Architecture (§6) exists specifically for the CTO/technical-diligence persona** inside a CXO buying committee — even if most visitors skim it, its presence and quality (an accurate, real diagram, not a marketing cartoon) signals engineering rigor to the one stakeholder in the room who will ask hard questions.
- **Vision/Roadmap (§7) is deliberately understated** (dashed lines, reduced opacity, no bold "COMING SOON" badges) because overselling a roadmap to an enterprise/investor audience reads as immature; the honest MVP-vs-future distinction (which matches your actual instruction to never overstate what's built) is itself a credibility signal.
- **No CTA in the footer** — the ask ("Live Demo") already happened twice (hero + demo section); repeating it a third time at the exit point reads as sales pressure rather than confidence, which cuts against "enterprise-grade" positioning.

---

## Open decisions requiring your approval before implementation

1. **Live Demo data source**: reuse the real backend (`/api/search`) live, requiring the FastAPI backend to be reachable from the marketing site, vs. a recorded/canned demo-mode response for reliability on a public marketing page. Recommend: real backend behind a lightweight rate limit, since a canned demo undermines the "real product" trust signal this whole plan is built around — but this is an infra decision, flagging rather than deciding unilaterally.
2. **Typeface licensing** (Inter/free vs. a paid premium face like Söhne) — affects budget, not design system.
3. **Whether the marketing site lives in a new top-level directory (e.g., `alphasource/marketing/`) alongside the existing `frontend/` (product) and `backend/`, or is a separate repo** — a structural, not visual, decision, but affects how §4's code-reuse from `frontend/src` actually gets wired in.

No code has been written. Awaiting your go-ahead on the above before implementation begins.
