"""
Seed Dropdown Values Script
Populates system_config table with initial dropdown values for the FIU reporting system
"""
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger('fiu_system')


def seed_dropdown_values(db_path):
    """Seed initial dropdown values into system_config"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Starting dropdown values seeding...")
        logger.info("Starting dropdown values seeding")

        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM system_config WHERE config_type = 'dropdown'")
        existing_count = cursor.fetchone()[0]

        if existing_count > 0:
            print(f"⚠️  Found {existing_count} existing dropdown values.")
            response = input("Do you want to clear and re-seed? (yes/no): ")
            if response.lower() != 'yes':
                print("Seeding cancelled.")
                return False

            # Clear existing dropdown values
            cursor.execute("DELETE FROM system_config WHERE config_type = 'dropdown'")
            print("Cleared existing dropdown values")

        # Define dropdown values by category
        dropdown_data = {
            'status': [
                'Open',
                'Under Review',
                'Pending Information',
                'Approved',
                'Rejected',
                'Closed',
                'Escalated',
                'On Hold',
            ],
            'risk_level': [
                'Low',
                'Medium',
                'High',
                'Critical',
            ],
            'transaction_type': [
                'Wire Transfer',
                'Cash Deposit',
                'Cash Withdrawal',
                'Check Deposit',
                'ATM Transaction',
                'Online Transfer',
                'International Transfer',
                'Currency Exchange',
                'Money Order',
                'Other',
            ],
            'entity_type': [
                'Individual',
                'Corporation',
                'Partnership',
                'Trust',
                'Government Entity',
                'Non-Profit Organization',
                'Financial Institution',
                'Other',
            ],
            'report_type': [
                'Suspicious Activity',
                'Cash Transaction',
                'Wire Transfer',
                'Cross-Border',
                'High-Value Transaction',
                'Structuring',
                'Trade-Based Money Laundering',
                'Terrorist Financing',
                'Other',
            ],
            'investigation_status': [
                'Not Started',
                'In Progress',
                'Completed',
                'Referred to Law Enforcement',
                'No Action Required',
            ],
            'document_type': [
                'National ID',
                'Passport',
                'Driving License',
                'Commercial Registration',
                'Tax ID',
                'Bank Statement',
                'Contract',
                'Other',
            ],
            'currency': [
                'USD - US Dollar',
                'EUR - Euro',
                'GBP - British Pound',
                'SAR - Saudi Riyal',
                'AED - UAE Dirham',
                'KWD - Kuwaiti Dinar',
                'QAR - Qatari Riyal',
                'BHD - Bahraini Dinar',
                'OMR - Omani Rial',
                'JPY - Japanese Yen',
                'CNY - Chinese Yuan',
                'CHF - Swiss Franc',
            ],
            'country': [
                'United States',
                'United Kingdom',
                'Saudi Arabia',
                'United Arab Emirates',
                'Kuwait',
                'Qatar',
                'Bahrain',
                'Oman',
                'Egypt',
                'Jordan',
                'Lebanon',
                'Iraq',
                'Syria',
                'Yemen',
                'Other',
            ],
            'gender': [
                'Male',
                'Female',
                'Other',
                'Not Specified',
            ],
            'reporting_method': [
                'Paper',
                'Automated',
                'Electronic',
                'Manual Entry',
                'System Generated',
            ],
            'arb_staff': [
                'FIU Director',
                'Senior Analyst',
                'Compliance Officer',
                'Investigation Officer',
                'Risk Manager',
                'Legal Advisor',
                'Operations Manager',
                'Data Analyst',
                'Quality Assurance',
                'Admin Staff',
            ],
        }

        # Insert dropdown values
        insert_count = 0
        for category, values in dropdown_data.items():
            for order, value in enumerate(values, start=1):
                config_key = f"{category}_{value.lower().replace(' ', '_').replace('-', '_')}"
                cursor.execute("""
                    INSERT INTO system_config (config_key, config_value, config_type, config_category, display_order)
                    VALUES (?, ?, 'dropdown', ?, ?)
                """, (config_key, value, category, order))
                insert_count += 1

        conn.commit()
        conn.close()

        print(f"\n✅ Successfully seeded {insert_count} dropdown values across {len(dropdown_data)} categories!")
        print("\nCategories seeded:")
        for category, values in dropdown_data.items():
            print(f"  - {category.replace('_', ' ').title()}: {len(values)} values")

        logger.info(f"Seeded {insert_count} dropdown values")
        return True

    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        logger.error(f"Dropdown seeding error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)

    # Get database path from config
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    try:
        from config import Config

        if Config.load():
            print(f"Database path: {Config.DATABASE_PATH}")

            if Path(Config.DATABASE_PATH).is_file():
                seed_dropdown_values(Config.DATABASE_PATH)
            else:
                print("❌ Database file not found. Please run the application first to create the database.")
        else:
            print("❌ Configuration not found. Please run the application first to set up the system.")

    except Exception as e:
        print(f"❌ Error: {e}")
