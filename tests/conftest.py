# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from swimsmart.db import Base  # your Declarative Base


@pytest.fixture()
def db_session(tmp_path):
    # file-based sqlite so multiple connections see the same data
    db_file = tmp_path / "test_swimsmart.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_file}", future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
