from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config.settings import BACKEND_ROOT, env_value

_configured_database_url = env_value("DATABASE_URL", "")
if _configured_database_url:
    DATABASE_URL = _configured_database_url
    DATABASE_PATH = Path(DATABASE_URL.removeprefix("sqlite:///")) if DATABASE_URL.startswith("sqlite:///") else None
    if DATABASE_PATH is not None and not DATABASE_PATH.is_absolute():
        DATABASE_PATH = (BACKEND_ROOT / DATABASE_PATH).resolve()
        DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"
else:
    DATABASE_PATH = BACKEND_ROOT / "ecommerce.db"
    DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

if DATABASE_PATH is not None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 10} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
