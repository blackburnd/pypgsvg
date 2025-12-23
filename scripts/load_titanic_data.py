#!/usr/bin/env python3
"""
Script to load Titanic passenger data from CSV into PostgreSQL database.
"""

import csv
import psycopg2
from psycopg2 import sql
import sys
from pathlib import Path


def create_table(cursor):
    """Create the titanic_passengers table if it doesn't exist."""
    create_table_query = """
    DROP TABLE IF EXISTS titanic_passengers CASCADE;

    CREATE TABLE titanic_passengers (
        passenger_id INTEGER PRIMARY KEY,
        survived INTEGER NOT NULL,
        pclass INTEGER NOT NULL,
        name TEXT NOT NULL,
        sex VARCHAR(10),
        age NUMERIC(5, 2),
        sibsp INTEGER,
        parch INTEGER,
        ticket VARCHAR(50),
        fare NUMERIC(10, 4),
        cabin VARCHAR(50),
        embarked CHAR(1)
    );

    CREATE INDEX idx_survived ON titanic_passengers(survived);
    CREATE INDEX idx_pclass ON titanic_passengers(pclass);
    CREATE INDEX idx_sex ON titanic_passengers(sex);
    CREATE INDEX idx_embarked ON titanic_passengers(embarked);
    """
    cursor.execute(create_table_query)
    print("✓ Table created successfully")


def load_data(cursor, csv_path):
    """Load data from CSV file into the database."""
    insert_query = """
    INSERT INTO titanic_passengers (
        passenger_id, survived, pclass, name, sex, age,
        sibsp, parch, ticket, fare, cabin, embarked
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """

    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        row_count = 0

        for row in reader:
            # Convert empty strings to None for NULL values
            values = (
                int(row['PassengerId']),
                int(row['Survived']),
                int(row['Pclass']),
                row['Name'],
                row['Sex'] or None,
                float(row['Age']) if row['Age'] else None,
                int(row['SibSp']) if row['SibSp'] else None,
                int(row['Parch']) if row['Parch'] else None,
                row['Ticket'] or None,
                float(row['Fare']) if row['Fare'] else None,
                row['Cabin'] or None,
                row['Embarked'] or None
            )

            cursor.execute(insert_query, values)
            row_count += 1

            if row_count % 100 == 0:
                print(f"  Loaded {row_count} rows...", end='\r')

    print(f"✓ Loaded {row_count} rows successfully")
    return row_count


def verify_data(cursor):
    """Verify the loaded data with some basic statistics."""
    queries = [
        ("Total passengers", "SELECT COUNT(*) FROM titanic_passengers"),
        ("Survivors", "SELECT COUNT(*) FROM titanic_passengers WHERE survived = 1"),
        ("Non-survivors", "SELECT COUNT(*) FROM titanic_passengers WHERE survived = 0"),
        ("Male passengers", "SELECT COUNT(*) FROM titanic_passengers WHERE sex = 'male'"),
        ("Female passengers", "SELECT COUNT(*) FROM titanic_passengers WHERE sex = 'female'"),
        ("First class", "SELECT COUNT(*) FROM titanic_passengers WHERE pclass = 1"),
        ("Second class", "SELECT COUNT(*) FROM titanic_passengers WHERE pclass = 2"),
        ("Third class", "SELECT COUNT(*) FROM titanic_passengers WHERE pclass = 3"),
    ]

    print("\nData verification:")
    print("-" * 40)
    for label, query in queries:
        cursor.execute(query)
        count = cursor.fetchone()[0]
        print(f"  {label:20s}: {count:4d}")


def main():
    # Configuration
    db_config = {
        'dbname': 'titanic',
        'user': 'danielblackburn',
        'host': 'localhost',
        'port': '5432'
    }

    # Determine CSV path relative to script location
    script_dir = Path(__file__).parent.parent
    csv_path = script_dir / 'docs' / 'titanic.csv'

    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        sys.exit(1)

    print(f"Loading Titanic data from: {csv_path}")
    print(f"Database: {db_config['dbname']} on {db_config['host']}:{db_config['port']}")
    print("-" * 60)

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**db_config)
        conn.autocommit = False
        cursor = conn.cursor()

        # Create table
        print("\n1. Creating table...")
        create_table(cursor)

        # Load data
        print("\n2. Loading data...")
        row_count = load_data(cursor, csv_path)

        # Commit the transaction
        conn.commit()
        print("\n✓ Transaction committed")

        # Verify data
        print("\n3. Verifying data...")
        verify_data(cursor)

        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("✓ Data load completed successfully!")
        print("=" * 60)

    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)


if __name__ == '__main__':
    main()
