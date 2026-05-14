import os
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import bcrypt

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "test_generator")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# Модели БД
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Generation(Base):
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String(500), nullable=False)
    num_questions = Column(Integer, nullable=False)
    quiz_text = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    parent_id = Column(Integer, ForeignKey("generations.id"), nullable=True)
    model_used = Column(String(100), default="local")
    generation_time = Column(Integer, nullable=True)
    prompt_length = Column(Integer, nullable=True)
    response_length = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)


def get_db_session():
    return SessionLocal()


def create_user(username: str, email: str, password: str):
    session = SessionLocal()
    try:
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = User(username=username, email=email, password_hash=password_hash)
        session.add(user)
        session.commit()
        return user.id
    finally:
        session.close()


def authenticate_user(username: str, password: str):
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == username).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return user
        return None
    finally:
        session.close()


def get_user_by_username(username: str):
    session = SessionLocal()
    try:
        return session.query(User).filter(User.username == username).first()
    finally:
        session.close()


def save_generation(
    session,
    user_id: int,
    topic: str,
    num_questions: int,
    quiz_text: str,
    parent_id: int = None,
    model_used: str = "local",
    generation_time: float = None,
    prompt_length: int = None,
    response_length: int = None
):
    if parent_id is None:
        generation = Generation(
            user_id=user_id,
            topic=topic,
            num_questions=num_questions,
            quiz_text=quiz_text,
            parent_id=None,
            version=1,
            model_used=model_used,
            generation_time=generation_time,
            prompt_length=prompt_length,
            response_length=response_length
        )
        session.add(generation)
        session.commit()
        return generation.id
    else:
        parent_gen = session.query(Generation).filter(Generation.id == parent_id).first()
        if not parent_gen:
            raise ValueError(f"Родительская версия с id={parent_id} не найдена")

        # Находим корневую версию (где parent_id IS NULL)
        root_id = parent_gen.parent_id if parent_gen.parent_id else parent_gen.id

        # Считаем количество существующих версий в этой цепочке
        existing_versions = session.query(Generation).filter(
            (Generation.id == root_id) | (Generation.parent_id == root_id)
        ).count()

        new_version = existing_versions + 1

        generation = Generation(
            user_id=user_id,
            topic=topic,
            num_questions=num_questions,
            quiz_text=quiz_text,
            parent_id=parent_id,
            version=new_version,
            model_used=model_used,
            generation_time=generation_time,
            prompt_length=prompt_length,
            response_length=response_length
        )
        session.add(generation)
        session.commit()
        return generation.id

    # if parent_id:
    #     last_version = session.query(Generation).filter(Generation.parent_id == parent_id).count()
    #     generation.version = last_version + 2
    # else:
    #     generation.version = 1
    #
    # session.add(generation)
    # session.commit()
    # return generation_time.id


def get_user_generations(user_id: int, limit: int = 50):
    session = SessionLocal()
    try:
        return session.query(Generation).filter(
            Generation.user_id == user_id
        ).order_by(Generation.created_at.desc()).limit(limit).all()
    finally:
        session.close()


def get_generation_by_id(gen_id: int):
    session = SessionLocal()
    try:
        return session.query(Generation).filter(Generation.id == gen_id).first()
    finally:
        session.close()


def get_all_versions(gen_id: int):
    session = SessionLocal()
    try:
        gen = session.query(Generation).filter(Generation.id == gen_id).first()
        if not gen:
            return []

        # Находим корневой ID (первая версия)
        root_id = gen.parent_id if gen.parent_id else gen.id

        # Получаем все версии, сортируем по возрастанию версии
        versions = session.query(Generation).filter(
            (Generation.id == root_id) | (Generation.parent_id == root_id)
        ).order_by(Generation.version.asc()).all()

        return versions
    finally:
        session.close()