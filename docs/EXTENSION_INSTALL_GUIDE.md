# AlphaSource Browser Extension — Installation Guide (Proof of Concept)

This is an unpacked, unpublished Chrome/Edge (Manifest V3) extension for the
Sprint 12 proof of concept. It has not been submitted to the Chrome Web
Store — install it in "developer mode" as described below.

## 1. Point it at your backend

Before loading the extension, know the URL of your running AlphaSource
backend (e.g. `http://localhost:8000` for a local dev server, or your
Railway deployment URL once that's live). You'll enter this in step 4.

## 2. Load the unpacked extension

1. Open `chrome://extensions` (or `edge://extensions` on Edge).
2. Enable **Developer mode** (top-right toggle).
3. Click **Load unpacked**.
4. Select the `extension/` folder from the AlphaSource repository.
5. AlphaSource should now appear in your extensions list and in the
   toolbar's extension menu (pin it for one-click access).

## 3. Configure settings

1. Right-click the AlphaSource icon → **Options** (or click the extension
   icon, then **Settings** at the bottom of the popup).
2. Enter your **Backend URL** (from step 1).
3. Enter a **recruiter identity** — any self-reported string (e.g. your
   email). This is attached to candidates you capture for traceability; it
   is not a login and no password is ever requested or stored.
4. Click **Save settings**.

## 4. Capture a candidate

1. Navigate to a candidate profile, portfolio, or resume page you are
   already legitimately viewing in your own, already-authenticated browser
   session.
2. Click the AlphaSource extension icon.
3. The popup scans the current page only, once, right now — it does not
   run in the background and does not scan any other tab or page.
4. If a candidate is detected, review the extracted name/headline/company
   and click **Add to AlphaSource**.
5. On success, the popup shows the candidate's AlphaSource ID and whether
   it was created new or merged into an existing record.

## What this extension does NOT do

- It does not run automatically on every page you visit — extraction only
  happens while the popup is open, which only happens when you click the
  icon.
- It does not log in to any site, store any site's password or session
  cookie, or bypass any site's authentication. It only ever reads the page
  you are already viewing in your own session.
- It never sends anything to AlphaSource without you clicking
  **Add to AlphaSource** — there is no silent or automatic upload.
- It is not a scraper or crawler: it has no ability to navigate to other
  pages, follow links, or run against a list of URLs. One page, one click,
  one candidate.

## Known limitations (Proof of Concept)

- **Detection accuracy is heuristic.** The generic schema.org/JSON-LD
  adapter is reliable when a page provides that markup; the DOM-heuristic
  fallback is a best-effort pattern match and will occasionally miss a
  real profile page or, more rarely, mis-fire on a page that isn't one.
  Always review the detected fields before clicking **Add to AlphaSource**.
- **No site-specific adapters ship in this POC.** The adapter registry
  (`extension/content-scripts/adapters/`) is built so a specific site's
  adapter can be added later without touching the extractor, popup, or
  backend — none is included yet, so extraction quality on any single
  platform is only as good as that platform's generic markup.
- **`captured_by` is self-reported, not authenticated.** This POC has no
  login step for the extension itself; the identity string is trusted at
  face value.
- **Icons are placeholder art**, generated for this POC rather than final
  brand assets.
- **No update mechanism.** As an unpacked, unpublished extension, updates
  mean re-pulling the repo and clicking "Reload" on `chrome://extensions`.
