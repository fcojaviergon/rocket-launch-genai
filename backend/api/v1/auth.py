from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import jwt as pyjwt
import logging
from fastapi.encoders import jsonable_encoder

from core.config import settings
from core.dependencies import get_db, get_current_active_user
from modules.auth.service import AuthService
from database.models.user import User
from schemas.auth import Token, UserCreate, UserResponse, RefreshTokenRequest
from modules.auth.exceptions import (
    AuthError,
    InvalidCredentialsError,
    UserNotFoundError,
    UserInactiveError,
    EmailAlreadyExistsError,
    InvalidTokenError,
    TokenExpiredError
)
from core.dependencies import get_auth_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Get JWT access token
    """

    try:
        # Try to authenticate user. Service raises exceptions on failure.
        user = await auth_service.authenticate_user(
            db=db, 
            email=form_data.username, 
            password=form_data.password
        )

        # If authentication succeeds, proceed to create tokens
        
        logger.info(f"Authentication successful for user: {form_data.username}")
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        refresh_token = auth_service.create_refresh_token(data={"sub": str(user.id)})
        
        # Log user information
        logger.info(f"Tokens generated for user: {user.email}, Role: {user.role}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
                }
            }
    
    except UserInactiveError as e:
        logger.warning(f"Authentication failed for {form_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=str(e),
        )
    except InvalidCredentialsError as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e), headers={"WWW-Authenticate": "Bearer"})
    except Exception as e:
        logger.exception(f"Unexpected error during login: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to authenticate user.")


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user
    """
    try:
        # Service now returns the ORM object
        user = await auth_service.register_user(db, user_data)
        return user # Removed comment
    except EmailAlreadyExistsError as e: # Catch specific error
         logger.warning(f"Registration failed: {e}")
         raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e: # Catch other potential ValueErrors from service
         logger.error(f"Validation error during registration: {e}")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e: # Catch unexpected errors
         logger.exception(f"Unexpected error during user registration: {e}")
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register user.")

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token
    """
    token = refresh_request.refresh_token

    try:
        user = await auth_service.verify_refresh_token(db, token)

        # Generate new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )

        # Generate new refresh token (optional, we could also keep the same one)
        new_refresh_token = auth_service.create_refresh_token(data={"sub": str(user.id)})

        logger.info(f"Tokens regenerated via refresh for user: {user.email}")
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role
            }
        }
    except TokenExpiredError as e:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e), headers={"WWW-Authenticate": "Bearer"})
    except InvalidTokenError as e:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e), headers={"WWW-Authenticate": "Bearer"})
    except UserNotFoundError as e:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e), headers={"WWW-Authenticate": "Bearer"})
    except UserInactiveError as e:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e), headers={"WWW-Authenticate": "Bearer"})
    except AuthError as e:
         logger.error(f"Generic auth error during token refresh: {e}")
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not refresh token", headers={"WWW-Authenticate": "Bearer"})
    except Exception as e:
        # Log the full traceback for unexpected errors
        logger.exception(f"Unexpected error during token refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during token refresh.",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/me")
async def get_current_user(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information (Bypassing response_model for diagnosis)
    """
    logger.info(f"Fetching current user info for: {current_user.email} (ID: {current_user.id}) Role: {current_user.role}")
    
    # Manually encode using FastAPI's encoder
    return jsonable_encoder(current_user)
