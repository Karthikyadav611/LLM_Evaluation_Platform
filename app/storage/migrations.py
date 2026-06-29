from sqlalchemy import inspect, text

from app.storage.models import Base


def initialize_database(engine) -> None:
    Base.metadata.create_all(bind=engine)
    _add_missing_experiment_columns(engine)


def _add_missing_experiment_columns(engine) -> None:
    inspector = inspect(engine)
    if "experiments" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("experiments")}
    columns = {
        "generation_provider": "VARCHAR(64)",
        "generation_model": "VARCHAR(255)",
        "judge_provider": "VARCHAR(64)",
        "judge_model": "VARCHAR(255)",
        "report_directory": "TEXT",
    }
    with engine.begin() as connection:
        for name, sql_type in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE experiments ADD COLUMN {name} {sql_type}"))
