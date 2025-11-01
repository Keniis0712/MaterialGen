from datetime import timedelta
import datetime
from typing import Optional

from fastapi import Cookie, Depends, HTTPException
from jose import jwt, JWTError
from passlib.context import CryptContext

from fastapi.security import OAuth2PasswordBearer

from config import *
from db.models import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# --------------------
# JWT
# --------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: Optional[str] = Cookie(None)):
    user = get_current_user_by_default(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def get_current_user_by_default(token: Optional[str] = Cookie(None)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if not username or not role or not role.isnumeric():
            return None
        return {"username": username, "role": int(role)}
    except JWTError:
        return None


def require_role(required_role: UserRole):
    def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user["role"]
        if user_role < required_role.value:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return role_checker
