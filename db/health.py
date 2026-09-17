from db.session import SessionLocal
from sqlalchemy import text


def check_db_connection() -> bool:
    try:
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        session.close()
        return True
    except Exception:
        return False