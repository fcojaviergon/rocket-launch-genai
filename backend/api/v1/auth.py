from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import jwt as pyjwt

from core.config import settings
from core.deps import get_db, get_current_active_user
from modules.auth.service import AuthService
from database.models.user import User
from schemas.auth import Token, UserCreate, UserResponse

router = APIRouter()
auth_service = AuthService()

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Get JWT access token
    """

    user = await auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        print(f"Authentication failed for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"Access token authentication successful for: {form_data.username}")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    refresh_token = auth_service.create_refresh_token(data={"sub": str(user.id)})
    
    # Print user information for debugging
    print(f"Authenticated user: {user.email}, Role: {user.role}")
    
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

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    """
    try:
        user = await auth_service.register_user(db, user_data)
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    print(f"Refresh data received: {refresh_data}")
    token = refresh_data.get("token")
    if not token:
        print("Error: No refresh token received")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required"
        )
        
    try:
        print(f"Decoding token: {token[:10]}...")
        # Decode the token to get the user ID
        try:
            payload = pyjwt.decode(
                token, settings.SECRET_KEY, algorithms=["HS256"]
            )
        except pyjwt.ExpiredSignatureError:
            print("Error: Refresh token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except pyjwt.InvalidTokenError as e:
            print(f"Error: Invalid token - {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user_id = payload.get("sub")
        if not user_id:
            print("Error: Token without 'sub' (user_id)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token (no user_id)",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        print(f"User ID extracted from token: {user_id}")
        # Verify user exists
        user = await db.get(User, user_id)
        if not user:
            print(f"Error: User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not user.is_active:
            print(f"Error: Inactive user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print(f"User verified: {user.email}, Role: {user.role}")
        # Generate new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # Generate new refresh token (optional, we could also keep the same one)
        refresh_token = auth_service.create_refresh_token(data={"sub": str(user.id)})
        
        print(f"Tokens regenerated for user: {user.email}")
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error refreshing token: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information
    """
    print(f"Endpoint /me: User: {current_user.email}, ID: {current_user.id}, Role: {current_user.role}")
    print(f"Complete user data: {current_user.__dict__}")
    
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "role": current_user.role
    }
