import yaml
import pandas as pd
from datetime import datetime

# Define the complete OpenACR template structure matching the 2.4-edition-wcag-2.1-508-en catalog
def create_openacr_template():
    """Create a complete OpenACR template matching the official format."""
    return {
        "title": "Accessibility Conformance Report",
        "product": {
            "name": "",
            "version": "",
            "description": ""
        },
        "author": {
            "name": "",
            "company_name": "",
            "address": "",
            "email": "",
            "phone": "",
            "website": ""
        },
        "vendor": {
            "name": "",
            "company_name": "",
            "address": "",
            "email": "",
            "phone": "",
            "website": ""
        },
        "report_date": "",
        "last_modified_date": "",
        "version": 1,
        "notes": "",
        "evaluation_methods_used": "",
        "legal_disclaimer": "",
        "repository": "",
        "feedback": "",
        "license": "CC-BY-4.0",
        "related_openacrs": [],
        "catalog": "2.4-edition-wcag-2.1-508-en",
        "chapters": {
            "success_criteria_level_a": {
                "notes": "",
                "disabled": False,
                "criteria": []
            },
            "success_criteria_level_aa": {
                "notes": "",
                "disabled": False,
                "criteria": []
            },
            "success_criteria_level_aaa": {
                "notes": "",
                "disabled": False,
                "criteria": []
            },
            "functional_performance_criteria": {
                "notes": "",
                "disabled": False,
                "criteria": []
            },
            "hardware": {
                "notes": "",
                "disabled": False,
                "criteria": []
            },
            "software": {
                "notes": "",
                "disabled": False,
                "criteria": []
            },
            "support_documentation_and_services": {
                "notes": "",
                "disabled": False,
                "criteria": []
            }
        }
    }

def get_wcag_level(sc):
    """Map WCAG Success Criterion to conformance level (A, AA, AAA)."""
    # WCAG 2.1 Level A criteria
    level_a = [
        '1.1.1', '1.2.1', '1.2.2', '1.2.3', '1.3.1', '1.3.2', '1.3.3',
        '1.4.1', '1.4.2', '2.1.1', '2.1.2', '2.1.4', '2.2.1', '2.2.2',
        '2.3.1', '2.4.1', '2.4.2', '2.4.3', '2.4.4', '2.5.1', '2.5.2',
        '2.5.3', '2.5.4', '3.1.1', '3.2.1', '3.2.2', '3.3.1', '3.3.2',
        '4.1.1', '4.1.2'
    ]
    
    # WCAG 2.1 Level AA criteria
    level_aa = [
        '1.2.4', '1.2.5', '1.3.4', '1.3.5', '1.4.3', '1.4.4', '1.4.5',
        '1.4.10', '1.4.11', '1.4.12', '1.4.13', '2.4.5', '2.4.6', '2.4.7',
        '3.1.2', '3.2.3', '3.2.4', '3.3.3', '3.3.4', '4.1.3'
    ]
    
    # WCAG 2.1 Level AAA criteria
    level_aaa = [
        '1.2.6', '1.2.7', '1.2.8', '1.2.9', '1.3.6', '1.4.6', '1.4.7',
        '1.4.8', '1.4.9', '2.1.3', '2.2.3', '2.2.4', '2.2.5', '2.2.6',
        '2.3.2', '2.3.3', '2.4.8', '2.4.9', '2.4.10', '2.5.5', '2.5.6',
        '3.1.3', '3.1.4', '3.1.5', '3.1.6', '3.2.5', '3.3.5', '3.3.6'
    ]
    
    if sc in level_a:
        return 'success_criteria_level_a'
    elif sc in level_aa:
        return 'success_criteria_level_aa'
    elif sc in level_aaa:
        return 'success_criteria_level_aaa'
    else:
        # Default to Level AA if unknown
        return 'success_criteria_level_aa'

def run(results_dir):
    """Generate OpenACR YAML report from consolidated CSV."""
    infile = results_dir / "wcag-acr-consolidated.csv"
    if not infile.exists():
        print("No consolidated report found.")
        return

    df = pd.read_csv(infile)
    
    # Create report from template
    report = create_openacr_template()
    today = datetime.now().strftime("%Y-%m-%d")
    report['report_date'] = today
    report['last_modified_date'] = today

    # Process each issue and populate the appropriate WCAG criteria
    for _, row in df.iterrows():
        sc = str(row['WCAG SC']).strip()
        level_key = get_wcag_level(sc)
        
        # Create the criterion object following OpenACR format
        criterion = {
            "num": sc,
            "components": [
                {
                    "name": "web",
                    "adherence": {
                        "level": row.get('ACR Assessment', ''),  # e.g. "partially-supports", "does-not-support"
                        "notes": row.get('ACR Summary', '')
                    }
                },
                {
                    "name": "electronic-docs",
                    "adherence": {
                        "level": "",
                        "notes": ""
                    }
                },
                {
                    "name": "software",
                    "adherence": {
                        "level": "",
                        "notes": ""
                    }
                },
                {
                    "name": "authoring-tool",
                    "adherence": {
                        "level": "",
                        "notes": ""
                    }
                }
            ]
        }
        
        # Append to the correct chapter
        if level_key in report['chapters']:
            report['chapters'][level_key]['criteria'].append(criterion)

    # Output only YAML format
    yaml_outfile = results_dir / "openacr-report.yaml"
    with open(yaml_outfile, 'w') as f:
        yaml.dump(report, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
    print(f"✅ Generated OpenACR YAML: {yaml_outfile}")
