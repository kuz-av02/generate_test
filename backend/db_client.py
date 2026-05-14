import os
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "test_generator")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id = Column(Integer, primary_key=True)
    request_id = Column(String(100), unique=True, nullable=False)
    topic = Column(String(500), nullable=False)
    num_questions = Column(Integer, nullable=False)
    quiz_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


def save_generation_log(request_id: str, topic: str, num_questions: int, quiz_text: str):
    session = SessionLocal()
    try:
        log = GenerationLog(
            request_id=request_id,
            topic=topic,
            num_questions=num_questions,
            quiz_text=quiz_text
        )
        session.add(log)
        session.commit()
    finally:
        session.close()