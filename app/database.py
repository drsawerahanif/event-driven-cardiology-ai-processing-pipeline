from sqlalchemy import create_engine, Column, Integer, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./prompts.db"

engine = create_engine(
    DATABASE_URL,
    connect_args = {"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine,
                            autoflush=False,
                            autocommit=False)

Base = declarative_base()

class Prompt(Base):
    __tablename__ = "prompts"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    

def init_db():
    Base.metadata.create_all(bind=engine)
