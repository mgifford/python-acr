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
Analyze this accessibility issue thread and provide a structured summary.

ISSUE: {row['Issue Title']}
REPORTER: {issue_data.get('reporter_info', 'Unknown')}
FOLLOWERS: {issue_data.get('followers', 'Unknown')}
RECENT FILES/PATCHES: {', '.join(issue_data.get('recent_files', []))}

COMMENT THREAD:
{comments_text}

ORIGINAL DESCRIPTION: {row['Description']}

Provide 5 outputs in this EXACT format:

TLDR: A high-level executive summary (2-3 sentences) of the issue and its current status.

PROBLEM_STATEMENT: A clear definition of the accessibility barrier, referencing specific WCAG criteria if applicable.

SENTIMENT: A brief assessment of the community sentiment (e.g., "Collaborative", "Heated", "Stalled") and why.

TIMELINE: A chronological summary of the discussion. Use the format "#<number> <User> <action>" for key events.
Example:
#1 UserA reported the issue.
#3 UserB confirmed reproduction.
#5 UserC proposed a patch.

LINKS: Relevant resources, documentation, or related issues mentioned. Format as "- [Title](URL): Description".

Format your response exactly as:
TLDR: ...
PROBLEM_STATEMENT: ...
SENTIMENT: ...
TIMELINE: ...
LINKS: ...
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
