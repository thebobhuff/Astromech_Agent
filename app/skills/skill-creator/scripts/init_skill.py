import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Initialize a new skill.")
    parser.add_argument("name", help="Name of the skill")
    parser.add_argument("--path", required=True, help="Output directory path (e.g. app/skills)")
    parser.add_argument("--resources", help="Comma-separated list of resources (scripts, references, assets)")
    parser.add_argument("--examples", action="store_true", help="Add example files")
    
    args = parser.parse_args()
    
    skill_name = args.name.lower().replace(" ", "-")
    base_path = os.path.join(args.path, skill_name)
    
    if os.path.exists(base_path):
        print(f"Error: Skill directory already exists at {base_path}")
        sys.exit(1)
        
    os.makedirs(base_path)
    print(f"Created skill directory: {base_path}")
    
    # Create SKILL.md
    skill_md_content = f"""---
name: {skill_name}
description: TODO: Add a description of what this skill does and when to use it.
---

# {skill_name.replace("-", " ").title()}

## Usage

TODO: Add instructions on how to use this skill.
"""
    with open(os.path.join(base_path, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_md_content)
    print("Created SKILL.md")

    # Create resources
    if args.resources:
        resources = args.resources.split(",")
        for res in resources:
            res_dir = os.path.join(base_path, res.strip())
            os.makedirs(res_dir, exist_ok=True)
            print(f"Created resource directory: {res_dir}")
            
            if args.examples and res.strip() == "scripts":
                 with open(os.path.join(res_dir, "example.py"), "w") as f:
                     f.write("# Example script\nprint('Hello from the skill!')")

if __name__ == "__main__":
    main()
