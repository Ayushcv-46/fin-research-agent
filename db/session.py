# Database session management
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base

engine = create_engine("sqlite:///./data/app.db")
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)