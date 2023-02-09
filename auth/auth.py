from passlib.context import CryptContext
from db import models
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID
import datetime
from typing import Optional
from jose import jwt, JWTError
from fastapi import Depends, Request
from fastapi.exceptions import HTTPException
from fastapi_jwt_auth import AuthJWT
from config import settings
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN

SECRET_KEY = "dk&sjn@#JDJand)?S>jNC!123SJFNF0-?"
ALGORITHM = "HS256"

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="token")




def get_password_hash(password):
    return bcrypt_context.hash(password)


def verify_password(plain_password, hashed_password):
    return bcrypt_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str, db):
    user = db.query(models.Users).filter(
        models.Users.username == username).first()
    
    if not user:
        return False
    if not verify_password(password, user.password):
        return False

    return user


def create_access_token(username: str, user_id: UUID, is_superuser: bool, expires_delta: Optional[datetime.timedelta] = None):
    encode = {'username': username, 'id': user_id,
              'is_superuser': is_superuser}
    if expires_delta:
        expire = datetime.datetime.now() + expires_delta
    else:
        expire = datetime.datetime.now() + datetime.timedelta(minutes=15)

    encode.update({"exp": expire})

    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(username: str, user_id: UUID, is_superuser: bool, expires_delta: Optional[datetime.timedelta] = None):
    encode = {'username': username, 'id': user_id,
              'is_superuser': is_superuser}
    if expires_delta:
        expire = datetime.datetime.now() + expires_delta
    else:
        expire = datetime.datetime.now() + datetime.timedelta(minutes=15)

    encode.update({"exp": expire})

    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_bearer)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('username')
        user_id: UUID = payload.get("id")
        is_superuser: bool = payload.get('is_superuser')
        if username is None or user_id is None:
            raise HTTPException(status_code=404, detail="User not found")
        return {'username': username, 'id': user_id, 'is_superuser': is_superuser}

    except JWTError:
        raise HTTPException(status_code=404, detail="User not found")
