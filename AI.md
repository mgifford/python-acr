# AI Prompts Documentation

This file outlines the various prompts used by the application to interact with the AI models (Ollama/Gemini). These prompts are currently embedded in the source code.

## 1. Issue Summarization (`src/summarize.py`)

**Purpose:** Analyzes a single issue (Title + Description) to determine the WCAG criteria and generate compliance notes.

**Prompt Template:**
```text
Analyze this accessibility issue:
Title: {row['Issue Title']}
Description: {row['Description']}

Provide 4 specific outputs:
1. ACR_NOTE: A professional note for a compliance report describing the barrier.
2. DEVELOPER_NOTE: Technical guidance for fixing this, noting if patches exist.
3. TITLE_ASSESSMENT: Does the title accurately reflect the issue? (OK/SUGGEST)
4. WCAG_ASSESSMENT: The specific WCAG Success Criterion number ONLY (e.g. '1.1.1'). Do not include the name, level, or reasoning in this line.

Format response strictly as:
ACR_NOTE: ...
DEVELOPER_NOTE: ...
TITLE_ASSESSMENT: ...
WCAG_ASSESSMENT: ...
```

---

## 2. Thread Analysis (`src/analyze_thread.py`)

**Purpose:** Analyzes the full comment thread of an issue to extract the discussion journey, TODOs, and resources.

**Prompt Template:**
```text
Analyze this accessibility issue thread and provide:

ISSUE: {row['Issue Title']}
REPORTER: {issue_data.get('reporter_info', 'Unknown')}
FOLLOWERS: {issue_data.get('followers', 'Unknown')}
RECENT FILES/PATCHES: {', '.join(issue_data.get('recent_files', []))}

COMMENT THREAD:
{comments_text}

ORIGINAL DESCRIPTION: {row['Description']}

Provide 4 outputs in this EXACT format:

JOURNEY: A chronological summary of the discussion (who said what, key decisions, concerns raised). Keep it concise like: "#1 UserA reported the issue, #2 UserB confirmed it, #3 UserC suggested a fix..."

TODO: List of specific outstanding tasks needed to resolve this issue (e.g., "Needs screen reader testing", "Awaiting upstream fix")

PASTE_SUMMARY: A 2-3 sentence summary that could be pasted into the issue to update status (e.g., "Current status: Patch available but needs testing. Waiting on upstream resolution.")

RESOURCES: 3-5 relevant W3C or accessibility expert resources related to the specific accessibility barrier discussed (WCAG success criteria, ARIA authoring practices, WebAIM articles, Deque blogs, etc.). Format as: "- [Title](URL): Brief description"

Format your response exactly as:
JOURNEY: ...
TODO: ...
PASTE_SUMMARY: ...
RESOURCES: ...
```

---

## 3. WCAG Consolidation (`src/consolidate.py`)

**Purpose:** Aggregates multiple issues for a single WCAG Success Criterion to determine the overall conformance level for the report.

**Prompt Template:**
```text
You are writing an OpenACR report for WCAG SC {sc}.
Here are the known open issues:
{issues_text}

1. Determine Conformance Level: 'supports', 'partially-supports', 'does-not-support', 'not-applicable'.
2. Write a consolidated 'Remarks' paragraph summarizing the barriers.

Format:
LEVEL: <level>
REMARKS: <text>
```

---

## 4. Evaluation / Test Prompt (`collect_responses.py`)

**Purpose:** Used for testing or evaluating model performance on specific datasets.

**Prompt Template:**
```text
Analyze this Drupal accessibility issue:
Title: {row['Issue Title']}
Description: {row.get('Description', row['Issue Title'])} 

Provide 4 specific outputs:
1. ACR_NOTE: A professional note for a compliance report describing the barrier.
2. DEVELOPER_NOTE: Technical guidance for fixing this, noting if patches exist.
3. TITLE_ASSESSMENT: Does the title accurately reflect the issue? (OK/SUGGEST)
4. WCAG_ASSESSMENT: Confirm the WCAG SC (e.g. 1.1.1) or suggest a better one.

Format response strictly as:
ACR_NOTE: ...
DEVELOPER_NOTE: ...
TITLE_ASSESSMENT: ...
WCAG_ASSESSMENT: ...
```
