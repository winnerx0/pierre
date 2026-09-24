from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.schema import Base

engine = create_engine("postgresql://postgres:postgres@localhost:5432/postgres")

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base.metadata.create_all(engine)


def get_db():

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
