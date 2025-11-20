"""
Quick-Start Deployment Script
Automates the deployment of all user test result requirements.

This script:
1. Backs up the current database
2. Runs database migrations
3. Seeds dropdown data
4. Verifies the deployment
5. Runs basic tests
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database.migrations import migrate_database
from database.seed_dropdowns import seed_dropdown_values
from config import Config


def print_header(text):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)


def print_step(step_num, text):
    """Print a step number and description."""
    print(f"\n[{step_num}] {text}")
    print("-" * 70)


def backup_database(db_path):
    """Create a backup of the database."""
    if not Path(db_path).exists():
        print("ℹ️  No existing database to backup (fresh installation)")
        return True

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{db_path}.backup_{timestamp}"

        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return True

    except Exception as e:
        print(f"❌ Backup failed: {str(e)}")
        return False


def run_migrations(db_path):
    """Run database migrations."""
    try:
        success, message = migrate_database(db_path)

        if success:
            print(f"✅ {message}")
            return True
        else:
            print(f"❌ Migration failed: {message}")
            return False

    except Exception as e:
        print(f"❌ Migration error: {str(e)}")
        return False


def seed_dropdowns(db_path):
    """Seed dropdown data."""
    try:
        # Auto-confirm for script mode
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check existing dropdowns
        cursor.execute("SELECT COUNT(*) FROM system_config WHERE config_type = 'dropdown'")
        existing_count = cursor.fetchone()[0]

        conn.close()

        if existing_count > 0:
            print(f"ℹ️  Found {existing_count} existing dropdown values")
            response = input("   Clear and re-seed? (yes/no): ").strip().lower()
            if response != 'yes':
                print("   Skipping dropdown seeding")
                return True

        # Run seeding (will clear if user confirmed)
        success = seed_dropdown_values(db_path)

        if success:
            print(f"✅ Dropdown data seeded successfully")
            return True
        else:
            print(f"❌ Dropdown seeding failed")
            return False

    except Exception as e:
        print(f"❌ Seeding error: {str(e)}")
        return False


def verify_schema(db_path):
    """Verify the schema has all required tables and columns."""
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("\nVerifying database schema...")

        # Check new tables
        required_tables = ['report_number_reservations', 'restore_log']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in required_tables:
            if table in existing_tables:
                print(f"  ✅ Table '{table}' exists")
            else:
                print(f"  ❌ Table '{table}' MISSING")
                conn.close()
                return False

        # Check new columns in reports table
        cursor.execute("PRAGMA table_info(reports)")
        columns = [row[1] for row in cursor.fetchall()]

        required_columns = ['legal_entity_owner_checkbox', 'acc_membership_checkbox', 'relationship']
        for col in required_columns:
            if col in columns:
                print(f"  ✅ Column 'reports.{col}' exists")
            else:
                print(f"  ❌ Column 'reports.{col}' MISSING")
                conn.close()
                return False

        # Check dropdown data
        cursor.execute("""
            SELECT config_category, COUNT(*)
            FROM system_config
            WHERE config_type = 'dropdown'
            GROUP BY config_category
        """)
        dropdown_counts = {row[0]: row[1] for row in cursor.fetchall()}

        required_categories = [
            'nationality',
            'report_source',
            'reporting_entity',
            'second_reason_for_suspicion',
            'type_of_suspected_transaction',
            'report_classification',
            'fiu_feedback'
        ]

        print(f"\n  Dropdown categories:")
        for category in required_categories:
            count = dropdown_counts.get(category, 0)
            if count > 0:
                print(f"    ✅ {category}: {count} values")
            else:
                print(f"    ❌ {category}: NO VALUES")

        conn.close()

        print(f"\n✅ Schema verification complete")
        return True

    except Exception as e:
        print(f"❌ Verification error: {str(e)}")
        return False


def run_basic_tests():
    """Run basic functionality tests."""
    try:
        print("\nRunning basic tests...")

        # Test 1: Report number service
        from database.db_manager import DatabaseManager
        from services.logging_service import LoggingService
        from services.report_number_service import ReportNumberService

        db = DatabaseManager(Config.DATABASE_PATH)
        logger = LoggingService(db)
        service = ReportNumberService(db, logger)

        # Test reservation
        success, reservation, message = service.reserve_next_numbers("test_deployment")

        if success:
            print(f"  ✅ Reservation system works: {reservation['report_number']}")
            # Clean up
            service.cancel_reservation(reservation['report_number'], "test_deployment")
        else:
            print(f"  ❌ Reservation system failed: {message}")
            return False

        # Test 2: Dropdown service
        from services.dropdown_service import DropdownService

        dropdown_service = DropdownService(db, logger)

        nationalities = dropdown_service.get_active_dropdown_values('nationality')
        if len(nationalities) > 0:
            print(f"  ✅ Dropdown service works: {len(nationalities)} nationalities loaded")
        else:
            print(f"  ❌ Dropdown service failed: No nationalities found")
            return False

        # Test 3: Restore service
        from services.restore_service import RestoreService

        restore_service = RestoreService(db, logger)
        stats = restore_service.get_restore_stats()
        print(f"  ✅ Restore service works: {stats['total_restores']} total restores")

        return True

    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main deployment function."""
    print_header("FIU REPORT SYSTEM - DEPLOYMENT SCRIPT")
    print("\nThis script will deploy all user test result requirements.")
    print("It will:")
    print("  1. Backup the current database")
    print("  2. Run database migrations")
    print("  3. Seed dropdown data (195+ countries, etc.)")
    print("  4. Verify the deployment")
    print("  5. Run basic functionality tests")

    # Load configuration
    print_step(0, "Loading Configuration")
    if not Config.load():
        print("❌ Configuration not loaded. Please run the application first to set up.")
        return False

    print(f"✅ Configuration loaded")
    print(f"   Database: {Config.DATABASE_PATH}")

    # Confirm deployment
    print("\n" + "!"*70)
    response = input("Continue with deployment? (yes/no): ").strip().lower()
    if response != 'yes':
        print("\n❌ Deployment cancelled by user")
        return False

    # Step 1: Backup
    print_step(1, "Backing Up Database")
    if not backup_database(Config.DATABASE_PATH):
        print("\n⚠️  Backup failed. Continue anyway? (yes/no): ")
        if input().strip().lower() != 'yes':
            return False

    # Step 2: Migrations
    print_step(2, "Running Database Migrations")
    if not run_migrations(Config.DATABASE_PATH):
        print("\n❌ Deployment failed at migration step")
        return False

    # Step 3: Seed Dropdowns
    print_step(3, "Seeding Dropdown Data")
    if not seed_dropdowns(Config.DATABASE_PATH):
        print("\n❌ Deployment failed at seeding step")
        return False

    # Step 4: Verify
    print_step(4, "Verifying Deployment")
    if not verify_schema(Config.DATABASE_PATH):
        print("\n❌ Deployment verification failed")
        return False

    # Step 5: Test
    print_step(5, "Running Basic Tests")
    if not run_basic_tests():
        print("\n❌ Deployment tests failed")
        return False

    # Success!
    print_header("DEPLOYMENT SUCCESSFUL!")
    print("\n✅ All steps completed successfully!")
    print("\nNext steps:")
    print("  1. Start the application: python main.py")
    print("  2. Test report creation with new fields")
    print("  3. Test concurrent access (open multiple dialogs)")
    print("  4. Review DEPLOYMENT_GUIDE.md for comprehensive testing")
    print("\nOptional:")
    print("  - Run test_concurrent_reservations.py for stress testing")
    print("  - Check system_logs table for any errors")

    print("\n" + "="*70)

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
