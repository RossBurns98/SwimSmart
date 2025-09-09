from swimsmart.db import SessionLocal

def get_db():
    """
    FastAPI dependency, yields a database session as well as ensures that 
    the database is closed after request ends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()