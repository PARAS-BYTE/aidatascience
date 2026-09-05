import sqlite3
import os

db_path = os.path.abspath("app.db")
print("Migrating DB at:", db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def add_column_if_not_exists(table, column, col_type):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        print(f"Adding {column} ({col_type}) to {table}...")
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            conn.commit()
            print(f"Added {column} successfully!")
        except Exception as e:
            print(f"Error adding {column}: {e}")
    else:
        print(f"{column} already in {table}")

# Datasets
add_column_if_not_exists("datasets", "validation_schema", "TEXT")

# Jobs
add_column_if_not_exists("jobs", "budget_seconds", "INTEGER")
add_column_if_not_exists("jobs", "elimination_log", "TEXT")
add_column_if_not_exists("jobs", "forecast_config", "TEXT")

# Deployments
add_column_if_not_exists("deployments", "role", "VARCHAR(20) DEFAULT 'champion'")
add_column_if_not_exists("deployments", "traffic_pct", "FLOAT DEFAULT 1.0")

# Verify
cursor.execute("PRAGMA table_info(datasets)")
print("Datasets columns:", [r[1] for r in cursor.fetchall()])

cursor.execute("PRAGMA table_info(jobs)")
print("Jobs columns:", [r[1] for r in cursor.fetchall()])

cursor.execute("PRAGMA table_info(deployments)")
print("Deployments columns:", [r[1] for r in cursor.fetchall()])

conn.close()
print("Migration finished!")
