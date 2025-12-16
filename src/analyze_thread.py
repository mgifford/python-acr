import pandas as pd
import os
import sys
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

def fetch_github_thread(url):
    """Fetch GitHub issue comments using API with pagination."""
    try:
        # Parse URL: https://github.com/owner/repo/issues/number
        parts = url.replace("https://github.com/", "").split("/")
        if len(parts) < 4 or parts[2] != "issues":
            print(f"Invalid GitHub URL format: {url}")
            return None
            
        owner = parts[0]
        repo = parts[1]
        issue_number = parts[3]
        
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
        
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"
            
        all_comments = []
        page = 1
        per_page = 100
        
        while True:
            params = {'page': page, 'per_page': per_page}
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"Error fetching GitHub comments: {response.status_code}")
                break
                
            comments_data = response.json()
            if not comments_data:
                break
                
            for idx, comment in enumerate(comments_data):
                # Calculate global index (1-based)
                global_idx = (page - 1) * per_page + idx + 1
                all_comments.append({
                    'number': str(global_idx), # Use sequential number for readability
                    'original_id': str(comment['id']),
                    'author': comment['user']['login'],
                    'content': comment['body'][:1000] if comment['body'] else ""
                })
            
            if len(comments_data) < per_page:
                break
                
            page += 1
        
        metadata = {
            'reporter_info': f"GitHub Issue #{issue_number}",
            'followers': "N/A",
            'recent_files': [], # GitHub attachments are harder to list simply
            'comments': all_comments
        }
            
        return metadata

    except Exception as e:
        print(f"Error fetching GitHub thread {url}: {e}")
        return None

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
        for comment in comment_divs[:200]:  # Increased limit to 200
            comment_num = comment.find('a', class_='permalink')
            author = comment.find('span', class_='username')
            content = comment.find('div', class_='content')
            
            if comment_num and author and content:
                comments.append({
                    'number': comment_num.get_text(strip=True).replace('#', ''),
                    'author': author.get_text(strip=True),
                    'content': content.get_text(strip=True)[:1000]  # Increased truncation limit
                })
        
        metadata['comments'] = comments
        
        return metadata
    except Exception as e:
        print(f"Error scraping issue {url}: {e}")
        return None

def analyze_issue_thread(row, model, url):
    """Use AI to analyze the full issue thread and generate summaries."""
    
    issue_data = None
    if "github.com" in url:
        issue_data = fetch_github_thread(url)
    else:
        # Scrape the issue page (Drupal)
        issue_data = scrape_drupal_issue(url)
        
    if not issue_data:
        return "", "", "", ""
    
    # Build comment summary for AI
    comments_text = "\n".join([
        f"#{c['number']} by {c['author']}: {c['content'][:300]}"
        for c in issue_data.get('comments', [])
    ])
    
    prompt = f"""
Analyze this accessibility issue thread and provide a structured summary.

ISSUE: {row['Issue Title']}
REPORTER: {issue_data.get('reporter_info', 'Unknown')}
FOLLOWERS: {issue_data.get('followers', 'Unknown')}
RECENT FILES/PATCHES: {', '.join(issue_data.get('recent_files', []))}

COMMENT THREAD:
{comments_text}

ORIGINAL DESCRIPTION: {row['Description']}

CRITICAL INSTRUCTIONS:
1. DO NOT INVENT OR HALLUCINATE: Only use actual usernames, comment numbers, and events from the thread above. Never create fake users like "Alice", "UserB", or "CKEditor-Dev" unless they appear in the comments.
2. BE EXPLICIT ABOUT LIMITED DATA: If there are only 1-2 comments, say "minimal discussion" or "only initial report". Don't speculate about what "probably" happened.
3. NO REDUNDANT LINKS: Do NOT include the original issue URL in LINKS (it's already captured elsewhere in the report).
4. USE ACTUAL COMMENT NUMBERS: Reference the #number from the COMMENT THREAD above, not invented numbers.
5. SENTIMENT ACCURACY: Look carefully at WHO is commenting. If 2+ different people engage (commenting, agreeing, proposing solutions), use "Active collaboration" or "Minimal engagement". Only use "Initial report only" if literally just the original reporter posted with no other participants.
6. LINK TO SPECIFIC COMMENTS: When mentioning a GitHub comment, format as: https://github.com/owner/repo/issues/NUMBER#issuecomment-ID

Provide 5 outputs in this EXACT format:

TLDR: A high-level executive summary (2-3 sentences) of the issue and its current status. Be honest if status is unknown.

PROBLEM_STATEMENT: A clear definition of the accessibility barrier, referencing specific WCAG criteria if applicable.

SENTIMENT: One of: "Active collaboration", "Minimal engagement", "Stalled (no recent activity)", or "Initial report only". Look at participant count: 1 person = "Initial report only", 2+ people = engagement level based on constructive discussion.

TIMELINE: A chronological summary using ONLY actual comment numbers and usernames from the COMMENT THREAD above.
CRITICAL: Put each timeline entry on its OWN LINE. Do not run them together.
Format each entry on a new line:
# 1 johndoe: Reported the issue with reproduction steps.
# 3 janedoe: Confirmed bug and suggested adding aria-label.
# 5 johndoe: Tested the fix and confirmed it works.

If there are fewer than 3 comments, be explicit:
# 1 reporter: Filed initial bug report. No further discussion.

LINKS: Relevant WCAG docs, MDN pages, or related external issues mentioned in comments. DO NOT include the original issue URL. Format as "- [Title](URL): Brief description"

Format your response exactly as:
TLDR: ...
PROBLEM_STATEMENT: ...
SENTIMENT: ...
TIMELINE: ...
LINKS: ...
"""
    
    try:
        resp = model.generate_content(prompt)
        text = resp.text
        
        tldr = ""
        problem = ""
        sentiment = ""
        timeline = ""
        links = ""
        
        # Parse response
        lines = text.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            if line.startswith('TLDR:'):
                if current_section and section_content:
                    # Save previous section
                    content = ' '.join(section_content).strip()
                    if current_section == 'TLDR': tldr = content
                    elif current_section == 'PROBLEM_STATEMENT': problem = content
                    elif current_section == 'SENTIMENT': sentiment = content
                    elif current_section == 'TIMELINE': timeline = content
                    elif current_section == 'LINKS': links = content
                current_section = 'TLDR'
                section_content = [line.replace('TLDR:', '').strip()]
            elif line.startswith('PROBLEM_STATEMENT:'):
                if current_section and section_content:
                    content = ' '.join(section_content).strip()
                    if current_section == 'TLDR': tldr = content
                current_section = 'PROBLEM_STATEMENT'
                section_content = [line.replace('PROBLEM_STATEMENT:', '').strip()]
            elif line.startswith('SENTIMENT:'):
                if current_section and section_content:
                    content = ' '.join(section_content).strip()
                    if current_section == 'PROBLEM_STATEMENT': problem = content
                current_section = 'SENTIMENT'
                section_content = [line.replace('SENTIMENT:', '').strip()]
            elif line.startswith('TIMELINE:'):
                if current_section and section_content:
                    content = ' '.join(section_content).strip()
                    if current_section == 'SENTIMENT': sentiment = content
                current_section = 'TIMELINE'
                section_content = [line.replace('TIMELINE:', '').strip()]
            elif line.startswith('LINKS:'):
                if current_section and section_content:
                    content = ' '.join(section_content).strip()
                    if current_section == 'TIMELINE': timeline = content
                current_section = 'LINKS'
                section_content = [line.replace('LINKS:', '').strip()]
            elif current_section and line.strip():
                section_content.append(line.strip())
        
        # Save last section
        if current_section and section_content:
            content = ' '.join(section_content).strip()
            if current_section == 'LINKS':
                links = content
        
        return tldr, problem, sentiment, timeline, links
        
    except Exception as e:
        error_str = str(e)
        # Check for critical quota/rate limit errors
        if "429" in error_str or "quota" in error_str.lower():
            print(f"\nCRITICAL ERROR: API Quota Exceeded or Rate Limit Hit.")
            print(f"Details: {error_str.splitlines()[0]}")
            print("Exiting gracefully to prevent further errors.")
            sys.exit(1)

        # Clean up verbose error messages
        error_msg = error_str.split('\n')[0]
        if len(error_msg) > 200: error_msg = error_msg[:200] + "..."
        print(f"Error analyzing thread: {error_msg}")
        return "", "", "", ""

