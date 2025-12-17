import argparse
import os
import re
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from src import extract, summarize, analyze_thread, consolidate, generate_yaml


def find_existing_results_dir(repo_name, model_name):
    """
    Find an existing results directory for the given repo/model combination.
    Returns the most recent one if multiple exist, or None if none found.
    """
    results_path = Path("results")
    if not results_path.exists():
        return None
    
    # Pattern: repo-model-MM-DD-YYYY
    pattern = f"{repo_name}-{model_name}-"
    matching_dirs = []
    
    for dir_path in results_path.iterdir():
        if dir_path.is_dir() and dir_path.name.startswith(pattern):
            # Extract date from directory name
            date_part = dir_path.name[len(pattern):]
            # Validate date format MM-DD-YYYY
            if re.match(r'\d{2}-\d{2}-\d{4}$', date_part):
                try:
                    date = pd.to_datetime(date_part, format='%m-%d-%Y')
                    matching_dirs.append((dir_path, date))
                except:
                    continue
    
    if not matching_dirs:
        return None
    
    # Sort by date descending and return the most recent
    matching_dirs.sort(key=lambda x: x[1], reverse=True)
    return matching_dirs[0][0]


def main():
    parser = argparse.ArgumentParser(description="Automated OpenACR Generator")
    parser.add_argument("--repo", type=str, help="Repo ID (e.g. 'drupal')")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4, 5], help="Run specific step (1=extract, 2=summarize, 3=analyze threads, 4=consolidate, 5=generate YAML)")
    
    # New AI arguments
    parser.add_argument("--ai-backend", choices=['gemini', 'ollama'], default='gemini', 
                        help="Choose AI backend (default: gemini)")
    parser.add_argument("--model", type=str, 
                        help="Specific model name (e.g., 'llama3', 'gemini-1.5-pro')")
    parser.add_argument("--tags", type=str,
                        help="Comma-separated list of tags to search for (overrides default accessibility tags)")
    parser.add_argument("--limit", type=int,
                        help="Limit the number of issues to process (useful for testing)")
    parser.add_argument("--github-token", type=str,
                        help="GitHub Personal Access Token for higher API rate limits")
    parser.add_argument("--results-dir", type=str,
                        help="Use a specific results directory (overrides auto-generated name)")
    
    args = parser.parse_args()
    load_dotenv()

    # Set GitHub token in environment if provided via CLI
    if args.github_token:
        os.environ["GITHUB_TOKEN"] = args.github_token

    # Normalize repo input if it's a GitHub URL
    if args.repo and "github.com" in args.repo:
        # Strip protocol and domain
        clean_repo = args.repo.replace("https://github.com/", "").replace("http://github.com/", "")
        # Strip trailing slash
        if clean_repo.endswith("/"):
            clean_repo = clean_repo[:-1]
        args.repo = clean_repo

    # Create date-based results directory
    today = pd.Timestamp.now().strftime('%m-%d-%Y')
    
    # Create a specific subdirectory for this run configuration
    # This ensures we don't overwrite results when running different models/repos
    repo_name = args.repo.replace("/", "-") if args.repo else "default"
    model_name = args.model.replace(":", "") if args.model else "default"
    
    # Check if user specified a custom results directory
    if args.results_dir:
        results_dir = Path(args.results_dir)
        if not results_dir.is_absolute():
            # If relative path, assume it's under results/
            if not str(results_dir).startswith("results"):
                results_dir = Path("results") / results_dir
    else:
        # User requested format: CkEditor-gemma3b-12-13-2025
        run_folder_name = f"{repo_name}-{model_name}-{today}"
        results_dir = Path("results") / run_folder_name
    
    # Only check for directory overwrite if we're running step 1 or all steps
    if (not args.step or args.step == 1) and results_dir.exists():
        response = input(f"\nDirectory '{results_dir}' already exists. Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("Aborting. Please rename or delete the existing directory.")
            return
        print(f"Overwriting existing directory: {results_dir}")
    
    # For steps 2-5, ensure the directory exists (or find a previous one)
    if args.step and args.step > 1:
        if not results_dir.exists():
            # Try to find an existing directory from a previous date
            existing_dir = find_existing_results_dir(repo_name, model_name)
            if existing_dir:
                print(f"Today's directory '{results_dir}' does not exist.")
                print(f"Found existing directory: {existing_dir}")
                response = input(f"Use '{existing_dir}' instead? (y/n): ").strip().lower()
                if response == 'y':
                    results_dir = existing_dir
                else:
                    print("Aborting. Use --results-dir to specify a directory, or run step 1 first.")
                    return
            else:
                print(f"Error: Directory '{results_dir}' does not exist and no previous runs found.")
                print("Run step 1 first, or use --results-dir to specify an existing directory.")
                return
        print(f"Using existing directory: {results_dir}")
    
    results_dir.mkdir(parents=True, exist_ok=True)
    print(f"Results will be saved to: {results_dir}")

    # Pass AI config to the modules
    ai_config = {
        "backend": args.ai_backend,
        "model_name": args.model
    }

    if not args.step or args.step == 1:
        print("\n--- Step 1: Extracting Issues ---")
        if args.repo:
            tags_list = args.tags.split(",") if args.tags else None
            extract.run('drupal', args.repo, results_dir, tags=tags_list, limit=args.limit)

    if not args.step or args.step == 2:
        print(f"\n--- Step 2: Summarizing with {args.ai_backend.upper()} ---")
        summarize.run(results_dir, ai_config, limit=args.limit)

    if not args.step or args.step == 3:
        print(f"\n--- Step 3: Analyzing Issue Threads with {args.ai_backend.upper()} ---")
        analyze_thread.run(results_dir, ai_config, limit=args.limit)

    if not args.step or args.step == 4:
        print(f"\n--- Step 4: Consolidating with {args.ai_backend.upper()} ---")
        consolidate.run(results_dir, ai_config)

    if not args.step or args.step == 5:
        print("\n--- Step 5: Generating YAML ---")
        generate_yaml.run(results_dir)

if __name__ == "__main__":
    main()