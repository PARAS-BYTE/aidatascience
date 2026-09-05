from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def upgrade_sqlite_schema() -> None:
    """Apply additive compatibility upgrades for local SQLite installations.

    ``create_all`` only creates missing tables; it does not add columns to an
    existing database.  The desktop-friendly SQLite setup therefore needs these
    non-destructive additions when a user updates the application.
    """
    if engine.dialect.name != "sqlite":
        return

    additions = {
        "datasets": {"validation_schema": "TEXT"},
        "jobs": {
            "budget_seconds": "INTEGER",
            "elimination_log": "TEXT",
            "forecast_config": "TEXT",
        },
        "deployments": {
            "role": "VARCHAR(20) DEFAULT 'champion'",
            "traffic_pct": "FLOAT DEFAULT 1.0",
        },
    }
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table, columns in additions.items():
            if table not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table)}
            for column, definition in columns.items():
                if column not in existing_columns:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def get_db():
    """Dependency for obtaining database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
