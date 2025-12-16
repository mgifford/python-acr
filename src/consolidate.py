import pandas as pd
import os
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

def consolidate_sc(sc, group, model):
    issues_text = "\n".join([f"- {r['acr_note']} (Status: {r['Status']})" for _, r in group.iterrows()])
    prompt = f"""
You are preparing formal OpenACR / VPAT documentation for a vendor accessibility
attestation that may be submitted as part of a government procurement process. You are the accessibility expert for the product. 

This content must be factual, conservative, and suitable for legal and compliance review.

WCAG SUCCESS CRITERION: {sc}

RELATED OPEN ACCESSIBILITY ISSUES:
{issues_text}

INSTRUCTIONS:

1. CONFORMANCE LEVEL SELECTION  
Determine the appropriate conformance level for this Success Criterion using
ONLY the evidence from the listed open issues. 

Allowed values:
- supports
- partially-supports
- does-not-support
- not-applicable

Guidance:
- If one or more open issues indicate user-facing barriers, do NOT select "supports".
- Use "partially-supports" when barriers exist but are limited in scope or impact.
- Use "does-not-support" when barriers are significant or affect core functionality.
- Use "not-applicable" ONLY if the Success Criterion clearly does not apply.

When in doubt, choose the more conservative level.

2. REMARKS CONTENT REQUIREMENTS  
Write a single consolidated REMARKS paragraph that:
- Describes the accessibility barriers in neutral, professional language
- Focuses on user impact and affected functionality
- Does NOT include remediation plans, timelines, or promises
- Does NOT include implementation guidance
- Does NOT speculate beyond the documented issues
- Is suitable for inclusion in a VPAT or OpenACR submission

Length constraint:
- REMARKS must be under 500 characters.

3. ISSUE TRACEABILITY  
List the relevant issue identifiers that support this assessment.
Do NOT invent or infer issue numbers.

OUTPUT FORMAT (EXACT):

LEVEL: <supports | partially-supports | does-not-support | not-applicable>
REMARKS: <single paragraph under 500 characters>
ISSUES: <ID1>, <ID2>, <ID3>
    """
    try:
        resp = model.generate_content(prompt)
        text = resp.text
        
        level = "partially-supports" # Default fallback
        remarks = ""
        
        for line in text.strip().split('\n'):
            if line.startswith("LEVEL:"): level = line.replace("LEVEL:", "").strip().lower()
            if line.startswith("REMARKS:"): remarks = line.replace("REMARKS:", "").strip()
            
        # If remarks is empty, maybe the model didn't use the prefix, take the whole text
        if not remarks and not text.startswith("LEVEL:"):
            remarks = text
            
        return level, remarks
    except Exception as e:
        print(f"Error consolidating SC {sc}: {e}")
        return "not-evaluated", "Error during consolidation"

def run(results_dir, ai_config):
    files = sorted(results_dir.glob("issues_summarized_*.csv"))
    if not files:
        print("No summarized issues found to consolidate.")
        return
    
    infile = files[-1]
    print(f"Reading from {infile}")
    df = pd.read_csv(infile)
    
    backend = ai_config.get('backend', 'gemini')
    model_name = ai_config.get('model_name')
    
    if backend == 'ollama':
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
    
    consolidated = []
    
    # Pre-process: Try to extract WCAG SC from "General" issues based on content
    def extract_wcag_from_content(row):
        """Look for WCAG SC patterns in issue content."""
        import re
        # Check all text fields for WCAG patterns
        text_fields = [
            str(row.get('Issue Description', '')),
            str(row.get('acr_note', '')),
            str(row.get('dev_note', '')),
            str(row.get('thread_journey', '')),
            str(row.get('paste_summary', ''))
        ]
        full_text = ' '.join(text_fields)
        
        # Look for patterns like "WCAG 4.1.2", "4.1.2", "SC 4.1.2"
        patterns = [
            r'WCAG\s*(\d+\.\d+\.\d+)',
            r'SC\s*(\d+\.\d+\.\d+)',
            r'\b(\d+\.\d+\.\d+)\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, full_text)
            if match:
                return match.group(1)
        return None
    
    # Reassign "General" issues that have WCAG mentions
    general_mask = ~df['ai_wcag'].str.match(r'\d+\.\d+\.\d+', na=False)
    reassigned_count = 0
    
    for idx in df[general_mask].index:
        extracted_sc = extract_wcag_from_content(df.loc[idx])
        if extracted_sc:
            df.at[idx, 'ai_wcag'] = extracted_sc
            reassigned_count += 1
    
    if reassigned_count > 0:
        print(f"📝 Reassigned {reassigned_count} 'General' issues to specific WCAG SC based on content mentions")
    
    # Handle valid SCs (including newly reassigned ones)
    valid_sc_df = df[df['ai_wcag'].str.match(r'\d+\.\d+\.\d+', na=False)]
    print(f"Found {len(valid_sc_df)} issues with valid WCAG SCs.")
    
    for sc, group in valid_sc_df.groupby('ai_wcag'):
        print(f"Consolidating SC {sc} ({len(group)} issues)...")
        level, remarks = consolidate_sc(sc, group, model)
        consolidated.append({
            "WCAG SC": sc,
            "ACR Assessment": level,
            "ACR Summary": remarks,
            "Issue Count": len(group)
        })

    # Handle unmapped/general issues
    unmapped_df = df[~df['ai_wcag'].str.match(r'\d+\.\d+\.\d+', na=False)]
    if not unmapped_df.empty:
        print(f"Found {len(unmapped_df)} unmapped/general accessibility issues.")
        # We group them all under a special "General" category
        level, remarks = consolidate_sc("General Accessibility (Unmapped)", unmapped_df, model)
        consolidated.append({
            "WCAG SC": "General",
            "ACR Assessment": level,
            "ACR Summary": remarks,
            "Issue Count": len(unmapped_df)
        })
        
    out_df = pd.DataFrame(consolidated)
    outfile = results_dir / "wcag-acr-consolidated.csv"
    out_df.to_csv(outfile, index=False)
    print(f"Saved consolidated report to {outfile}")
