import pandas as pd
import os
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
        # Clean up verbose error messages (especially from Gemini)
        error_msg = str(e).split('\n')[0]
        if len(error_msg) > 200: error_msg = error_msg[:200] + "..."
        print(f"Error analyzing issue: {error_msg}")
        return "Error", "Error", "Error"

def run(results_dir, ai_config):
    files = sorted(results_dir.glob("issues_raw_*.csv"))
    if not files:
        print("No raw issues found to summarize.")
        return
    
    infile = files[-1]
    print(f"Reading from {infile}")
    df = pd.read_csv(infile)
    
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
