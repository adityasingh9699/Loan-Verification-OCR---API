from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.routers.auth import get_current_user
from app.services.firestore_service import FirestoreService
from app.models import User

router = APIRouter(tags=["stats"])

@router.get("/global")
async def get_global_stats(current_user: User = Depends(get_current_user)):
    """
    Get global statistics for all applications in the database
    """
    try:
        firestore_service = FirestoreService()
        
        # Get all applications from the database
        all_applications = await firestore_service.get_all_applications()
        
        # Calculate statistics
        total_applications = len(all_applications)
        verified_count = len([app for app in all_applications if app.get('verification_status') == 'verified'])
        mismatch_count = len([app for app in all_applications if app.get('verification_status') == 'mismatch'])
        pending_count = len([app for app in all_applications if app.get('verification_status') == 'pending'])
        error_count = len([app for app in all_applications if app.get('verification_status') == 'error'])
        no_documents_count = len([app for app in all_applications if app.get('verification_status') == 'no_documents'])
        
        # Calculate verification rate
        verified_rate = (verified_count / total_applications * 100) if total_applications > 0 else 0
        
        stats = {
            "total_applications": total_applications,
            "verified": verified_count,
            "mismatch": mismatch_count,
            "pending": pending_count,
            "error": error_count,
            "no_documents": no_documents_count,
            "verification_rate": round(verified_rate, 1)
        }
        
        return stats
        
    except Exception as e:
        print(f"Error fetching global stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch global statistics")
