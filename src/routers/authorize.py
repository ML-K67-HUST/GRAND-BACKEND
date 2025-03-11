from pydantic import BaseModel
from authorization.check_user_login import (
    check_login, create_account, send_email, hash_password,
)
from authorization.token_based import (
    verify_access_token, refresh_tokens, generate_access_token, generate_refresh_token, store_refresh_token
)
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from database.postgresdb import PostgresDB
from google.oauth2 import id_token
from google.auth.transport import requests
from authorization.google_oauth import *
from authorization.token_based import get_current_user
import random
from config import settings
from typing import Optional
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.responses import RedirectResponse
from urllib.parse import quote


router = APIRouter(prefix='/authorization',tags=["authorization"])

oauth = OAuth()
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    client_kwargs={
        'scope': 'email openid profile',
        'redirect_uri': 'http://127.0.0.1:5050/auth'
    }
)
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str
    email: str = None
    full_name: str = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str
    confirm_password: str

class GoogleAuthRequest(BaseModel):
    id_token: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/login/")
def login(user: LoginRequest):
    return check_login(user.username, user.password)

@router.post("/register/")
def register(user: RegisterRequest):
    return create_account(user.username, user.password, user.confirm_password, user.email, user.full_name)

@router.get("/google-login/")
async def login(request: Request):
    url = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, url)

@router.get('/callback')
async def auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as e:
        return {"error": e.error}

    user = token.get('userinfo')
    if user:
        print(user)
        username = user.get('name')
        userID = user.get('sub')  # Google user ID

        # Encode username để tránh lỗi UnicodeEncodeError
        encoded_username = quote(username)

        user_data = {
            "userid":userID,
            "username": username,
            "email":user.get("email"),
            "password": "google_auth",
            "full_name": user.get("name"),
            "google_auth":"true"
        }
        access_token = generate_access_token(user_data, google_auth=True)
        print('ACCESS TOKEN:\n',access_token)
        refresh_token = generate_refresh_token(user_data)

        # print('REFRESH TOKEN:\n', refresh_token)
        store_refresh_token(user_id=userID, refresh_token=refresh_token)
        
        response = Response(status_code=302)
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="Lax")

        response.headers["Location"] = f"http://127.0.0.1:5001/calendar?username={encoded_username}&record={userID}"
        return response

    return {"error": "User info not found"}

@router.post("/forgot-password/")
def forgot_password(request: ForgotPasswordRequest):
    email = request.email

    with PostgresDB() as db:
        user = db.select("users", {"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="❌ Email không tồn tại!")

        userid = user[0]["userid"]

    otp = str(random.randint(100000, 999999)) 
    expires_at = datetime.utcnow() + timedelta(minutes=1) 

    with PostgresDB() as db:
        db.execute("DELETE FROM password_reset_otp WHERE email = %s", (email,), commit=True)
        db.insert("password_reset_otp", {"email": email, "otp": otp, "expires_at": expires_at})

    send_email(user_email=email, subject="OTP code to reset your password", message=f"This is your OTP, don't share with any body:\n{otp}\nCode expires after 1 minutes.")

    return {"message": "✅ Kiểm tra email để lấy OTP!"}

@router.post("/verify-otp/")
def verify_otp(request: VerifyOTPRequest):
    email = request.email
    otp = request.otp

    with PostgresDB() as db:
        result = db.select("password_reset_otp", {"email": email, "otp": otp})
        if not result:
            raise HTTPException(status_code=400, detail="❌ OTP không hợp lệ!")

        expires_at = result[0]["expires_at"]
        if datetime.utcnow() > expires_at:
            raise HTTPException(status_code=400, detail="❌ OTP đã hết hạn!")

        db.execute("UPDATE password_reset_otp SET verified = TRUE WHERE email = %s", (email,), commit=True)

    return {"message": "✅ OTP hợp lệ, bạn có thể đổi mật khẩu!"}

@router.post("/reset-password/")
def reset_password(request: ResetPasswordRequest):
    email = request.email
    new_password = request.new_password
    confirm_password = request.confirm_password
    
    with PostgresDB() as db:
        result = db.select("password_reset_otp", {"email": email})
        if not result or not result[0]["verified"]:
            raise HTTPException(status_code=400, detail="❌ OTP chưa được xác thực!")

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="❌ Mật khẩu xác nhận không khớp!")
    hashed_password = hash_password(new_password)
    with PostgresDB() as db:
        db.execute("UPDATE users SET password = %s WHERE email = %s", (hashed_password, email), commit=True)
        db.execute("DELETE FROM password_reset_otp WHERE email = %s", (email,), commit=True) 

    return {"message": "✅ Mật khẩu đã được cập nhật!"}

@router.post("/refresh-token/")
def refresh_token_endpoint(request: RefreshTokenRequest):
    result = refresh_tokens(request.refresh_token)
    if "error" in result:
        raise HTTPException(status_code=result.get("status_code", 401), detail=result["error"])
    return result

@router.get("/verify-token/")
def verify_token_endpoint(current_user = Depends(get_current_user)):
    return {
        "status_code": 200,
        "message": "Token is valid",
        "user": current_user
    }

@router.post("/logout/")
def logout(request: RefreshTokenRequest):
    try:
        payload = verify_access_token(request.refresh_token)
        if payload and "jti" in payload:
            from authorization.check_user_login import revoke_refresh_token
            revoke_refresh_token(payload["jti"])
    except:
        pass
    
    return {"status_code": 200, "message": "Logged out successfully"}