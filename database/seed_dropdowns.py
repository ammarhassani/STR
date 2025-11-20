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
            # Note: 'status' field is being removed per requirements, kept for backward compatibility
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
            # NEW: Comprehensive nationality list (~195 countries)
            'nationality': [
                'Afghan', 'Albanian', 'Algerian', 'American', 'Andorran', 'Angolan', 'Antiguan', 'Argentine',
                'Armenian', 'Australian', 'Austrian', 'Azerbaijani', 'Bahamian', 'Bahraini', 'Bangladeshi',
                'Barbadian', 'Belarusian', 'Belgian', 'Belizean', 'Beninese', 'Bhutanese', 'Bolivian',
                'Bosnian', 'Botswanan', 'Brazilian', 'British', 'Bruneian', 'Bulgarian', 'Burkinabe',
                'Burmese', 'Burundian', 'Cambodian', 'Cameroonian', 'Canadian', 'Cape Verdean',
                'Central African', 'Chadian', 'Chilean', 'Chinese', 'Colombian', 'Comoran', 'Congolese',
                'Costa Rican', 'Croatian', 'Cuban', 'Cypriot', 'Czech', 'Danish', 'Djiboutian', 'Dominican',
                'Dutch', 'East Timorese', 'Ecuadorean', 'Egyptian', 'Emirati', 'English', 'Equatorial Guinean',
                'Eritrean', 'Estonian', 'Ethiopian', 'Fijian', 'Filipino', 'Finnish', 'French', 'Gabonese',
                'Gambian', 'Georgian', 'German', 'Ghanaian', 'Greek', 'Grenadian', 'Guatemalan', 'Guinean',
                'Guinea-Bissauan', 'Guyanese', 'Haitian', 'Honduran', 'Hungarian', 'Icelandic', 'Indian',
                'Indonesian', 'Iranian', 'Iraqi', 'Irish', 'Israeli', 'Italian', 'Ivorian', 'Jamaican',
                'Japanese', 'Jordanian', 'Kazakh', 'Kenyan', 'Kittitian', 'Kuwaiti', 'Kyrgyz', 'Laotian',
                'Latvian', 'Lebanese', 'Liberian', 'Libyan', 'Liechtensteiner', 'Lithuanian', 'Luxembourgish',
                'Macedonian', 'Malagasy', 'Malawian', 'Malaysian', 'Maldivian', 'Malian', 'Maltese',
                'Marshallese', 'Mauritanian', 'Mauritian', 'Mexican', 'Micronesian', 'Moldovan', 'Monacan',
                'Mongolian', 'Montenegrin', 'Moroccan', 'Mozambican', 'Namibian', 'Nauruan', 'Nepalese',
                'New Zealander', 'Nicaraguan', 'Nigerian', 'Nigerien', 'North Korean', 'Norwegian', 'Omani',
                'Pakistani', 'Palauan', 'Palestinian', 'Panamanian', 'Papua New Guinean', 'Paraguayan',
                'Peruvian', 'Polish', 'Portuguese', 'Qatari', 'Romanian', 'Russian', 'Rwandan',
                'Saint Lucian', 'Salvadoran', 'Samoan', 'San Marinese', 'Sao Tomean', 'Saudi', 'Scottish',
                'Senegalese', 'Serbian', 'Seychellois', 'Sierra Leonean', 'Singaporean', 'Slovak', 'Slovenian',
                'Solomon Islander', 'Somali', 'South African', 'South Korean', 'South Sudanese', 'Spanish',
                'Sri Lankan', 'Sudanese', 'Surinamese', 'Swazi', 'Swedish', 'Swiss', 'Syrian', 'Taiwanese',
                'Tajik', 'Tanzanian', 'Thai', 'Togolese', 'Tongan', 'Trinidadian', 'Tunisian', 'Turkish',
                'Turkmen', 'Tuvaluan', 'Ugandan', 'Ukrainian', 'Uruguayan', 'Uzbek', 'Vanuatuan',
                'Venezuelan', 'Vietnamese', 'Welsh', 'Yemeni', 'Zambian', 'Zimbabwean',
            ],
            # NEW: Report Source (Requirement #12)
            'report_source': [
                'SAS',
                'Branch',
            ],
            # NEW: Reporting Entity (Requirement #13)
            'reporting_entity': [
                'SAS',
                'BRANCH',
                'Internal Whistleblower',
            ],
            # NEW: Second Reason for Suspicion (Requirement #7 - Admin manageable)
            'second_reason_for_suspicion': [
                'Unusual transaction patterns',
                'Structuring to avoid reporting thresholds',
                'Transactions inconsistent with customer profile',
                'Rapid movement of funds',
                'Use of multiple accounts',
                'Complex transaction structures',
                'Suspicious use of third parties',
                'Transactions with high-risk jurisdictions',
                'Lack of economic rationale',
                'Other suspicious indicators',
            ],
            # NEW: Type of Suspected Transaction (Requirement #8 - Admin manageable)
            'type_of_suspected_transaction': [
                'Money Laundering',
                'Terrorist Financing',
                'Fraud',
                'Corruption/Bribery',
                'Tax Evasion',
                'Sanctions Violation',
                'Human Trafficking',
                'Drug Trafficking',
                'Arms Trafficking',
                'Cyber Crime',
                'Identity Theft',
                'Trade-Based Money Laundering',
                'Structuring/Smurfing',
                'Wire Transfer Fraud',
                'Check Fraud',
                'Credit Card Fraud',
                'Other Financial Crime',
            ],
            # NEW: Report Classification (Requirement #11 - Admin manageable)
            'report_classification': [
                'High Priority',
                'Medium Priority',
                'Low Priority',
                'Urgent',
                'Routine',
                'Follow-up Required',
                'Investigation Pending',
                'Closed - No Action',
                'Closed - Referred',
                'Archived',
            ],
            # NEW: FIU Feedback (Requirement #18 - Admin manageable)
            'fiu_feedback': [
                'Under Review',
                'Additional Information Required',
                'Investigation Opened',
                'Referred to Law Enforcement',
                'No Further Action',
                'Case Closed',
                'Merged with Existing Case',
                'Pending External Response',
                'Quality Review Required',
                'Archived',
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
