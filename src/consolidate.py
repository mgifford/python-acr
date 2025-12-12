import pandas as pd
import google.generativeai as genai
import os
import ollama

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
    You are writing an OpenACR report for WCAG SC {sc}.
    Here are the known open issues:
    {issues_text}
    
    1. Determine Conformance Level: 'supports', 'partially-supports', 'does-not-support', 'not-applicable'.
    2. Write a consolidated 'Remarks' paragraph summarizing the barriers.
    
    Format:
    LEVEL: <level>
    REMARKS: <text>
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
        target_model = model_name if model_name else 'gemini-1.5-flash'
        model = genai.GenerativeModel(target_model)
    
    consolidated = []
    
    # Handle valid SCs
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
