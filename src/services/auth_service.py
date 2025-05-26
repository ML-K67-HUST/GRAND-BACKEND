"""
Enhanced authentication service with comprehensive JWT handling.

This service provides:
- JWT token creation and validation
- Token refresh mechanism
- Password hashing and verification
- User session management
- Google OAuth integration
- Security logging and monitoring
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import hashlib
import secrets
from functools import lru_cache

import jwt
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.config import settings
from core.exceptions import (
    AuthenticationError,
    TokenExpiredError,
    InvalidTokenError,
    UserNotFoundError,
    ValidationError
)
from infrastructure.database.connection import db_manager

logger = logging.getLogger(__name__)


class AuthService:
    """
    Enhanced authentication service with JWT and security features.
    """
    
    def __init__(self):
        self.jwt_secret = settings.jwt.secret_key
        self.jwt_refresh_secret = settings.jwt.refresh_secret_key
        self.jwt_algorithm = settings.jwt.algorithm
        self.access_token_expire_minutes = settings.jwt.access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt.refresh_token_expire_days

        # Token blacklist (in production, use Redis)
        self._blacklisted_tokens = set()
    
    # Password Management
    
    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password
            hashed_password: Stored hash
            
        Returns:
            bool: True if password matches
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def validate_password_strength(self, password: str) -> Tuple[bool, list]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple[bool, list]: (is_valid, list_of_requirements)
        """
        requirements = []
        is_valid = True
        
        if len(password) < 8:
            requirements.append("Password must be at least 8 characters long")
            is_valid = False
        
        if not any(c.isupper() for c in password):
            requirements.append("Password must contain at least one uppercase letter")
            is_valid = False
        
        if not any(c.islower() for c in password):
            requirements.append("Password must contain at least one lowercase letter")
            is_valid = False
        
        if not any(c.isdigit() for c in password):
            requirements.append("Password must contain at least one number")
            is_valid = False
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            requirements.append("Password must contain at least one special character")
            is_valid = False
        
        return is_valid, requirements
    
    # JWT Token Management
    
    def create_access_token(
        self, 
        user_id: str, 
        email: str, 
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create JWT access token.
        
        Args:
            user_id: User identifier
            email: User email
            additional_claims: Additional JWT claims
            
        Returns:
            str: JWT access token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "iat": now,  # Issued at
            "exp": expire,  # Expiration
            "type": "access",
            "jti": self._generate_jti()  # JWT ID for blacklisting
        }
        
        # Add additional claims
        if additional_claims:
            payload.update(additional_claims)
        
        try:
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            logger.info(f"Access token created for user {user_id}")
            return token
            
        except Exception as e:
            logger.error(f"Access token creation failed: {e}")
            raise AuthenticationError("Token creation failed")
    
    def create_refresh_token(self, user_id: str, email: str) -> str:
        """
        Create JWT refresh token.
        
        Args:
            user_id: User identifier
            email: User email
            
        Returns:
            str: JWT refresh token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "email": email,
            "iat": now,
            "exp": expire,
            "type": "refresh",
            "jti": self._generate_jti()
        }
        
        try:
            token = jwt.encode(
                payload, 
                self.jwt_refresh_secret, 
                algorithm=self.jwt_algorithm
            )
            
            logger.info(f"Refresh token created for user {user_id}")
            return token
            
        except Exception as e:
            logger.error(f"Refresh token creation failed: {e}")
            raise AuthenticationError("Token creation failed")
    
    async def validate_access_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT access token.
        
        Args:
            token: JWT access token
            
        Returns:
            Dict[str, Any]: User context from token
            
        Raises:
            TokenExpiredError: If token is expired
            InvalidTokenError: If token is invalid
        """
        try:
            # Check if token is blacklisted
            if self._is_token_blacklisted(token):
                raise InvalidTokenError("Token has been revoked")
            
            # Decode and validate token
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            # Verify token type
            if payload.get("type") != "access":
                raise InvalidTokenError("Invalid token type")
            
            # Extract user context
            user_context = {
                "user_id": payload["sub"],
                "email": payload["email"],
                "jti": payload.get("jti"),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp")
            }
            
            # Add any additional claims
            for key, value in payload.items():
                if key not in ["sub", "email", "iat", "exp", "type", "jti"]:
                    user_context[key] = value
            
            return user_context
            
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Access token has expired")
            
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid access token: {str(e)}")
            
        except Exception as e:
            logger.error(f"Access token validation error: {e}")
            raise InvalidTokenError("Token validation failed")
    
    async def validate_refresh_token(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT refresh token.
        
        Args:
            token: JWT refresh token
            
        Returns:
            Dict[str, Any]: User context from token
        """
        try:
            if self._is_token_blacklisted(token):
                raise InvalidTokenError("Token has been revoked")
            
            payload = jwt.decode(
                token,
                self.jwt_refresh_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            if payload.get("type") != "refresh":
                raise InvalidTokenError("Invalid token type")
            
            return {
                "user_id": payload["sub"],
                "email": payload["email"],
                "jti": payload.get("jti")
            }
            
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Refresh token has expired")
            
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid refresh token: {str(e)}")
    
    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Tuple[str, str]: (new_access_token, new_refresh_token)
        """
        try:
            # Validate refresh token
            user_context = await self.validate_refresh_token(refresh_token)
            
            # Blacklist old refresh token
            self._blacklist_token(refresh_token)
            
            # Create new tokens
            new_access_token = self.create_access_token(
                user_context["user_id"],
                user_context["email"]
            )
            
            new_refresh_token = self.create_refresh_token(
                user_context["user_id"],
                user_context["email"]
            )
            
            logger.info(f"Tokens refreshed for user {user_context['user_id']}")
            
            return new_access_token, new_refresh_token
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise
    
    # User Registration and Authentication
    
    async def register_user(
        self,
        email: str,
        password: str,
        username: str,
        first_name: str,
        last_name: str
    ) -> Tuple[Dict[str, Any], str, str]:
        """
        Register a new user account.
        
        Args:
            email: User email
            password: User password
            username: Username
            first_name: First name
            last_name: Last name
            
        Returns:
            Tuple[Dict, str, str]: (user_data, access_token, refresh_token)
        """
        async with db_manager.get_session() as session:
            try:
                # Check if email already exists
                existing_user = await self._get_user_by_email(session, email)
                if existing_user:
                    raise AuthenticationError("Email already registered")
                
                # Check if username already exists
                existing_username = await self._get_user_by_username(session, username)
                if existing_username:
                    raise AuthenticationError("Username already taken")
                
                # Hash password
                password_hash = self.hash_password(password)
                
                # Create user
                user_id = await self._create_user(
                    session, email, username, password_hash, first_name, last_name
                )
                
                # Create tokens
                access_token = self.create_access_token(user_id, email)
                refresh_token = self.create_refresh_token(user_id, email)
                
                logger.info(f"User created successfully: {email}")
                
                # Return user data
                user_data = {
                    "user_id": user_id,
                    "email": email,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_active": True
                }
                
                return user_data, access_token, refresh_token
                
            except AuthenticationError:
                raise
            except Exception as e:
                logger.error(f"User registration failed: {e}")
                raise AuthenticationError("Registration failed")
    
    async def authenticate_user(
        self, 
        email: str, 
        password: str
    ) -> Tuple[Dict[str, Any], str, str]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Tuple[Dict, str, str]: (user_data, access_token, refresh_token)
        """
        async with db_manager.get_session() as session:
            try:
                # Get user from database
                user = await self._get_user_by_email(session, email)
                
                if not user:
                    raise AuthenticationError("Invalid email or password")
                
                # Verify password
                if not self.verify_password(password, user["password_hash"]):
                    logger.warning(f"Failed login attempt for email: {email}")
                    raise AuthenticationError("Invalid email or password")
                
                # Check if user is active
                if not user.get("is_active", True):
                    raise AuthenticationError("Account is deactivated")
                
                # Convert UUID to string for JSON serialization
                user_id_str = str(user["userid"])
                
                # Create tokens
                access_token = self.create_access_token(
                    user_id_str,
                    user["email"]
                )
                
                refresh_token = self.create_refresh_token(
                    user_id_str,
                    user["email"]
                )
                
                # Update last login
                await self._update_last_login(session, user_id_str)
                
                logger.info(f"User authenticated successfully: {email}")
                
                # Return user data (excluding sensitive info)
                user_data = {
                    "user_id": user_id_str,
                    "email": user["email"],
                    "username": user.get("username"),
                    "first_name": user.get("first_name"),
                    "last_name": user.get("last_name"),
                    "last_login": user.get("last_login")
                }
                
                return user_data, access_token, refresh_token
                
            except AuthenticationError:
                raise
            except Exception as e:
                logger.error(f"User authentication failed: {e}")
                raise AuthenticationError("Authentication failed")
    
    async def logout_user(self, access_token: str, refresh_token: str) -> None:
        """
        Logout user by blacklisting tokens.
        
        Args:
            access_token: User's access token
            refresh_token: User's refresh token
        """
        try:
            # Blacklist both tokens
            self._blacklist_token(access_token)
            self._blacklist_token(refresh_token)
            
            logger.info("User logged out successfully")
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            raise AuthenticationError("Logout failed")
    
    # Token Blacklisting
    
    def _blacklist_token(self, token: str) -> None:
        """Add token to blacklist"""
        # In production, store in Redis with expiration
        jti = self._extract_jti_from_token(token)
        if jti:
            self._blacklisted_tokens.add(jti)
    
    def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        jti = self._extract_jti_from_token(token)
        return jti in self._blacklisted_tokens if jti else False
    
    def _extract_jti_from_token(self, token: str) -> Optional[str]:
        """Extract JTI from token without validation"""
        try:
            # Decode without verification to get JTI
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("jti")
        except:
            return None
    
    def _generate_jti(self) -> str:
        """Generate unique JWT ID"""
        return secrets.token_urlsafe(32)
    
    # Database Operations
    
    async def _get_user_by_email(
        self, 
        session: AsyncSession, 
        email: str
    ) -> Optional[Dict[str, Any]]:
        """Get user by email from database"""
        try:
            query = text("""
                SELECT 
                    userid, email, username, first_name, last_name,
                    password_hash, is_active, last_login, created_at
                FROM users 
                WHERE email = :email
            """)
            
            result = await session.execute(query, {"email": email})
            row = result.fetchone()
            
            if not row:
                return None
            
            return dict(row._mapping)
            
        except Exception as e:
            logger.error(f"Database error fetching user by email: {e}")
            raise AuthenticationError("Database error during authentication")
    
    async def _get_user_by_username(
        self, 
        session: AsyncSession, 
        username: str
    ) -> Optional[Dict[str, Any]]:
        """Get user by username from database"""
        try:
            query = text("""
                SELECT 
                    userid, email, username, first_name, last_name,
                    password_hash, is_active, last_login, created_at
                FROM users 
                WHERE username = :username
            """)
            
            result = await session.execute(query, {"username": username})
            row = result.fetchone()
            
            if not row:
                return None
            
            return dict(row._mapping)
            
        except Exception as e:
            logger.error(f"Database error fetching user by username: {e}")
            raise AuthenticationError("Database error during registration")
    
    async def _create_user(
        self,
        session: AsyncSession,
        email: str,
        username: str,
        password_hash: str,
        first_name: str,
        last_name: str
    ) -> str:
        """Create new user in database"""
        try:
            import uuid
            from datetime import datetime, timezone
            
            user_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            query = text("""
                INSERT INTO users (
                    userid, email, username, first_name, last_name,
                    password_hash, is_active, created_at, last_login
                ) VALUES (
                    :userid, :email, :username, :first_name, :last_name,
                    :password_hash, :is_active, :created_at, :last_login
                )
            """)
            
            await session.execute(query, {
                "userid": user_id,
                "email": email,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "password_hash": password_hash,
                "is_active": True,
                "created_at": now,
                "last_login": None
            })
            
            await session.commit()
            return user_id
            
        except Exception as e:
            logger.error(f"Database error creating user: {e}")
            raise AuthenticationError("Database error during registration")
    
    async def _update_last_login(
        self, 
        session: AsyncSession, 
        user_id: str
    ) -> None:
        """Update user's last login timestamp"""
        try:
            now = datetime.now(timezone.utc)
            
            query = text("""
                UPDATE users 
                SET last_login = :last_login
                WHERE userid = :user_id
            """)
            
            await session.execute(query, {
                "last_login": now,
                "user_id": user_id
            })
            
        except Exception as e:
            logger.error(f"Database error updating last login: {e}")
            # Don't raise exception here as it's not critical for auth


# Global auth service instance
@lru_cache()
def get_auth_service() -> AuthService:
    """Get cached auth service instance"""
    return AuthService()


# FastAPI dependency
def get_auth_service_dependency() -> AuthService:
    """FastAPI dependency for auth service"""
    return get_auth_service() 