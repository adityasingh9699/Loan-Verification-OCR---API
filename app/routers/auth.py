from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models import User
from app.services.auth_service import clerk_auth
from app.services.firestore_service import firestore_service
import logging

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user"""
    try:
        # Verify token with Clerk
        token_data = await clerk_auth.verify_token(credentials.credentials)
        clerk_user_id = token_data.get("user_id")
        
        if not clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get or create user in Firestore
        user_data = await firestore_service.get_user_by_clerk_id(clerk_user_id)
        
        if not user_data:
            # Get user info from Clerk
            user_info = await clerk_auth.get_user_info(clerk_user_id)
            email = user_info.get("email_addresses", [{}])[0].get("email_address", "")
            
            # Create new user
            user_data = {
                "clerk_user_id": clerk_user_id,
                "email": email
            }
            user_id = await firestore_service.create_user(user_data)
            user_data["id"] = user_id
        
        return User(**user_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "clerk_user_id": current_user.clerk_user_id,
        "email": current_user.email,
        "created_at": current_user.created_at
    }