def run(results_dir, ai_config, limit=None):
    """Analyze issue threads for all issues."""
    files = sorted(results_dir.glob("issues_summarized_*.csv"))
    if not files:
        print("No summarized issues found to analyze.")
        return
    
    infile = files[-1]
    print(f"Reading from {infile}")
    df = pd.read_csv(infile)
    
    # Apply limit if specified
    if limit:
        print(f"Limiting to first {limit} issues (out of {len(df)} total)")
        df = df.head(limit)
    
    # Ensure output columns exist
    for col in ['thread_tldr', 'thread_problem', 'thread_sentiment', 'thread_timeline', 'thread_links']:
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
        if pd.notna(row.get('thread_timeline')) and row.get('thread_timeline'):
            continue
        
        issue_url = row.get('Issue URL', '')
        if not issue_url or ('drupal.org' not in issue_url and 'github.com' not in issue_url):
            print(f"Skipping {idx+1}/{len(df)}: No valid Drupal.org or GitHub URL")
            continue
        
        print(f"Processing {idx+1}/{len(df)}: {row['Issue Title'][:50]}...")
        print(f"🔗 URL: {issue_url}")
        
        try:
            tldr, problem, sentiment, timeline, links = analyze_issue_thread(row, model, issue_url)
            
            df.at[idx, 'thread_tldr'] = tldr
            df.at[idx, 'thread_problem'] = problem
            df.at[idx, 'thread_sentiment'] = sentiment
            df.at[idx, 'thread_timeline'] = timeline
            df.at[idx, 'thread_links'] = links
            
            # Only display if we got actual content
            if tldr or problem or sentiment or timeline or links:
                print(f"\n{'='*80}")
                print(f"📋 TLDR: {tldr[:200]}..." if len(tldr) > 200 else f"📋 TLDR: {tldr}")
                print(f"\n⚠️ PROBLEM: {problem[:150]}..." if len(problem) > 150 else f"⚠️ PROBLEM: {problem}")
                print(f"\n💬 SENTIMENT: {sentiment}")
                print(f"\n📅 TIMELINE: {timeline[:200]}..." if len(timeline) > 200 else f"📅 TIMELINE: {timeline}")
                print(f"\n🔗 LINKS: {links[:200]}..." if len(links) > 200 else f"🔗 LINKS: {links}")
                print(f"{'='*80}\n")
            else:
                print("⚠️  No analysis generated (issue may have no comments or scraping failed)\n")
            
            # Save progress incrementally
            if (idx + 1) % 10 == 0:
                df.to_csv(outfile, index=False)
                print(f"  Checkpoint: Saved {idx + 1} analyzed issues")
            
            # Rate limiting
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Error analyzing issue: {e}\n")
            continue
    
    df.to_csv(outfile, index=False)
    print(f"Thread analysis complete. Saved to {outfile}")
