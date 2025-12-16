import pandas as pd
import os
import sys
import time
import ollama

# Conditionally import genai only when needed
try:
    import google.generativeai as genai
except ImportError:
    genai = None

class OllamaModel:
    def __init__(self, model_name="gemma3:4b"):
        self.model_name = model_name

    def generate_content(self, prompt):
        try:
            response = ollama.chat(model=self.model_name, messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
            ])
            class Response:
                text = response['message']['content']
            return Response()
        except Exception as e:
            print(f"Ollama Error: {e}")
            raise e

def analyze_issue(row, model):
    prompt = f"""
You are an experienced web accessibility professional reviewing an issue queue.
Your role is to identify and clearly describe accessibility barriers, assess whether
the reported issue is valid and actionable, and provide practical guidance to move
the issue toward resolution.

Analyze the following accessibility issue:

Title: {row['Issue Title']}
Description: {row['Description']}

Your goal is to:
- Clarify the actual accessibility barrier, if one exists
- Nudge the issue forward with concrete, standards-based guidance
- Provide developers with clear, minimal, and current technical direction
- Avoid speculative or non-actionable advice

Provide exactly four outputs:

1. ACR_NOTE  
A concise, professional note suitable for an accessibility compliance report.
Describe the user impact and barrier in plain, neutral language. Do not speculate
beyond the information provided.

2. DEVELOPER_NOTE  
Actionable technical guidance focused on fixing the issue.  
Prioritize:
- Semantic HTML solutions first
- ARIA only when native semantics are insufficient
- Established patterns and documented techniques

Note known patches, common fixes, or references to authoritative guidance when relevant.
Avoid deprecated techniques and unnecessary complexity.

3. TITLE_ASSESSMENT  
Indicate whether the issue title accurately reflects the described barrier.
Respond with:
- OK
- SUGGEST (if misleading, vague, or incorrect)

4. WCAG_ASSESSMENT  
Provide the applicable WCAG 2.2 Success Criterion number ONLY (for example: 1.1.1).
Do not include the criterion name, level, or explanation.

Use the following constraints and references:

- WCAG 2.2 Level AA is the baseline standard
- Reference WCAG 2.2 Understanding documents for interpretation - https://www.w3.org/WAI/WCAG22/Understanding/
- Reference WAI-ARIA 1.2 for ARIA usage - https://www.w3.org/TR/wai-aria-1.2/
- Always prefer semantic HTML over ARIA
- Avoid suggesting deprecated or outdated technologies
- Emphasize user impact and accessible, user-friendly design

Implementation priority order:
1. Semantic HTML structure
2. Accessible markup and ARIA (only when necessary)
3. CSS architecture and layering
4. Responsive layouts using relative units
5. Progressive enhancement with JavaScript
6. Accessibility testing and validation

Format the response exactly as follows:

ACR_NOTE: ...
DEVELOPER_NOTE: ...
TITLE_ASSESSMENT: ...
WCAG_ASSESSMENT: ...
    """
    try:
        resp = model.generate_content(prompt)
        text = resp.text
        
        wcag = "Unknown"
        acr_note = ""
        dev_note = ""
        
        for line in text.strip().split('\n'):
            line = line.strip()
            if line.startswith("WCAG_ASSESSMENT:"): wcag = line.replace("WCAG_ASSESSMENT:", "").strip()
            elif line.startswith("WCAG:"): wcag = line.replace("WCAG:", "").strip()
            
            if line.startswith("ACR_NOTE:"): acr_note = line.replace("ACR_NOTE:", "").strip()
            if line.startswith("DEVELOPER_NOTE:"): dev_note = line.replace("DEVELOPER_NOTE:", "").strip()
            elif line.startswith("DEV_NOTE:"): dev_note = line.replace("DEV_NOTE:", "").strip()
            
        return wcag, acr_note, dev_note
    except Exception as e:
        error_str = str(e)
        # Check for critical quota/rate limit errors
        if "429" in error_str or "quota" in error_str.lower():
            print(f"\nCRITICAL ERROR: API Quota Exceeded or Rate Limit Hit.")
            print(f"Details: {error_str.splitlines()[0]}")
            print("Exiting gracefully to prevent further errors.")
            sys.exit(1)

        # Clean up verbose error messages (especially from Gemini)
        error_msg = error_str.split('\n')[0]
        if len(error_msg) > 200: error_msg = error_msg[:200] + "..."
        print(f"Error analyzing issue: {error_msg}")
        return "Error", "Error", "Error"

def run(results_dir, ai_config, limit=None):
    files = sorted(results_dir.glob("issues_raw_*.csv"))
    if not files:
        print("No raw issues found to summarize.")
        return
    
    infile = files[-1]
    print(f"Reading from {infile}")
    df = pd.read_csv(infile)
    
    # Apply limit if specified
    if limit:
        print(f"Limiting to first {limit} issues (out of {len(df)} total)")
        df = df.head(limit)
    
    # Ensure output columns exist
    for col in ['ai_wcag', 'acr_note', 'dev_note']:
        if col not in df.columns:
            df[col] = ""
    
    backend = ai_config.get('backend', 'gemini')
    model_name = ai_config.get('model_name')
    
    if backend == 'ollama':
        # Default to gemma3:4b if not specified
        target_model = model_name if model_name else "gemma3:4b"
        print(f"Using Ollama backend with model: {target_model}")
        model = OllamaModel(model_name=target_model)
    else:
        print("Using Gemini backend")
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        # Ensure model name has models/ prefix
        if model_name:
            target_model = model_name if model_name.startswith('models/') else f'models/{model_name}'
        else:
            target_model = 'models/gemini-2.0-flash'
        print(f"Using Gemini model: {target_model}")
        model = genai.GenerativeModel(target_model)
    
    # Determine output file and check for existing progress
    timestamp = pd.Timestamp.now().strftime('%Y%m%d')
    outfile = results_dir / f"issues_summarized_{timestamp}.csv"
    
    # Check if there is an existing summary file to resume from
    existing_summaries = sorted(results_dir.glob("issues_summarized_*.csv"))
    processed_ids = set()
    
    if existing_summaries:
        # Use the latest one
        outfile = existing_summaries[-1]
        print(f"Found existing summary file: {outfile}")
        try:
            existing_df = pd.read_csv(outfile)
            if 'Issue ID' in existing_df.columns:
                processed_ids = set(existing_df['Issue ID'].astype(str))
            print(f"Resuming... {len(processed_ids)} issues already processed.")
        except Exception as e:
            print(f"Error reading existing summary: {e}. Starting fresh.")
    
    print(f"Summarizing {len(df)} issues...")
    
    for idx, row in df.iterrows():
        if str(row['Issue ID']) in processed_ids:
            continue

        print(f"Processing {idx+1}/{len(df)}: {row['Issue Title'][:30]}...")
        wcag, acr, dev = analyze_issue(row, model)
        
        # Prefer AI wcag detection if raw was unknown
        final_wcag = wcag if row['wcag_sc'] == "Unknown" else row['wcag_sc']
        
        # Update the row data
        row['ai_wcag'] = final_wcag
        row['acr_note'] = acr
        row['dev_note'] = dev
        
        # Save incrementally
        # Create a DataFrame for this single row
        single_df = pd.DataFrame([row])
        
        # Append to CSV
        # If file doesn't exist, write header. If it does, skip header.
        header = not outfile.exists()
        single_df.to_csv(outfile, mode='a', header=header, index=False)
        
        if backend == 'gemini':
            time.sleep(1) # Rate limit for Gemini
            
    print(f"Saved summaries to {outfile}")
