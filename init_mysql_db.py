#!/usr/bin/env python3
"""
Initialize MySQL database tables for QA Trainings.
This creates all the required tables based on the SQLAlchemy models.
"""

import os
import sys

# Set MySQL database URL
os.environ['DATABASE_URL'] = 'mysql+pymysql://qa_user:qa_password@localhost:3307/qa_trainings'

from flask import Flask
from models import db

def init_mysql_db(host='localhost', port='3307', user='qa_user', password='qa_password', database='qa_trainings'):
    """Initialize MySQL database tables."""

    # Create Flask app with MySQL configuration
    app = Flask(__name__)
    database_url = f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}'
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    print("\n" + "="*70)
    print("QA Trainings: MySQL Database Initialization")
    print("="*70 + "\n")

    print(f"Connecting to MySQL at {host}:{port}...")
    print(f"Database: {database}\n")

    try:
        with app.app_context():
            # Create all tables
            print("Creating tables...")
            db.create_all()
            print("✓ All tables created successfully!\n")

            # List created tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            print("Tables created:")
            for table in tables:
                row_count = db.session.execute(f"SELECT COUNT(*) FROM {table}").scalar()
                print(f"  ✓ {table} (0 rows, ready for migration)")

            print("\n" + "="*70)
            print("✓ Database initialization complete!")
            print("="*70)
            print("\nNext step: Run migration script")
            print("  python migrate_to_mysql.py --mysql-host localhost --mysql-port 3307")

            return True

    except Exception as e:
        print(f"✗ Error: {e}")
        print(f"\nTroubleshooting:")
        print(f"  - Check MySQL is running")
        print(f"  - Verify connection: {user}@{host}:{port}")
        print(f"  - Database '{database}' exists")
        return False

if __name__ == '__main__':
    success = init_mysql_db()
    sys.exit(0 if success else 1)
