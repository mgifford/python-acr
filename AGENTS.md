# AGENTS.md

## Project Overview
This project is an AI Accessibility Validator (`python-acr`) that automates the creation of Accessibility Conformance Reports (ACR) / VPATs. It extracts issues from issue trackers (Drupal.org, GitHub), summarizes them using AI models (Ollama, Gemini), and generates reports.

## Environment Setup
- **Python Version**: Python 3.x
- **Virtual Environment**: Always use a virtual environment (`venv`).
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- **Dependencies**: Install via `requirements.txt`.
  ```bash
  pip install -r requirements.txt
  ```
- **Ollama Setup** (for local AI):
  - Install Ollama application from https://ollama.ai
  - The `ollama` Python package (in requirements.txt) is the client library
  - Check installed models: `ollama list`
  - Example models: `gpt-oss:20b`, `gemma3:4b`, `llama3`

## Running the Application
- **Main Entry Point**: `run_acr.py`
- **Command Structure**:
  ```bash
  python run_acr.py --repo <repo_id> --ai-backend <ollama|gemini> --model <model_name> --tags <tag1,tag2>
  ```
- **Custom Tags**:
  - Use `--tags` to override default accessibility tags (e.g., `--tags "performance,sustainability"`).
  - Works for both Drupal (issue tags) and GitHub (issue labels).
- **Long-running Processes (macOS)**: Use `caffeinate` to prevent sleep during long scans.
  ```bash
  caffeinate -i ./venv/bin/python3 run_acr.py ...
  ```

## Key Components
- **`run_acr.py`**: Orchestrates the workflow (extract -> summarize -> consolidate -> report).
- **`src/extract.py`**: Handles fetching issues from Drupal.org and GitHub API.
  - **Drupal**: Scrapes issue search results based on WCAG tags.
  - **GitHub**: Uses GitHub API to fetch issues and discover accessibility labels.
- **`src/summarize.py`**: Uses AI to analyze issues and map them to WCAG criteria.
  - Supports **Ollama** (local) and **Gemini** (cloud).
  - Implements checkpointing to resume interrupted runs.
- **`results/`**: Stores output files. **Do not commit this directory.**

## Coding Conventions
- **Error Handling**:
  - Implement retries for network requests, especially for `429 Too Many Requests`.
  - Use `time.sleep()` for rate limiting.
- **Data Persistence**:
  - Save intermediate results (CSVs) frequently (checkpointing) to avoid data loss during long runs.
- **Git**:
  - `results/` and `data/` are ignored via `.gitignore`.
  - Ensure new logic supports both Drupal and GitHub workflows.

## Testing & Validation
- **GitHub Extraction**: Verify with a known repo (e.g., `ckeditor/ckeditor5`, `joomla/joomla-cms`).
- **Ollama Models**: Check available models with `ollama list`. Tested with `gpt-oss:20b` (13 GB, 20B parameters).
- **Drupal Extraction**: Verify with `drupal` project ID.
- **AI Backend**: Ensure `ollama list` shows the requested model before running.


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
