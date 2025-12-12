import pandas as pd
import time
import ollama

# Ollama model wrapper
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
            elif line.startswith("WCAG:"): wcag = line.replace("WCAG:", "").strip() # Fallback
            
            if line.startswith("ACR_NOTE:"): acr_note = line.replace("ACR_NOTE:", "").strip()
            if line.startswith("DEVELOPER_NOTE:"): dev_note = line.replace("DEVELOPER_NOTE:", "").strip()
            elif line.startswith("DEV_NOTE:"): dev_note = line.replace("DEV_NOTE:", "").strip() # Fallback
            
        return wcag, acr_note, dev_note
    except Exception as e:
        print(f"Error analyzing issue: {e}")
        return "Error", "Error", "Error"

def main():
    try:
        df = pd.read_csv('test_queries.csv')
        print(f"Loaded {len(df)} queries.")
        
        # Using gemma3:4b as it was found in 'ollama list'
        model = OllamaModel(model_name="gemma3:4b")
        print(f"Using Ollama model: {model.model_name}")
        
        # Add missing columns if needed
        if 'Description' not in df.columns:
            df['Description'] = df['Issue Title']
            
        for idx, row in df.iterrows():
            print(f"Processing issue {idx + 1}/{len(df)}: {row['Issue Title'][:50]}...")
            wcag, acr, dev = analyze_issue(row, model)
            df.at[idx, 'ai_wcag'] = wcag
            df.at[idx, 'acr_note'] = acr
            df.at[idx, 'dev_note'] = dev
            
        df.to_csv('responses.csv', index=False)
        print("Saved responses to responses.csv")
        
    except Exception as e:
        print(f"Failed to run: {e}")

if __name__ == "__main__":
    main()
