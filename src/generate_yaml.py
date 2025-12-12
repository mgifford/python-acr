import yaml
import json
import pandas as pd
from datetime import datetime

# Define the standard OpenACR template structure
OPENACR_TEMPLATE = {
    "title": "Drupal Accessibility Conformance Report",
    "report_date": "",
    "chapters": {
        "success_criteria_level_a": {"criteria": []},
        "success_criteria_level_aa": {"criteria": []},
        "success_criteria_level_aaa": {"criteria": []}
    }
}

def get_level(sc):
    # Simplified mapping logic. In a real app, use a proper WCAG map.
    # Level A
    if sc.startswith('1.1') or sc.startswith('1.2') or sc.startswith('1.3') or sc.startswith('1.4.1') or sc.startswith('1.4.2'):
        return 'success_criteria_level_a'
    if sc.startswith('2.1') or sc.startswith('2.2') or sc.startswith('2.3') or sc.startswith('2.4.1') or sc.startswith('2.4.2') or sc.startswith('2.4.3') or sc.startswith('2.4.4'):
        return 'success_criteria_level_a'
    if sc.startswith('3.1.1') or sc.startswith('3.2.1') or sc.startswith('3.2.2') or sc.startswith('3.3.1') or sc.startswith('3.3.2'):
        return 'success_criteria_level_a'
    if sc.startswith('4.1'):
        return 'success_criteria_level_a'
        
    # Level AA (Everything else for now for simplicity, or add specific logic)
    return 'success_criteria_level_aa'

def run(results_dir):
    infile = results_dir / "wcag-acr-consolidated.csv"
    if not infile.exists():
        print("No consolidated report found.")
        return

    df = pd.read_csv(infile)
    
    # Load template
    report = OPENACR_TEMPLATE.copy()
    report['report_date'] = datetime.now().strftime("%Y-%m-%d")

    for _, row in df.iterrows():
        sc = str(row['WCAG SC'])
        level_key = get_level(sc)
        
        # Create the criterion object exactly as OpenACR expects it
        criterion = {
            "num": sc,
            "components": [
                {
                    "name": "web",
                    "adherence": {
                        "level": row['ACR Assessment'],  # e.g. "partially-supports"
                        "notes": row['ACR Summary']
                    }
                }
            ]
        }
        
        # Append to the correct chapter
        # Ensure the chapter exists (it should from template)
        if level_key in report['chapters']:
            report['chapters'][level_key]['criteria'].append(criterion)

    # Dump to YAML
    yaml_outfile = results_dir / "openacr-report.yaml"
    with open(yaml_outfile, 'w') as f:
        yaml.dump(report, f, sort_keys=False, default_flow_style=False)
    print(f"Generated OpenACR YAML: {yaml_outfile}")
    
    # Dump to JSON
    json_outfile = results_dir / "openacr-report.json"
    with open(json_outfile, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Generated OpenACR JSON: {json_outfile}")
