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

**Purpose:** Analyzes the full comment thread of an issue to extract the discussion journey, engagement, and actionable next steps.

**Latest Prompt (Dec 2025):**
```text
You are an experienced web accessibility professional reviewing an accessibility
issue thread to assess the validity of the reported barrier, the quality of discussion,
and the current state of resolution based solely on recorded evidence.

Analyze the following accessibility issue thread and provide a structured, factual summary.

ISSUE: {row['Issue Title']}
REPORTER: {issue_data.get('reporter_info', 'Unknown')}
FOLLOWERS: {issue_data.get('followers', 'Unknown')}
RECENT FILES/PATCHES: {', '.join(issue_data.get('recent_files', []))}
ENGAGEMENT METRICS:
- Unique users: {num_unique_users}
- Total comments: {num_comments}
- Patches/PRs: {num_patches}
- Screenshots: {num_screenshots}

COMMENT THREAD:
{comments_text}

ORIGINAL DESCRIPTION:
{row['Description']}

CRITICAL INSTRUCTIONS:
1. NO INVENTION OR INFERENCE  
Use ONLY information explicitly present in the issue title, description, and comment
thread above. Do not infer intent, outcomes, or internal decisions. Do not invent users,
events, fixes, or timelines.

2. EXPLICIT DATA LIMITS  
If discussion is limited, state that clearly using phrases such as:
- "Initial report only"
- "Minimal discussion"
- "No evidence of follow-up or resolution"

Do not speculate about what may have happened off-thread.

3. COMMENT AND USER ACCURACY  
Reference ONLY real usernames and comment numbers that appear in the thread.
Never fabricate placeholders or generic contributors.

4. SENTIMENT BASED ON PARTICIPATION  
Assess sentiment strictly by observable engagement:
- One participant only → "Initial report only"
- Two or more participants with limited interaction → "Minimal engagement"
- Multiple participants proposing, testing, or refining solutions → "Active collaboration"
- No recent activity over a significant period → "Stalled (no recent activity)"

5. TIMELINE DISCIPLINE  
Use actual comment numbers and usernames.
Each timeline entry MUST be on its own line.
Do not combine events or summarize multiple comments into one entry.

6. LINK HYGIENE  
Do NOT include the original issue URL.
Only include external references explicitly mentioned or clearly relevant
to understanding the accessibility barrier (WCAG, MDN, specs, related issues).

7. STANDARDS BASELINE  
- Use WCAG 2.2 Level AA as the accessibility baseline
- Reference WCAG 2.2 Success Criteria only when supported by the issue description
- Avoid speculative or weak mappings

8. ISSUE TRACKER SOURCE DETECTION AND FORMATTING

Determine the issue tracker platform based on the issue URL or domain present
in the data provided.

Supported platforms:
- GitHub (github.com)
- Drupal (drupal.org)

Once the platform is identified, ALL comment references, user references, and
links MUST follow the conventions of that platform.

Do NOT mix formats between platforms.

GITHUB FORMATTING RULES (github.com):
- Comment anchors use the format:
	https://github.com/{{owner}}/{{repo}}/issues/{{NUMBER}}#issuecomment-{{ID}}
- User accounts use the format:
	https://github.com/{{username}}
- Timeline entries must reference the GitHub username exactly as shown in
	the comment thread.
- When linking to a specific comment, use the GitHub issuecomment anchor,
	not a generic issue link.

DRUPAL FORMATTING RULES (drupal.org):
- Comment anchors use the format:
	https://www.drupal.org/project/{{project}}/issues/{{NUMBER}}#comment-{{ID}}
- User accounts use the format:
	https://www.drupal.org/u/{{username}}
- Timeline entries must reference the Drupal username exactly as shown in
	the issue thread.
- When linking to a specific comment, use the Drupal comment anchor,
	not the issue page alone.

PLATFORM CONSISTENCY REQUIREMENT:
- If the issue originates from github.com, ALL comment and user links must
	follow GitHub conventions.
- If the issue originates from drupal.org, ALL comment and user links must
	follow Drupal conventions.
- Never assume GitHub-style usernames or comment IDs for Drupal issues, or
	vice versa.

UNCERTAIN SOURCE HANDLING:
- If the issue source cannot be confidently determined from the provided data,
	do NOT generate comment or user links.
- In that case, reference usernames and comment numbers as plain text only,
	and explicitly note limited linkability in the TLDR.


Provide EXACTLY the following five outputs, in this order and format:

TLDR:
A concise executive summary (2–3 sentences) describing the accessibility issue and its current observable status. In addition, clearly state the next step or call to action for the community (e.g., needs review, needs testing, waiting for maintainer, stalled, etc.). If status is unclear, say so explicitly.

PROBLEM_STATEMENT:
A clear, neutral description of the accessibility barrier affecting users. If possible, highlight the latest attempt to resolve the issue (such as a patch, pull request, or workaround) and its status. Reference specific WCAG Success Criteria only if justified by the content of the issue and comments.

SENTIMENT:
One of the following values ONLY:
- Active collaboration
- Minimal engagement
- Stalled (no recent activity)
- Initial report only

TIMELINE:
A chronological list using ONLY actual comment numbers and usernames.
Each entry on its own line, for example:
#1 johndoe: Filed the initial accessibility report with reproduction steps.
#3 janedoe: Confirmed the issue and referenced WCAG 1.1.1.
#5 johndoe: Tested proposed fix and reported outcome.
If fewer than three comments exist, be explicit:
#1 reporter: Filed initial accessibility report. No further discussion recorded.

LINKS:
Relevant external references only. Do NOT include the original issue URL.
Format exactly as:
- [Title](URL): Brief description of relevance

Format your response EXACTLY as follows:
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
