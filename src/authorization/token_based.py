import jwt
from datetime import datetime, timedelta
from database.mongodb import MongoManager
from database.postgresdb import PostgresDB
from fastapi import APIRouter, HTTPException, Depends, Header
from config import settings
from typing import Optional
import uuid

async def get_current_user(authorization: Optional[str] = Header(None),google_auth: Optional[str] = Header(None)):
    if settings.security_on:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        scheme, token = authorization.split()
        print('token no doi verify\n')
        print(token)
        print('gg authen:\n', google_auth)
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
        payload = verify_access_token(token.strip("b'"))
        print('payload parsed:\n',payload)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        if isinstance(payload, dict) and "error" in payload:
            if payload["code"] == "token_expired":
                raise HTTPException(status_code=401, detail="Token expired")
            raise HTTPException(status_code=401, detail=payload["error"])
        
        with PostgresDB() as db:
            user = db.select("users", {"userid": payload["sub"]})
            print(user)
            if not user:
                if google_auth == "true":
                    try:
                        
                        email = db.select("users", {"email": payload.get("email","")})
                    except:
                        email = {}
                    if email:
                        return email[0]
                    db.insert("users",{
                        "userid": str(payload["sub"]),
                        "username": payload["username"],
                        "email": payload["email"],
                        "password":payload["password"],
                        "full_name":payload["full_name"],
                        "google_auth": payload["google_auth"],
                    })
                    return {
                        "userid": str(payload["sub"]),
                        "username": payload["username"],
                        "email": payload["email"],
                        "password":payload["password"],
                        "full_name":payload["full_name"],
                        "google_auth": payload["google_auth"],
                    }
                else:
                    raise HTTPException(status_code=404, detail="User not found")
        
        return user[0]

def generate_access_token(user_data, google_auth=False):
    if google_auth:
        payload = {
            "sub": str(user_data["userid"]),
            "username": user_data["username"],
            "email": user_data["email"],
            "password":user_data["password"],
            "full_name":user_data["full_name"],
            "google_auth": user_data["google_auth"],
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow(),
            "type": "access"
        }
    else:
        payload = {
            "sub": str(user_data["userid"]),
            "username": user_data["username"],
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow(),
            "type": "access"
        }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

def generate_refresh_token(user_data):
    token_id = str(uuid.uuid4())
    payload = {
        "sub": str(user_data["userid"]),
        "jti": token_id,  
        "exp": datetime.utcnow() + timedelta(days=7),  
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    return jwt.encode(payload, settings.JWT_REFRESH_SECRET_KEY, algorithm="HS256")

def store_refresh_token(user_id, refresh_token):
    with PostgresDB() as db:

        payload = jwt.decode(
            refresh_token, 
            settings.JWT_REFRESH_SECRET_KEY, 
            algorithms=["HS256"]
        )
        
        token_data = {
            "userid": user_id,
            "token_id": payload["jti"],
            "expires_at": datetime.fromtimestamp(payload["exp"]),
            "revoked": False
        }
        
        db.insert("refresh_tokens", token_data)

def verify_access_token(token):
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=["HS256"]
        )
        if payload.get("type") != "access":
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired", "code": "token_expired"}
    except jwt.InvalidTokenError:
        return None

def verify_refresh_token(token):
    try:
        payload = jwt.decode(
            token, 
            settings.JWT_REFRESH_SECRET_KEY, 
            algorithms=["HS256"]
        )
        
        if payload.get("type") != "refresh":
            return None
            
        with PostgresDB() as db:
            token_record = db.select("refresh_tokens", {
                "token_id": payload["jti"],
                "revoked": False
            })
            
            if not token_record:
                return None
                
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired", "code": "token_expired"}
    except jwt.InvalidTokenError:
        return None

def revoke_refresh_token(token_id):
    with PostgresDB() as db:
        db.execute(
            "UPDATE refresh_tokens SET revoked = TRUE WHERE token_id = %s",
            (token_id,),
            commit=True
        )

def refresh_tokens(refresh_token):
    payload = verify_refresh_token(refresh_token)
    
    if not payload or isinstance(payload, dict) and "error" in payload:
        return {"status_code": 401, "error": "Invalid or expired refresh token"}
    
    user_id = payload["sub"]
    with PostgresDB() as db:
        user = db.select("users", {"userid": user_id})
        
    if not user:
        return {"status_code": 404, "error": "User not found"}
    
    revoke_refresh_token(payload["jti"])
    
    access_token = generate_access_token(user[0])
    new_refresh_token = generate_refresh_token(user[0])
    
    store_refresh_token(user_id, new_refresh_token)
    
    return {
        "status_code": 200,
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }