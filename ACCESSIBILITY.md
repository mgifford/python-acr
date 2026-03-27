# Accessibility Commitment (ACCESSIBILITY.md)

## 1. Our commitment

We believe accessibility is a subset of quality. This project commits to **WCAG 2.2 AA** as its design target for all user-facing documentation and UI tooling. We track known gaps publicly to remain accountable.

> **Important:** This project is a specialist expert tool. It is used by accessibility professionals to generate draft Accessibility Conformance Reports (ACRs). The UI will not be fully WCAG 2.2 AA conformant. Automated testing cannot guarantee accessibility. Known limitations are documented below.

## 2. Real-time health metrics

| Metric | Status / Value |
| :--- | :--- |
| **Open A11y Issues** | [View open accessibility issues](https://github.com/mgifford/python-acr/labels/accessibility) |
| **Automated Test Pass Rate** | Monitored via link checking and code review |
| **Browser Support** | Last 2 major versions of Chrome, Firefox, Safari |
| **Design target** | WCAG 2.2 Level AA (good-faith effort — see limitations) |

## 3. Contributor requirements (the guardrails)

To contribute to this repo, you must follow these guidelines:

- **Semantic HTML:** Prefer native HTML elements and ARIA roles over custom widgets
- **Keyboard operability:** All interactive controls must be reachable and operable by keyboard
- **Visible focus indicators:** Never remove focus rings; ensure 3:1 contrast against adjacent colors
- **Form labels:** All form controls must have programmatically associated labels
- **Color independence:** Do not use color alone to convey meaning
- **Dark mode:** Support both light and dark color themes using `prefers-color-scheme` and a manual toggle
  - Follow [Light/Dark Mode Accessibility Best Practices](https://github.com/mgifford/ACCESSIBILITY.md/blob/main/examples/LIGHT_DARK_MODE_ACCESSIBILITY_BEST_PRACTICES.md)
- **Motion:** Respect `prefers-reduced-motion` when adding transitions or animations
- **Inclusive language:** Use person-centered, respectful language throughout

## 4. Reporting and severity taxonomy

Please use our [issue tracker](https://github.com/mgifford/python-acr/issues/new) when reporting issues. We prioritize based on:

- **Critical:** Blocks a user from completing a core task (e.g., navigating issues, saving results)
- **High:** Significant barrier or misleading information that impacts broad user groups
- **Medium:** Clarity issues, incomplete ARIA labels, or inconsistent behavior
- **Low:** Minor improvements, cosmetic fixes, or enhancements

## 5. Automated check coverage

Where feasible, we aim to include:

- Contrast checks against WCAG 2.2 AA thresholds (normal text 4.5:1, large text 3:1)
- Validation of focus indicator visibility in both light and dark modes
- `prefers-color-scheme` media query implementation
- `forced-colors` mode fallbacks for critical UI boundaries
- `prefers-reduced-motion` respect in CSS transitions
- `aria-label` and `role` correctness on custom interactive elements

## 6. Browser and assistive technology testing

### Browser support

This project targets the **last 2 major versions** of:

- **Chrome / Chromium** (including Edge, Brave)
- **Firefox**
- **Safari / WebKit** (macOS and iOS)

### Assistive technology

Contributors are encouraged to test with:

- **Screen readers:** JAWS, NVDA, VoiceOver, TalkBack
- **Keyboard navigation:** Tab, arrow keys, Enter, Escape
- **Magnification:** Browser zoom to 200%, screen magnifiers
- **Voice control:** Dragon, Voice Control (macOS / iOS)

## 7. Known limitations

This project is a specialist expert tool, not a consumer application. The following gaps are intentional or currently unresolved:

| Area | Gap | Status |
| :--- | :--- | :--- |
| Data visualizations | Comparison panels may be difficult to navigate with screen readers | Documented, not yet resolved |
| Dense tables | Some comparison tables have limited row/column header associations | Documented |
| Color-only status cues | Some inline status indicators rely partly on color | In progress |
| Touch targets | Some UI controls may not meet 44×44 px minimum in dense layouts | Documented |

Improvements are incremental. Each change is intentional and explained.

## 8. Dark mode implementation

Both `index.html` and `comparator.html` implement accessible light/dark mode following the pattern described in [LIGHT_DARK_MODE_ACCESSIBILITY_BEST_PRACTICES.md](https://github.com/mgifford/ACCESSIBILITY.md/blob/main/examples/LIGHT_DARK_MODE_ACCESSIBILITY_BEST_PRACTICES.md):

- System preference (`prefers-color-scheme`) is detected and applied automatically
- User override persists across sessions via `localStorage`
- Theme toggle button uses sun/moon SVG icons with accessible `aria-label`
- Toggle button appears **after** navigation items in DOM order for correct tab flow
- All theme colors are defined as CSS custom properties and tested for WCAG AA contrast in both modes
- CSS transitions respect `prefers-reduced-motion`
- Forced-colors mode (Windows High Contrast) is supported via `@media (forced-colors: active)` fallbacks

## 9. AI output and accessibility claims

This tool uses AI models (Google Gemini, Ollama) to assist in drafting Accessibility Conformance Reports. AI-generated content:

- **Is not authoritative.** AI summaries may be incomplete, incorrect, or out of date.
- **Must be reviewed** by qualified accessibility professionals before use in procurement or compliance contexts.
- **Does not constitute a conformance determination.** Outputs are draft analytical artifacts.

Human review is mandatory. See [AGENTS.md](./AGENTS.md) for details on AI usage constraints.

## 10. Getting help

- **Questions:** Open a [discussion](https://github.com/mgifford/python-acr/discussions)
- **Bugs or gaps:** Open an [issue](https://github.com/mgifford/python-acr/issues)
- **Contributions:** See [README.md](./README.md)
- **Accommodations:** Request via the `accessibility-accommodation` label on issues

## 11. Continuous improvement

We regularly review and update:

- WCAG conformance targets as standards evolve
- Dark/light mode contrast ratios
- Keyboard navigation paths
- Screen reader compatibility
- Inclusive language and terminology

Last updated: 2026-03-27
