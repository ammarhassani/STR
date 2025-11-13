#!/usr/bin/env python3
"""
Fix Approval Workflow Script

This script fixes databases that were created before the migration bug was fixed.
It manually runs the migrations to add the necessary approval workflow tables and columns.

Usage:
    python fix_approval_workflow.py

The script will use the database path from your configuration.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config
from database.migrations import migrate_database


def main():
    """Main function to fix the approval workflow."""
    print("=" * 60)
    print("FIU Approval Workflow Fix")
    print("=" * 60)
    print()

    # Load configuration
    try:
        Config.load()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return 1

    # Check if system is configured
    if not Config.is_configured():
        print("Error: System is not configured yet.")
        print("Please run the application first to complete the setup wizard.")
        return 1

    db_path = Config.DATABASE_PATH
    print(f"Database path: {db_path}")

    # Check if database exists
    if not Path(db_path).exists():
        print(f"Error: Database file not found at {db_path}")
        return 1

    print()
    print("Running migrations to fix approval workflow...")
    print()

    # Run migrations
    success, message = migrate_database(db_path)

    if success:
        print("✓ Success!")
        print(f"  {message}")
        print()
        print("The approval workflow should now be working correctly.")
        print("Please restart the application to see the changes.")
        return 0
    else:
        print("✗ Failed!")
        print(f"  {message}")
        print()
        print("Please check the error message above and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
