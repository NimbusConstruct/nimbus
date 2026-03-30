import sys
import os
import argparse
import json
from datetime import datetime
from collections import Counter

from nimbus.engine import SmartArchitectureEngine
from nimbus.explainer import get_explanation
from nimbus.comparison import compare_architectures
from nimbus.generators.factory import generate_infrastructure

# Ensure cross-platform package path
package_root = os.path.dirname(os.path.abspath(__file__))
if package_root not in sys.path:
    sys.path.insert(0, package_root)


HISTORY_DIR = os.path.join("projects")
os.makedirs(HISTORY_DIR, exist_ok=True)


def generate_unique_filename(base="project"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}_{timestamp}.json"


def load_previous_projects():
    projects = []
    for fname in os.listdir(HISTORY_DIR):
        if fname.endswith(".json"):
            with open(os.path.join(HISTORY_DIR, fname), "r") as f:
                projects.append(json.load(f))
    return projects


def suggest_default(key, choices, prev_projects):
    """
    Suggest the most common value for a field based on previous projects
    """
    if not prev_projects:
        return choices[0]  # fallback default
    values = [p[key] for p in prev_projects if key in p]
    if not values:
        return choices[0]
    most_common = Counter(values).most_common(1)[0][0]
    if most_common in choices:
        return most_common
    return choices[0]


def ask_choice(prompt, choices, default=None):
    choices_str = "/".join(choices)
    while True:
        val = input(f"{prompt} ({choices_str}) [{default}]: ").strip().lower()
        if not val and default:
            return default
        if val in choices:
            return val
        print(f"❌ Invalid input. Choose from {choices_str}.")


def ask_yes_no(prompt, default="no"):
    while True:
        val = input(f"{prompt} (yes/no) [{default}]: ").strip().lower()
        if not val:
            val = default
        if val in ["yes", "y"]:
            return True
        elif val in ["no", "n"]:
            return False
        print("❌ Please enter yes or no.")


def ask_multiple(prompt, options):
    """
    Prompt user to select multiple options from a comma-separated list
    """
    print(f"{prompt} (choose any, comma-separated)")
    print(f"Available: {', '.join(options)}")
    val = input("Your choices: ").strip().lower()
    selected = [x.strip() for x in val.split(",") if x.strip() in options]
    return selected


def print_live_recommendation(project):
    """
    Run the architecture engine and print live suggestions
    """
    try:
        engine = SmartArchitectureEngine(project)
        result = engine.analyze()

        best = result["recommended"]
        details = result["details"][best]
        explanation = get_explanation(best)

        print("\n💡 Live Architecture Suggestion")
        print(f"   → {best}")
        print(f"   Confidence: {details['confidence']}")

        print("\n   Why:")
        for w in explanation["why"]:
            print(f"    - {w}")

        print("\n   Tradeoffs:")
        for t in explanation["tradeoffs"]:
            print(f"    - {t}")

        print("\n   Avoid When:")
        for a in explanation["avoid_when"]:
            print(f"    - {a}")
        print()
        print(compare_architectures(result["details"]))

    except Exception:
        # avoid crashing intake if partial data
        pass


