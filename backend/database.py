from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


# 从环境变量或 .env 文件读取配置
class Settings(BaseSettings):
    database_url: str = Field(
        default="mysql+pymysql://root:password@localhost:3306/ecommerce_db",
        alias="DATABASE_URL",
    )
    secret_key: str = Field(default="your-secret-key", alias="SECRET_KEY")
    access_token_expire_hours: int = Field(
        default=24, alias="ACCESS_TOKEN_EXPIRE_HOURS"
    )
    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com", alias="DEEPSEEK_BASE_URL"
    )
    debug: bool = Field(default=False, alias="DEBUG")
    # SMTP 邮件配置（管理员注册验证码）
    smtp_host: Optional[str] = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=465, alias="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, alias="SMTP_USER")
    smtp_pass: Optional[str] = Field(default=None, alias="SMTP_PASS")
    smtp_from: Optional[str] = Field(default=None, alias="SMTP_FROM")
    simulator_api_token: Optional[str] = Field(
        default=None, alias="SIMULATOR_API_TOKEN"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        populate_by_name = True


settings = Settings()

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False,
    connect_args={"charset": "utf8mb4"},
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 基类
Base = declarative_base()


# FastAPI 依赖注入用的数据库会话生成器
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
