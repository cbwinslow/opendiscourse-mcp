#!/usr/bin/env python3
"""
Crew AI Runner for OpenDiscourse Project
Runs specialized crews for documentation, database administration, software design, and engineering.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_dependencies():
    """Check if Crew AI dependencies are installed."""
    try:
        import crewai
        import crewai_tools
        print("✓ Crew AI dependencies are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependencies: {e}")
        print("Please run: pip install crewai crewai-tools")
        return False

def run_crew(crew_name, crew_object):
    """Run a specific crew."""
    try:
        print(f"\n🚀 Running {crew_name}...")
        crew_object.kickoff()
        print(f"✓ {crew_name} completed successfully")
    except Exception as e:
        print(f"✗ Error running {crew_name}: {e}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Run Crew AI crews for OpenDiscourse")
    parser.add_argument(
        "crew",
        nargs="?",
        choices=["documentation", "database", "design", "engineering", "all"],
        default="all",
        help="Which crew to run (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually running crews"
    )

    args = parser.parse_args()

    if not check_dependencies():
        return 1

    if args.dry_run:
        print("🔍 Dry run mode - would run the following crews:")
        crews = {
            "documentation": "Documentation Crew",
            "database": "Database Administration Crew",
            "design": "Software Design Crew",
            "engineering": "Engineering Crew"
        }
        if args.crew == "all":
            for name, desc in crews.items():
                print(f"  - {desc}")
        else:
            print(f"  - {crews[args.crew]}")
        return 0

    # Import crew modules
    crews_to_run = []
    if args.crew == "all":
        crews_to_run = ["documentation", "database", "design", "engineering"]
    else:
        crews_to_run = [args.crew]

    success_count = 0
    for crew_type in crews_to_run:
        try:
            if crew_type == "documentation":
                import documentation_crew
                crew_name = "Documentation Crew"
                crew_obj = documentation_crew.documentation_crew
            elif crew_type == "database":
                import database_admin_crew
                crew_name = "Database Administration Crew"
                crew_obj = database_admin_crew.database_admin_crew
            elif crew_type == "design":
                import software_design_crew
                crew_name = "Software Design Crew"
                crew_obj = software_design_crew.software_design_crew
            elif crew_type == "engineering":
                import engineering_crew
                crew_name = "Engineering Crew"
                crew_obj = engineering_crew.engineering_crew

            if run_crew(crew_name, crew_obj):
                success_count += 1

        except ImportError as e:
            print(f"✗ Failed to import {crew_type} crew: {e}")
        except Exception as e:
            print(f"✗ Unexpected error with {crew_type} crew: {e}")

    print(f"\n📊 Results: {success_count}/{len(crews_to_run)} crews completed successfully")

    if success_count == len(crews_to_run):
        print("🎉 All crews completed successfully!")
        return 0
    else:
        print("⚠️  Some crews failed to complete")
        return 1

if __name__ == "__main__":
    sys.exit(main())
