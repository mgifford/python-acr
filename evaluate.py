import pandas as pd
import os
import json
from azure.ai.evaluation import (
    evaluate,
    GroundednessEvaluator,
    RelevanceEvaluator,
    CoherenceEvaluator,
    OpenAIModelConfiguration
)

def main():
    # 1. Prepare Data
    print("Preparing evaluation dataset...")
    try:
        df = pd.read_csv("responses.csv")
    except FileNotFoundError:
        print("Error: responses.csv not found. Please run collect_responses.py first.")
        return

    # Convert to JSONL format required by evaluate()
    # Mapping:
    # query -> Issue Title
    # context -> Description
    # response -> acr_note
    
    jsonl_data = []
    for _, row in df.iterrows():
        entry = {
            "query": row.get("Issue Title", ""),
            "context": row.get("Description", ""),
            "response": row.get("acr_note", "")
        }
        jsonl_data.append(entry)
        
    data_path = "evaluation_dataset.jsonl"
    with open(data_path, "w") as f:
        for entry in jsonl_data:
            f.write(json.dumps(entry) + "\n")
            
    print(f"Saved evaluation dataset to {data_path}")

    # 2. Configure Model (Ollama)
    # Pointing to local Ollama instance acting as an OpenAI-compatible server
    model_config = OpenAIModelConfiguration(
        type="openai",
        model="gemma3:4b", # Using the same model available locally
        base_url="http://localhost:11434/v1",
        api_key="ollama" # Ollama doesn't require a key, but SDK might expect a non-empty string
    )

    # 3. Initialize Evaluators
    print("Initializing evaluators...")
    groundedness_eval = GroundednessEvaluator(model_config)
    relevance_eval = RelevanceEvaluator(model_config)
    coherence_eval = CoherenceEvaluator(model_config)

    # 4. Run Evaluation
    print("Running evaluation... (this may take a moment)")
    result = evaluate(
        data=data_path,
        evaluators={
            "groundedness": groundedness_eval,
            "relevance": relevance_eval,
            "coherence": coherence_eval
        },
        evaluator_config={
            "groundedness": {
                "column_mapping": {
                    "response": "${data.response}",
                    "context": "${data.context}"
                }
            },
            "relevance": {
                "column_mapping": {
                    "query": "${data.query}",
                    "response": "${data.response}"
                }
            },
            "coherence": {
                "column_mapping": {
                    "query": "${data.query}",
                    "response": "${data.response}"
                }
            }
        },
        output_path="evaluation_results.json"
    )

    # 5. Display Results
    print("\n--- Evaluation Results ---")
    if result.get("metrics"):
        print("Aggregate Metrics:")
        for metric, value in result["metrics"].items():
            print(f"{metric}: {value}")
    
    print(f"\nDetailed results saved to evaluation_results.json")

if __name__ == "__main__":
    main()
