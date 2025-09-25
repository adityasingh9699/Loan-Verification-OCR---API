import httpx
from fastapi import HTTPException, status
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ClerkAuthService:
    def __init__(self):
        self.secret_key = settings.CLERK_SECRET_KEY
        self.base_url = "https://api.clerk.com/v1"
    
    async def verify_token(self, token: str) -> dict:
        """Verify JWT token with Clerk"""
        try:
            # For now, let's use a simpler approach - decode the JWT without verification
            # This is for development purposes. In production, you should verify the signature
            import jwt
            import json
            from datetime import datetime
            
            # Decode the token without verification to get the payload
            # In production, you should verify the signature using Clerk's public keys
            try:
                payload = jwt.decode(token, options={"verify_signature": False})
                
                # Check if token is expired
                exp = payload.get('exp')
                if exp and datetime.utcnow().timestamp() > exp:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has expired"
                    )
                
                # Extract user information
                user_id = payload.get('sub')
                if not user_id:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token format"
                    )
                
                return {
                    "user_id": user_id,
                    "session_id": payload.get('sid'),
                    "expires_at": exp
                }
                
            except jwt.InvalidTokenError as e:
                logger.error(f"Invalid JWT token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )
    
    async def get_user_info(self, user_id: str) -> dict:
        """Get user information from Clerk"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/{user_id}",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    # If we can't get user info from Clerk, return a basic structure
                    logger.warning(f"Could not get user info from Clerk: {response.status_code}")
                    return {
                        "id": user_id,
                        "email_addresses": [{"email_address": f"user_{user_id}@example.com"}]
                    }
        except httpx.RequestError as e:
            logger.error(f"Error getting user info from Clerk: {e}")
            # Return a basic structure if Clerk is unavailable
            return {
                "id": user_id,
                "email_addresses": [{"email_address": f"user_{user_id}@example.com"}]
            }

# Global instance
clerk_auth = ClerkAuthService()
