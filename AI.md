# AI Prompts Documentation

This file outlines the various prompts used by the application to interact with the AI models (Ollama/Gemini). These prompts are currently embedded in the source code.

## Validation Lessons (December 2025)

After validating 15 CKEditor5 issues, several consistent hallucination patterns emerged:

### Critical Problems Found:
1. **Invented people & events**: AI created fake usernames (e.g., "Alice", "UserB"), non-existent PRs (#1234), and fictitious maintainer responses
2. **Timeline formatting**: Using "#1GitHub" instead of "# 1 GitHub" - missing spaces
3. **Redundant links**: Including the original issue URL in "Key Links" when it's already in the report
4. **False collaboration**: Labeling single-user bug reports as "Collaborative"
5. **Generic speculation**: When threads had minimal comments, AI invented what "probably" happened instead of being honest about lack of data

### Solutions Implemented:
- **Explicit anti-hallucination instructions** in prompts: "DO NOT INVENT usernames, PRs, or events"
- **Be honest about limited data**: "If only 1-2 comments, say 'minimal discussion' - don't speculate"
- **No redundant URLs**: "Do NOT include original issue URL in LINKS section"
- **Accurate sentiment categories**: "Collaborative requires 2+ people engaging. Single report = 'Initial report only'"
- **Use actual comment numbers**: "Reference #number from COMMENT THREAD, not invented numbers"

### Validation Scoring System:
- **1 = Major Hallucination**: Invented people, PRs, timelines (e.g., "Alice proposed patch #1234")
- **2 = Major Hallucination**: Multiple fabricated events or substantial timeline errors
- **3 = Minor Hallucination**: Small inaccuracies in timeline or attribution
- **4 = Missed Context**: Technically correct but incomplete; missing key discussion points
- **5 = Bad Formatting**: Content accurate but formatting issues (spacing, redundant links)

---

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

**Updated Prompt (Post-Validation):**
```text
Analyze this accessibility issue thread and provide a structured summary.

ISSUE: {row['Issue Title']}
REPORTER: {issue_data.get('reporter_info', 'Unknown')}
COMMENT THREAD:
{comments_text}

CRITICAL INSTRUCTIONS:
1. DO NOT INVENT OR HALLUCINATE: Only use actual usernames, comment numbers, and events from the thread above.
2. BE EXPLICIT ABOUT LIMITED DATA: If there are only 1-2 comments, say "minimal discussion" - don't speculate.
3. NO REDUNDANT LINKS: Do NOT include the original issue URL (it's captured elsewhere).
4. SENTIMENT ACCURACY: "Collaborative" requires 2+ people engaging. Single report = "Initial report only".
5. USE ACTUAL COMMENT NUMBERS: Reference the #number from COMMENT THREAD, not invented numbers.

TLDR: Executive summary (2-3 sentences). Be honest if status is unknown.
PROBLEM_STATEMENT: Accessibility barrier definition with WCAG criteria.
SENTIMENT: One of: "Active collaboration", "Minimal engagement", "Stalled", "Initial report only"
TIMELINE: Format as "# N username: action" using ONLY actual data from COMMENT THREAD above.
LINKS: External WCAG/MDN docs mentioned in comments. NO original issue URL.
```

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
