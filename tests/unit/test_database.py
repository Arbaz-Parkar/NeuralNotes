"""Tests for SQLAlchemy database connection helpers."""

from sqlalchemy import text

from neuralnotes.database import (
    check_database_connection,
    create_database_engine,
    create_database_session_factory,
)
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


def test_database_session_factory_provides_transactional_sessions() -> None:
    engine = create_database_engine(
        Settings(database_url="sqlite+pysqlite:///:memory:")
    )
    session_factory = create_database_session_factory(engine)

    try:
        with session_factory.begin() as session:
            assert session.scalar(text("SELECT 1")) == 1
    finally:
        engine.dispose()
