from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from users import verify_password, get_user_by_username
from database import SessionLocal
import time
SECRET_KEY = ""
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600

def authenticate_user(db: Session, username: str, password: str) -> bool:
    user_data = get_user_by_username(db, username)
    if not user_data:
        return False
    if not verify_password(password, user_data.hashed_password):
        return False
    return True

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = int(time.time()) + ACCESS_TOKEN_EXPIRE_SECONDS
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except jwt.PyJWTError:
        return None