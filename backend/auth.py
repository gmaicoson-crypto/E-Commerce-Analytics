from datetime import UTC, datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import settings

# 使用 pbkdf2_sha256 算法加密密码
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# 对明文密码进行哈希
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# 校验明文密码与哈希是否匹配
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# 生成 JWT 访问令牌
def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(hours=settings.access_token_expire_hours)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


# 解码并验证 JWT 令牌，失败返回 None
def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
