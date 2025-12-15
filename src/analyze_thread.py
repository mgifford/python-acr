import pandas as pd
import os
import time
import requests
from bs4 import BeautifulSoup
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

def scrape_drupal_issue(url):
    """Fetch full Drupal issue page and extract metadata + comments."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract metadata
        metadata = {}
        
        # Reporter and date
        submitted = soup.find('span', class_='submitted')
        if submitted:
            metadata['reporter_info'] = submitted.get_text(strip=True)
        
        # Followers
        followers_section = soup.find('div', class_='project-issue-followers')
        if followers_section:
            metadata['followers'] = followers_section.get_text(strip=True)
        
        # Patches and MRs
        files = []
        file_section = soup.find_all('div', class_='file')
        for f in file_section[:5]:  # Limit to 5 most recent
            file_info = f.get_text(strip=True)
            files.append(file_info)
        metadata['recent_files'] = files
        
        # Comments - extract comment number, author, and text
        comments = []
        comment_divs = soup.find_all('div', class_='comment')
        for comment in comment_divs[:50]:  # Limit to 50 comments for token management
            comment_num = comment.find('a', class_='permalink')
            author = comment.find('span', class_='username')
            content = comment.find('div', class_='content')
            
            if comment_num and author and content:
                comments.append({
                    'number': comment_num.get_text(strip=True),
                    'author': author.get_text(strip=True),
                    'content': content.get_text(strip=True)[:500]  # Truncate long comments
                })
        
        metadata['comments'] = comments
        
        return metadata
    except Exception as e:
        print(f"Error scraping issue {url}: {e}")
        return None

def analyze_issue_thread(row, model, url):
    """Use AI to analyze the full issue thread and generate summaries."""
    
    # Scrape the issue page
    issue_data = scrape_drupal_issue(url)
    if not issue_data:
        return "", "", "", ""
    
    # Build comment summary for AI
    comments_text = "\n".join([
        f"#{c['number']} by {c['author']}: {c['content'][:300]}"
        for c in issue_data.get('comments', [])
    ])
    
    prompt = f"""
Analyze this Drupal accessibility issue thread and provide:

ISSUE: {row['Issue Title']}
REPORTER: {issue_data.get('reporter_info', 'Unknown')}
FOLLOWERS: {issue_data.get('followers', 'Unknown')}
RECENT FILES/PATCHES: {', '.join(issue_data.get('recent_files', []))}

COMMENT THREAD:
{comments_text}

ORIGINAL DESCRIPTION: {row['Description']}

Provide 4 outputs in this EXACT format:

JOURNEY: A chronological summary of the discussion (who said what, key decisions, concerns raised). Keep it concise like: "#3 jannakha reported, #4 smustgrave needed failing test, #7 mgifford suggested upstream issue..."

TODO: List of specific outstanding tasks needed to resolve this issue (e.g., "Needs screen reader testing", "Awaiting CKEditor5 upstream fix")

PASTE_SUMMARY: A 2-3 sentence summary that could be pasted into the issue to update status (e.g., "Current status: Patch available in #31 but needs screen reader testing. Waiting on CKEditor5 upstream resolution from #26.")

RESOURCES: 3-5 relevant W3C or accessibility expert resources related to the specific accessibility barrier discussed (WCAG success criteria, ARIA authoring practices, WebAIM articles, Deque blogs, etc.). Format as: "- [Title](URL): Brief description"

Format your response exactly as:
JOURNEY: ...
TODO: ...
PASTE_SUMMARY: ...
RESOURCES: ...
"""
    
    try:
        resp = model.generate_content(prompt)
        text = resp.text
        
        journey = ""
        todo = ""
        paste = ""
        resources = ""
        
        # Parse response
        lines = text.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            if line.startswith('JOURNEY:'):
                if current_section and section_content:
                    # Save previous section
                    content = ' '.join(section_content).strip()
                    if current_section == 'JOURNEY':
                        journey = content
                    elif current_section == 'TODO':
                        todo = content
                    elif current_section == 'PASTE_SUMMARY':
                        paste = content
                    elif current_section == 'RESOURCES':
                        resources = content
                current_section = 'JOURNEY'
                section_content = [line.replace('JOURNEY:', '').strip()]
            elif line.startswith('TODO:'):
                if current_section and section_content:
                    content = ' '.join(section_content).strip()
                    if current_section == 'JOURNEY':
                        journey = content
                current_section = 'TODO'
                section_content = [line.replace('TODO:', '').strip()]
            elif line.startswith('PASTE_SUMMARY:'):
                if current_section and section_content:
                    content = ' '.join(section_content).strip()
                    if current_section == 'TODO':
                        todo = content
                current_section = 'PASTE_SUMMARY'
                section_content = [line.replace('PASTE_SUMMARY:', '').strip()]
            elif line.startswith('RESOURCES:'):
                if current_section and section_content:
                    content = ' '.join(section_content).strip()
                    if current_section == 'PASTE_SUMMARY':
                        paste = content
                current_section = 'RESOURCES'
                section_content = [line.replace('RESOURCES:', '').strip()]
            elif current_section and line.strip():
                section_content.append(line.strip())
        
        # Save last section
        if current_section and section_content:
            content = ' '.join(section_content).strip()
            if current_section == 'RESOURCES':
                resources = content
        
        return journey, todo, paste, resources
        
    except Exception as e:
        print(f"Error analyzing thread: {e}")
        return "", "", "", ""

def run(results_dir, ai_config):
    """Analyze issue threads for all issues."""
    files = sorted(results_dir.glob("issues_summarized_*.csv"))
    if not files:
        print("No summarized issues found to analyze.")
        return
    
    infile = files[-1]
    print(f"Reading from {infile}")
    df = pd.read_csv(infile)
    
    # Ensure output columns exist
    for col in ['thread_journey', 'thread_todo', 'paste_summary', 'related_resources']:
        if col not in df.columns:
            df[col] = ""
    
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
    
    # Determine output file
    timestamp = pd.Timestamp.now().strftime('%Y%m%d')
    outfile = results_dir / f"issues_thread_analyzed_{timestamp}.csv"
    
    print(f"Analyzing threads for {len(df)} issues...")
    
    for idx, row in df.iterrows():
        # Skip if already analyzed
        if pd.notna(row.get('thread_journey')) and row.get('thread_journey'):
            continue
        
        issue_url = row.get('Issue URL', '')
        if not issue_url or 'drupal.org' not in issue_url:
            print(f"Skipping {idx+1}/{len(df)}: No valid Drupal.org URL")
            continue
        
        print(f"Processing {idx+1}/{len(df)}: {row['Issue Title'][:50]}...")
        
        try:
            journey, todo, paste, resources = analyze_issue_thread(row, model, issue_url)
            
            df.at[idx, 'thread_journey'] = journey
            df.at[idx, 'thread_todo'] = todo
            df.at[idx, 'paste_summary'] = paste
            df.at[idx, 'related_resources'] = resources
            
            # Save progress incrementally
            if (idx + 1) % 10 == 0:
                df.to_csv(outfile, index=False)
                print(f"  Checkpoint: Saved {idx + 1} analyzed issues")
            
            # Rate limiting
            time.sleep(2)
            
        except Exception as e:
            print(f"  Error analyzing issue: {e}")
            continue
    
    df.to_csv(outfile, index=False)
    print(f"Thread analysis complete. Saved to {outfile}")
