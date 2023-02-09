from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:1234@localhost:5432/fastapi"

engine = create_engine(DATABASE_URL)
session = Session(bind=engine)
Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



    

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(e)