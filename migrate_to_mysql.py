#!/usr/bin/env python3
"""
Migration script to copy data from SQLite to MySQL database.
Reads from SQLite and transfers all data to MySQL.

Usage:
    python migrate_to_mysql.py [--mysql-host HOST] [--mysql-user USER] [--mysql-password PASSWORD]

Example with defaults (localhost):
    python migrate_to_mysql.py

Example with Docker:
    python migrate_to_mysql.py --mysql-host mysql --mysql-user qa_user --mysql-password qa_password
"""

import os
import sqlite3
import sys
import argparse
from contextlib import contextmanager

try:
    import pymysql
except ImportError:
    print("Error: pymysql not installed. Install with: pip install pymysql")
    sys.exit(1)

# Paths
SQLITE_DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'trainings.db')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Migrate SQLite database to MySQL')
    parser.add_argument('--mysql-host', default='localhost', help='MySQL host (default: localhost)')
    parser.add_argument('--mysql-port', type=int, default=3306, help='MySQL port (default: 3306)')
    parser.add_argument('--mysql-user', default='qa_user', help='MySQL user (default: qa_user)')
    parser.add_argument('--mysql-password', default='qa_password', help='MySQL password (default: qa_password)')
    parser.add_argument('--mysql-db', default='qa_trainings', help='MySQL database (default: qa_trainings)')
    return parser.parse_args()

@contextmanager
def sqlite_connection(db_path):
    """Context manager for SQLite connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def mysql_connection(host, port, user, password, database):
    """Context manager for MySQL connection."""
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset='utf8mb4',
        autocommit=False
    )
    try:
        yield conn
    finally:
        conn.close()

def table_exists_in_mysql(cursor, table_name):
    """Check if table exists in MySQL."""
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
    """, (table_name,))
    return cursor.fetchone()[0] > 0

def copy_table(sqlite_conn, mysql_conn, table_name):
    """Copy a table from SQLite to MySQL."""
    sqlite_cursor = sqlite_conn.cursor()
    mysql_cursor = mysql_conn.cursor()

    # Get row count from SQLite
    sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = sqlite_cursor.fetchone()[0]

    if count == 0:
        print(f"  {table_name}: 0 records (skipped)")
        return 0

    try:
        # Get column names from SQLite
        sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in sqlite_cursor.fetchall()]

        # Fetch all data from SQLite
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()

        if rows:
            # Prepare insert statement with backticks for reserved keywords
            # Escape column names that might be reserved keywords
            escaped_columns = [f'`{col}`' if col == 'order' else col for col in columns]
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(escaped_columns)
            insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"

            # Insert rows in batches
            batch_size = 1000
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                # Convert Row objects to tuples
                data = [tuple(row) for row in batch]
                mysql_cursor.executemany(insert_sql, data)

            mysql_conn.commit()

        print(f"  ✓ {table_name}: {count} records migrated")
        return count

    except Exception as e:
        mysql_conn.rollback()
        print(f"  ✗ {table_name}: Error - {e}")
        return 0

def migrate():
    """Main migration function."""
    args = parse_args()

    print("\n" + "="*70)
    print("QA Trainings: SQLite to MySQL Migration")
    print("="*70 + "\n")

    # Check SQLite database exists
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"✗ Error: SQLite database not found at {SQLITE_DB_PATH}")
        return False

    print(f"✓ SQLite database found: {SQLITE_DB_PATH}\n")

    # Connect to MySQL
    print(f"Connecting to MySQL at {args.mysql_host}:{args.mysql_port}...")
    try:
        mysql_conn = pymysql.connect(
            host=args.mysql_host,
            port=args.mysql_port,
            user=args.mysql_user,
            password=args.mysql_password,
            database=args.mysql_db,
            charset='utf8mb4'
        )
        print(f"✓ Connected to MySQL database '{args.mysql_db}'\n")
    except Exception as e:
        print(f"✗ Failed to connect to MySQL: {e}")
        print(f"\nTroubleshooting:")
        print(f"  - Check MySQL is running")
        print(f"  - Verify credentials: {args.mysql_user}@{args.mysql_host}:{args.mysql_port}")
        print(f"  - Database '{args.mysql_db}' must exist")
        print(f"\nIf using Docker, start with: docker-compose up -d")
        return False

    # Tables to migrate (in dependency order - parent tables first)
    tables = [
        'training',
        'student',
        'instructor',
        'topic',
        'knowledge_skill',
        'attendance',
        'progress',
        'knowledge_assessment',
        'certificate',
        'training_instructors'
    ]

    print("Migrating data from SQLite to MySQL...\n")

    total_records = 0
    mysql_cursor = mysql_conn.cursor()

    try:
        # Disable foreign key checks for migration
        mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        mysql_conn.commit()

        with sqlite_connection(SQLITE_DB_PATH) as sqlite_conn:
            for table_name in tables:
                records = copy_table(sqlite_conn, mysql_conn, table_name)
                total_records += records

        # Re-enable foreign key checks
        mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        mysql_conn.commit()

    finally:
        mysql_cursor.close()
        mysql_conn.close()

    # Verify migration
    print("\nVerifying migration...")
    try:
        mysql_conn = pymysql.connect(
            host=args.mysql_host,
            port=args.mysql_port,
            user=args.mysql_user,
            password=args.mysql_password,
            database=args.mysql_db,
            charset='utf8mb4'
        )
        mysql_cursor = mysql_conn.cursor()

        with sqlite_connection(SQLITE_DB_PATH) as sqlite_conn:
            all_good = True
            for table_name in tables:
                # SQLite count
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                sqlite_count = sqlite_cursor.fetchone()[0]

                # MySQL count
                mysql_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                mysql_count = mysql_cursor.fetchone()[0]

                if sqlite_count == mysql_count:
                    if sqlite_count > 0:
                        print(f"  ✓ {table_name}: {mysql_count} records verified")
                else:
                    print(f"  ✗ {table_name}: Mismatch! SQLite={sqlite_count}, MySQL={mysql_count}")
                    all_good = False

        if all_good:
            print("\n" + "="*70)
            print("✓ Migration completed successfully!")
            print("="*70)
            print(f"\nDatabase Configuration:")
            print(f"  Host: {args.mysql_host}:{args.mysql_port}")
            print(f"  Database: {args.mysql_db}")
            print(f"  User: {args.mysql_user}")
            print(f"  Total records migrated: {total_records}")
            print(f"\nYour app is configured to use MySQL via DATABASE_URL environment variable.")
            print(f"\nTo start with Docker: docker-compose up -d")
        else:
            print("\n⚠ Migration completed with warnings - please verify data!")

        mysql_cursor.close()
        mysql_conn.close()

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False

    return True

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
