"""Tests for SQLAlchemy database connection helpers."""

from sqlalchemy import text

from neuralnotes.database import check_database_connection, create_database_engine
from neuralnotes.settings import Settings


def test_database_connection_helper_runs_select_one() -> None:
    engine = create_database_engine(
        Settings(database_url="sqlite+pysqlite:///:memory:")
    )

    try:
        check_database_connection(engine)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
    finally:
        engine.dispose()
