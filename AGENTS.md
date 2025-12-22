# AGENTS.md

## Project Overview
This project is an AI Accessibility Validator (`python-acr`) that assists in the creation of Accessibility Conformance Reports (ACR) / VPAT-style documentation.

**Important:**  
Outputs produced by this project are *draft analytical artifacts*. They are **not final ACRs** and **must be reviewed, validated, and signed off by qualified human accessibility experts** before being used for procurement, compliance claims, or publication.

The system:
- Extracts issues from issue trackers (Drupal.org, GitHub)
- Uses AI models (Ollama, Gemini) to summarize and cluster those issues
- Produces structured artifacts intended to *support* human-led ACR authoring

This project does **not** make authoritative accessibility conformance claims.

---

## Explicit limitations and human review requirement

- AI-generated summaries may be incomplete, incorrect, or out of date.
- Mapping issues to WCAG criteria is heuristic and probabilistic.
- No automated output may be treated as a compliance determination.

**Human review is mandatory.**
Humans are responsible for:
- Validating issue relevance
- Confirming WCAG mappings
- Determining applicability, severity, and conformance status
- Producing the final ACR / VPAT document

The tool exists to reduce analysis time, not to replace expert judgment.

---

## GitHub Pages constraints (required)

All pages must work when hosted under the repository subpath:
- `https://<user>.github.io/<repo>/`

Rules:
- Use relative URLs that respect the repo base path.
  - Prefer `./assets/...` or `assets/...` from the current page.
  - Avoid absolute root paths like `/assets/...` unless you explicitly set and use a base path.
- Navigation links must work from every page (no assumptions about being at site root).
- Do not rely on server-side routing. Every page must be reachable as a real file.
- Avoid build steps unless documented and reproducible. Prefer “works from static files”.
- If using Jekyll:
  - Treat Jekyll processing as optional unless `_config.yml` and layouts are part of the repo.
  - If you use `{{ site.baseurl }}`, use it consistently for links and assets.
- Provide a failure-safe: pages should render a readable error if required data files are missing.

Static asset rules:
- Pin external CDN dependencies (exact versions) and document why each exists.
- Prefer vendoring critical JS/CSS locally to reduce breakage.
- Don’t depend on blocked resources (mixed content, HTTP, or fragile third-party endpoints).

Caching/versioning:
- If you fetch JSON/data files, include a lightweight cache-busting strategy (e.g., query param using a version string) OR document that users must hard refresh after updates.

## Local preview (required before publish)

Test pages via a local HTTP server (not `file://`) to match GitHub Pages behavior.

Examples:
- `python3 -m http.server 8000`
- `npx serve`

Verify:
- links resolve under a subpath
- fetch requests succeed
- no console errors on load

## Future Improvements
- Add more robust error handling for AI model timeouts.
- Improve WCAG mapping logic in `extract.py`.

---

## Architecture: pipeline vs presentation

This repository has two distinct halves:

1. **Python AI pipeline**
   - Fetches data
   - Performs AI-assisted analysis
   - Generates structured artifacts (CSV/JSON/YAML)

2. **Static results UI (HTML/JS/CSS)**
   - Displays and compares generated artifacts
   - Explains assumptions and uncertainty
   - Supports expert review workflows

Non-negotiables:
- The Python pipeline is the source of truth.
- The UI must not invent data, infer certainty, or hide uncertainty.
- The UI may only render fields present in the generated artifacts.
- Unknown or low-confidence values must be explicit (`null`, `unknown`).
- All `.html` entry points must load correctly when hosted via GitHub Pages (no backend dependencies, absolute URLs, or build steps that Pages cannot run).

---

## Accessibility posture (important)

### This project is NOT fully accessible

Even with axe linters and automated checks enabled:
- The UI will **not** be fully WCAG 2.2 AA conformant.
- Automated testing cannot guarantee accessibility.
- Some visualizations and comparison views may remain partially inaccessible.

This is intentional and documented.

### Why
- The UI is a *specialist expert tool*, not an end-user application.
- It prioritizes dense comparative analysis over broad usability.
- Accessibility work here focuses on **good-faith effort, transparency, and improvement**, not certification.

---

## Accessibility intent and documentation

Despite the above limitations, the project commits to:

- Designing and coding *toward* WCAG 2.2 AA where feasible
- Documenting accessibility decisions and known gaps
- Making improvements incremental and explicit

Agents and contributors must:
- Prefer semantic HTML and native controls
- Maintain keyboard operability where practical
- Preserve visible focus indicators
- Label form controls programmatically
- Avoid introducing new barriers casually

When accessibility is not achievable:
- The limitation must be documented
- The reason must be explained
- The trade-off must be intentional

---

## AI usage constraints

AI output is assistive, not authoritative.

Rules:
- AI must not invent WCAG failures or conformance claims.
- AI summaries must remain traceable to source issues.
- When evidence is insufficient, the correct output is:
  `unknown` or `insufficient data`.

Prompt-driven transformations must:
- Have defined input/output structure
- Retain references to source issues (URLs or IDs)
- Avoid definitive language without evidence

Prompt templates and versions must be retained.

---

## Freshness and verification rules

If generated content references:
- WCAG versions or interpretations
- Legal or policy claims
- Conformance status
- "Current" project state

Then:
- Cite an authoritative source, OR
- Explicitly label the content as AI-derived and unverified

Verified claims must include:
- `Last verified: YYYY-MM-DD`

---

## Coding and data handling conventions

- Implement retries and backoff for network calls
- Surface AI timeouts or failures explicitly
- Save intermediate artifacts (checkpointing)
- Do not silently overwrite previous runs
- Do not commit generated results

## UI typography requirements

- Headings (semantic h1–h6 elements plus navigation labels and section chips) must use a reliable sans-serif stack: prefer Helvetica/Arial with `sans-serif` fallback.
- Body copy, paragraphs, table cells, and control text default to a serif stack (`"Times New Roman", Times, serif`) to keep dense analyses readable.
- Avoid adding external webfont downloads; rely on system fonts so GitHub Pages builds remain deterministic and offline-friendly.

---

## Definition of done

A change is complete only when:
- The pipeline runs without uncaught errors
- Generated artifacts are structured and traceable
- The UI renders artifacts without fabrication
- Known accessibility gaps are documented
- Assumptions and limitations are explicit

This project values transparency over false certainty.