def run_intake_form():
    """
    Semi-AI assisted client intake form with LIVE architecture suggestions
    """
    print("\n=== Nimbus AI-Assisted Intake (Live Architecture Mode) ===\n")
    project = {}

    prev_projects = load_previous_projects()

    # 1️⃣ App Type
    project['app_type'] = ask_choice(
        "App type", ["brochure", "dynamic", "saas"],
        default=suggest_default("app_type", ["brochure", "dynamic", "saas"], prev_projects)
    )
    print_live_recommendation(project)

    # 2️⃣ Auth
    project['auth_required'] = ask_yes_no(
        "Authentication required?",
        default="yes" if suggest_default("auth_required", [True, False], prev_projects) else "no"
    )

    # 3️⃣ Scale
    project['user_scale'] = ask_choice(
        "Expected user scale", ["small", "medium", "large"],
        default=suggest_default("user_scale", ["small", "medium", "large"], prev_projects)
    )
    print_live_recommendation(project)

    # 4️⃣ Integrations
    project['integrations'] = ask_multiple(
        "Integrations", ["slack", "jira", "github"]
    )
    print_live_recommendation(project)

    # 5️⃣ Real-time
    project['real_time'] = ask_yes_no(
        "Real-time functionality?",
        default="yes" if suggest_default("real_time", [True, False], prev_projects) else "no"
    )
    print_live_recommendation(project)

    # 6️⃣ Security
    project['sensitive_data'] = ask_yes_no(
        "Will app handle sensitive data?",
        default="yes" if suggest_default("sensitive_data", [True, False], prev_projects) else "no"
    )

    project['compliance'] = ask_yes_no(
        "Need compliance (HIPAA/GDPR)?",
        default="yes" if suggest_default("compliance", [True, False], prev_projects) else "no"
    )
    print_live_recommendation(project)

    # 7️⃣ Deployment
    project['deployment'] = ask_choice(
        "Deployment type", ["container", "serverless", "onprem"],
        default=suggest_default("deployment", ["container", "serverless", "onprem"], prev_projects)
    )
    print_live_recommendation(project)

    # Generate unique JSON filename
    filename = generate_unique_filename()
    os.makedirs("projects", exist_ok=True)
    filepath = os.path.join("projects", filename)

    # Save JSON
    with open(filepath, "w") as f:
        json.dump(project, f, indent=4)

    # Save to history (for future AI suggestions)
    history_file = os.path.join(HISTORY_DIR, filename)
    with open(history_file, "w") as f:
        json.dump(project, f, indent=4)

    print(f"\n✅ Project JSON created: {filepath}")
    print(f"\n🚀 Final Recommendation:")
    print_live_recommendation(project)

    return filepath


def load_project(path):
    with open(path, "r") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(prog="nimbus")
    subparsers = parser.add_subparsers(dest="command")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze project JSON")
    analyze_parser.add_argument("file", help="Path to project JSON file")

    # intake command
    intake_parser = subparsers.add_parser("intake", help="Run semi-AI assisted intake form")
    
    generate_parser = subparsers.add_parser("generate", help="Generate infrastructure templates")
    generate_parser.add_argument("file", help="Project JSON file")
    generate_parser.add_argument(
    "--env",
    choices=["dev", "staging", "prod"],
    default="dev",
    help="Deployment environment"
)

    args = parser.parse_args()

    if args.command == "analyze":
        project = load_project(args.file)
        engine = SmartArchitectureEngine(project)
        result = engine.analyze()

        print("\n=== Nimbus Architecture Recommendation ===\n")
        print(f"Recommended: {result['recommended']}\n")
        print("Reasons:")
        for r in result["explanation"]:
            print(f" - {r}")

        print("\nDetailed Scores:")
        for arch, data in result["details"].items():
            print(f"\n{arch}")
            print(f"  Score: {data['score']}")
            print(f"  Confidence: {data['confidence']}")
            for reason in data["reasons"]:
                print(f"   - {reason}")

    elif args.command == "intake":
        filepath = run_intake_form()
        print(f"\nYou can now run:\n  nimbus analyze {filepath}")
        
    elif args.command == "generate":
        project = load_project(args.file)

        engine = SmartArchitectureEngine(project)
        result = engine.analyze()

        architecture = result["recommended"]

        project_name = os.path.basename(args.file).replace(".json", "")
        output_dir = os.path.join("output", project_name)

        generate_infrastructure(
            project,
            architecture,
            output_dir,
            env=args.env
        )

        print(f"\n✅ Infrastructure generated in: {output_dir}")
        print(f"Environment: {args.env}")
        print(f"Architecture: {architecture}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()