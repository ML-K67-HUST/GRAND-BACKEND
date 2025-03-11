# from fastapi import APIRouter, Query
# from authlib.integrations.starlette_client import OAuth
# from starlette.config import Config
# from fastapi.responses import JSONResponse
# from datetime import datetime, timedelta
# from fastapi import HTTPException, status, Request, Cookie
# from authlib.integrations.starlette_client import OAuth
# from starlette.config import Config
# from starlette.responses import RedirectResponse
# from fastapi.responses import JSONResponse
# from jose import JWTError, jwt, ExpiredSignatureError, JWTError
# import traceback
# import requests
# import uuid
# import os
# from dotenv import load_dotenv
# from pydantic import ValidationError
# from typing import Optional
# from google.oauth2 import service_account
# import google.auth.transport.requests
# from google.oauth2.id_token import verify_oauth2_token
# import logging as logger
# from config import settings
# from database.postgresdb import PostgresDB
# load_dotenv(override=True)

# router = APIRouter()

# # Load configurations
# config = Config(".env")

# # Setup OAuth2
# oauth = OAuth()

# oauth.register(
#     name="auth_demo",
#     client_id=settings.google_client_id,
#     client_secret=settings.google_client_secret,
#     authorize_url="https://accounts.google.com/o/oauth2/auth",
#     authorize_params=None,
#     access_token_url="https://accounts.google.com/o/oauth2/token",
#     access_token_params=None,
#     refresh_token_url=None,
#     authorize_state=settings.secret_key,
#     redirect_uri=settings.redirect_url,
#     jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
#     client_kwargs={"scope": "openid profile email"},
# )


# # Secret key used to encode JWT tokens (should be kept secret)
# SECRET_KEY = settings.jwt_secret_key
# ALGORITHM = "HS256"
# REDIRECT_URL = settings.redirect_url
# FRONTEND_URL = settings.frontend_url


# def create_access_token(data: dict, expires_delta: timedelta = None):
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.utcnow() + expires_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=30)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt


# def get_current_user(token: str = Cookie(None)):
#     if not token:
#         raise HTTPException(status_code=401, detail="Not authenticated")

#     credentials_exception = HTTPException(
#         status_code=401,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )

#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id: str = payload.get("sub")
#         user_email: str = payload.get("email")
#         user_name: str = payload.get("name")

#         if user_id is None or user_email is None:
#             raise credentials_exception

#         with PostgresDB() as db:
#             user = db.select("users", {"userid": user_id, "email": user_email})

#             if not user:
#                 # 🔥 **User chưa có -> tạo mới**
#                 user_id = db.insert(
#                     "users", 
#                     {
#                         "userid": user_id,
#                         "username": user_name, 
#                         "email": user_email, 
#                         "password": "google-authen", 
#                         "full_name": user_name
#                     },
#                     returning="userid"
#                 )["userid"]

#         return {"user_id": user_id, "user_email": user_email}

#     except ExpiredSignatureError:
#         traceback.print_exc()
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please login again.")
#     except JWTError:
#         traceback.print_exc()
#         raise credentials_exception
#     except Exception as e:
#         traceback.print_exc()
#         raise HTTPException(status_code=401, detail="Not Authenticated")


# def log_user(user_id, user_email, user_name, user_pic, first_logged_in, last_accessed):
#     """Ghi log thông tin user, tạo mới nếu chưa có."""
#     try:
#         with PostgresDB() as db:
#             # Check nếu user đã tồn tại
#             existing_user = db.select("users", {"email_id": user_email}, columns=["COUNT(*)"])
            
#             if existing_user[0]["count"] == 0:
#                 # Nếu chưa có -> tạo mới user
#                 db.insert(
#                     "users",
#                     {
#                         "user_id": user_id,
#                         "email_id": user_email,
#                         "user_name": user_name,
#                         "user_pic": user_pic,
#                         "first_logged_in": first_logged_in,
#                         "last_accessed": last_accessed
#                     }
#                 )
#                 logger.info(f"User {user_email} inserted successfully")
#             else:
#                 logger.info(f"User {user_email} already exists")

#     except Exception as e:
#         logger.error(f"Error while logging user: {e}")

# def log_token(access_token, user_email, session_id):
#     """Ghi log token đã cấp cho user."""
#     try:
#         with PostgresDB() as db:
#             # Insert token vào bảng issued_tokens
#             db.insert(
#                 "issued_tokens",
#                 {
#                     "token": access_token,
#                     "email_id": user_email,
#                     "session_id": session_id
#                 }
#             )
#             logger.info(f"Token for {user_email} inserted successfully")

#     except Exception as e:
#         logger.error(f"Error while logging token: {e}")
