"""
Database Migration Script
Adds new columns for:
- Issue 5: id_type (ID or CR)
- Issue 6: account_type (Account or Membership)
- Issue 12: theme_preference (light or dark)
- Issue 13: org_username (organization username for login)
"""
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger('fiu_system')


def migrate_database(db_path):
    """Run database migrations to add new columns"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Starting database migration...")
        logger.info("Starting database migration")

        # Check which columns need to be added
        migrations = []

        # Check reports table for id_type
        cursor.execute("PRAGMA table_info(reports)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'id_type' not in columns:
            migrations.append({
                'name': 'Add id_type to reports',
                'sql': "ALTER TABLE reports ADD COLUMN id_type TEXT DEFAULT 'ID' CHECK(id_type IN ('ID', 'CR'))"
            })

        if 'account_type' not in columns:
            migrations.append({
                'name': 'Add account_type to reports',
                'sql': "ALTER TABLE reports ADD COLUMN account_type TEXT DEFAULT 'Account' CHECK(account_type IN ('Account', 'Membership'))"
            })

        # Check users table for new columns
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]

        if 'org_username' not in user_columns:
            migrations.append({
                'name': 'Add org_username to users',
                'sql': "ALTER TABLE users ADD COLUMN org_username TEXT"
            })

        if 'theme_preference' not in user_columns:
            migrations.append({
                'name': 'Add theme_preference to users',
                'sql': "ALTER TABLE users ADD COLUMN theme_preference TEXT DEFAULT 'light' CHECK(theme_preference IN ('light', 'dark'))"
            })

        # Run migrations
        if not migrations:
            print("✅ Database is already up to date. No migrations needed.")
            logger.info("No migrations needed")

            # Check if we need to create unique index on org_username
            needs_index = False
            try:
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_users_org_username'")
                if not cursor.fetchone():
                    needs_index = True
            except:
                needs_index = False

            if needs_index and 'org_username' in user_columns:
                print("Creating unique index on org_username...")
                try:
                    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_org_username ON users(org_username) WHERE org_username IS NOT NULL")
                    conn.commit()
                    print("✅ Unique index created successfully!")
                except Exception as e:
                    print(f"Warning: Could not create unique index: {e}")

            conn.close()
            return True

        print(f"\nFound {len(migrations)} migration(s) to apply:")
        for i, migration in enumerate(migrations, 1):
            print(f"  {i}. {migration['name']}")

        print("\nApplying migrations...")

        for migration in migrations:
            try:
                print(f"  ✓ {migration['name']}...", end=' ')
                cursor.execute(migration['sql'])
                conn.commit()
                print("Done")
                logger.info(f"Migration applied: {migration['name']}")
            except Exception as e:
                print(f"Failed: {e}")
                logger.error(f"Migration failed: {migration['name']} - {e}")
                conn.rollback()
                return False

        # Create unique index on org_username if we just added the column
        if any(m['name'] == 'Add org_username to users' for m in migrations):
            print("\nCreating unique index on org_username...")
            try:
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_org_username ON users(org_username) WHERE org_username IS NOT NULL")
                conn.commit()
                print("  ✓ Unique index created")
                logger.info("Created unique index on org_username")
            except Exception as e:
                print(f"  ⚠ Warning: Could not create unique index: {e}")
                logger.warning(f"Could not create unique index: {e}")

        conn.close()
        print("\n✅ All migrations applied successfully!")
        logger.info("All migrations applied successfully")
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        logger.error(f"Migration error: {e}")
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
                migrate_database(Config.DATABASE_PATH)
            else:
                print("❌ Database file not found. Please run the application first to create the database.")
        else:
            print("❌ Configuration not found. Please run the application first to set up the system.")

    except Exception as e:
        print(f"❌ Error: {e}")
