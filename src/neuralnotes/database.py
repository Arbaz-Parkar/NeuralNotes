"""SQLAlchemy engine creation and a small database connectivity check."""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from neuralnotes.settings import Settings


def create_database_engine(settings: Settings | None = None) -> Engine:
    """Create an engine from settings without opening a connection yet."""
    configuration = settings or Settings()
    return create_engine(configuration.database_url, pool_pre_ping=True)


def check_database_connection(engine: Engine) -> None:
    """Run a minimal query and raise the driver's error if the DB is unavailable."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
