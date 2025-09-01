from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

# Tell SQLAlchemy to use SQLite, also to keep file locally and call it swimsmart.db
# splite:/// the triple slash means relative to current wkdir
DATABASE_URL = "sqlite:///swimsmart.db"

# Create engine app uses to talk to DB, future = True enables SQLAlchemy 2.0 style 
engine = create_engine(DATABASE_URL, future=True)

#Defining Base class for models to inherit
class Base(DeclarativeBase):
    """Base Class for ORM models"""
    pass

#Builds a factory which creates new DB sessions on Demand
SessionLocal = sessionmaker(bind=engine, autoflush= False, expire_on_commit= False)

# Calls SQLAlchemy to make tables declared by models
def init_db() -> None:
    """Create all tables based on Base metadata"""
    from . import models
    Base.metadata.create_all(engine)

@contextmanager
def get_db() -> Session:
    """Open a DB session for use inside a with block.
    Session closes automatically when block ends."""
    db = SessionLocal() # Open a session
    try:
        yield db # Give session to user
    finally:
        db.close() # ensure session is closed when done