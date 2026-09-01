from pathlib import Path

from sqlalchemy import Engine, create_engine, event

from agent_reliability_lab.storage.schema import metadata

DEFAULT_DATABASE_PATH = Path("data/northstar.db")


def create_database_engine(
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> Engine:
    """Create a SQLite engine for the Northstar database."""
    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def initialise_database(engine: Engine) -> None:
    """Create all Northstar database tables."""
    metadata.create_all(engine)


def reset_database(engine: Engine) -> None:
    """Drop and recreate all Northstar database tables."""
    metadata.drop_all(engine)
    metadata.create_all(engine)
