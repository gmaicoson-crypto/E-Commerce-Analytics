"""Simulator 服务的 DB 连接,共享 ecommerce-vue-ts 后端的 MySQL 库。"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://root:20041122@127.0.0.1:3306/ecommerce_db",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"charset": "utf8mb4"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
