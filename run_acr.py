import argparse
import os
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from src import extract, summarize, consolidate, generate_yaml

def main():
    parser = argparse.ArgumentParser(description="Automated OpenACR Generator")
    parser.add_argument("--repo", type=str, help="Repo ID (e.g. 'drupal')")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4], help="Run specific step")
    
    # New AI arguments
    parser.add_argument("--ai-backend", choices=['gemini', 'ollama'], default='gemini', 
                        help="Choose AI backend (default: gemini)")
    parser.add_argument("--model", type=str, 
                        help="Specific model name (e.g., 'llama3', 'gemini-1.5-pro')")
    
    args = parser.parse_args()
    load_dotenv()

    # Create date-based results directory
    today = pd.Timestamp.now().strftime('%m-%d-%Y')
    
    # Create a specific subdirectory for this run configuration
    # This ensures we don't overwrite results when running different models/repos
    repo_name = args.repo if args.repo else "default"
    model_name = args.model.replace(":", "-") if args.model else "default"
    run_folder_name = f"{repo_name}_{args.ai_backend}_{model_name}"
    
    results_dir = Path("results") / today / run_folder_name
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
            extract.run('drupal', args.repo, results_dir)

    if not args.step or args.step == 2:
        print(f"\n--- Step 2: Summarizing with {args.ai_backend.upper()} ---")
        summarize.run(results_dir, ai_config)

    if not args.step or args.step == 3:
        print(f"\n--- Step 3: Consolidating with {args.ai_backend.upper()} ---")
        consolidate.run(results_dir, ai_config)

    if not args.step or args.step == 4:
        print("\n--- Step 4: Generating YAML ---")
        generate_yaml.run(results_dir)

if __name__ == "__main__":
    main()