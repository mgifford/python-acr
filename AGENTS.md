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
  python run_acr.py --repo <repo_id> --ai-backend <ollama|gemini> --model <model_name>
  ```
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

## Future Improvements
- Add more robust error handling for AI model timeouts.
- Improve WCAG mapping logic in `extract.py`.
